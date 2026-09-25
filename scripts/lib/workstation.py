"""Debian-only setup. Pure helpers are importable for macOS fixture tests."""

import argparse
import difflib
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[2]
ENV = dict(os.environ, LC_ALL="C", PATH="/usr/sbin:/usr/bin:/sbin:/bin")
PROFILES = {"base", "desktop", "development", "media", "latex"}
GIB = 1024**3


class SetupError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise SetupError(message)


def read(path):
    return Path(path).read_text()


def run(*args):
    result = subprocess.run(args, text=True, capture_output=True, env=ENV)
    require(result.returncode == 0,
            f"{shlex.join(args)} failed: {result.stderr.strip() or result.stdout.strip()}")
    return result.stdout.strip()


def guard():
    require(platform.system() == "Linux", "Debian 13 only; never run setup on macOS.")
    release = {}
    for line in read("/etc/os-release").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            release[key] = value.strip('"\'')
    require(release.get("ID") == "debian" and release.get("VERSION_ID") == "13",
            "Only Debian 13 is supported.")
    require(platform.machine() == "x86_64", "Only the amd64 target is supported.")
    require(sys.version_info[:2] == (3, 13), "Use Debian's /usr/bin/python3 (3.13).")


def load_config(path, identifiers=False):
    with Path(path).open("rb") as stream:
        config = tomllib.load(stream)
    schema = {"storage": {"swap_uuid"}, "network": {"interface", "connection_uuid"},
              "packages": {"profiles", "tailscale"}}
    require(set(config) == set(schema), "Config must contain storage, network, packages only.")
    for section, keys in schema.items():
        require(isinstance(config[section], dict) and set(config[section]) == keys,
                f"Unexpected or missing config keys in {section}.")
    profiles = config["packages"]["profiles"]
    require(isinstance(profiles, list) and all(isinstance(p, str) for p in profiles),
            "profiles must be a list of strings.")
    require("base" in profiles and set(profiles) <= PROFILES and len(set(profiles)) == len(profiles),
            "Choose unique supported profiles, including base.")
    require(type(config["packages"]["tailscale"]) is bool, "tailscale must be a boolean.")
    for section, key in (("storage", "swap_uuid"), ("network", "connection_uuid")):
        value = config[section][key]
        require(isinstance(value, str), f"{key} must be a string.")
        if value or identifiers:
            require(re.fullmatch(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}", value),
                    f"Set {key} to the real UUID from preflight.")
            config[section][key] = value.lower()
    iface = config["network"]["interface"]
    require(isinstance(iface, str), "interface must be a string.")
    require((not iface and not identifiers) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,14}", iface),
            "Set interface to the wired device name from preflight.")
    return config


def packages(config):
    names = set()
    for profile in config["packages"]["profiles"]:
        for line in read(ROOT / "packages" / f"{profile}.txt").splitlines():
            name = line.split("#", 1)[0].strip()
            if name:
                require(re.fullmatch(r"[a-z0-9][a-z0-9+.-]+", name), f"Invalid package: {name}")
                names.add(name)
    return sorted(names)


class Changes:
    """Preview by default; atomic file replacement with per-run original backups."""

    def __init__(self, apply, state):
        self.apply = apply
        self.state = Path(state)
        self.backup = None
        self.entries = []

    def save(self, name, data):
        if self.backup is None:
            self.state.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.backup = Path(tempfile.mkdtemp(prefix="run-", dir=self.state))
            print(f"Run records: {self.backup}")
        target = self.backup / name
        target.write_text(data)
        target.chmod(0o600)

    def command(self, *args):
        print(("RUN " if self.apply else "WOULD RUN ") + shlex.join(args), flush=True)
        if self.apply:
            result = subprocess.run(args, env=ENV)
            require(result.returncode == 0, f"Command failed: {shlex.join(args)}; see docs/recovery.md.")

    def file(self, path, data, mode=0o644):
        path = Path(path)
        require(not path.is_symlink(), f"Refusing to replace symlink: {path}")
        require(not path.exists() or path.is_file(), f"Not a regular file: {path}")
        if isinstance(data, str):
            data = data.encode()
        before = path.read_bytes() if path.exists() else None
        if before == data and path.stat().st_mode & 0o777 == mode:
            print(f"OK {path}")
            return False
        print(f"{'WRITE' if self.apply else 'WOULD WRITE'} {path} (mode {mode:o})")
        try:
            print("".join(difflib.unified_diff(
                (before or b"").decode().splitlines(True), data.decode().splitlines(True),
                fromfile=str(path), tofile=f"{path} (desired)")), end="")
        except UnicodeDecodeError:
            print(f"  binary SHA256: {hashlib.sha256(data).hexdigest()}")
        if not self.apply:
            return True
        self.save("phase.txt", "File and command changes; consult manifest.json and recovery.md.\n")
        entry = {"path": str(path), "existed": before is not None}
        if before is not None:
            original = self.backup / f"original-{len(self.entries)}"
            shutil.copy2(path, original)
            entry.update(backup=str(original), mode=path.stat().st_mode & 0o777,
                         uid=path.stat().st_uid, gid=path.stat().st_gid)
        self.entries.append(entry)
        self.save("manifest.json", json.dumps(self.entries, indent=2) + "\n")
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temporary = tempfile.mkstemp(prefix=".workstation-", dir=path.parent)
        try:
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(temporary, mode)
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return True


def flatten(devices):
    result = []
    for device in devices:
        result.append(device)
        result.extend(flatten(device.get("children", [])))
    return result


def validate_storage(devices, swap_uuid, root_device, efi_device, active, persistent):
    """Pure validation: never infer a disk from enumeration order."""
    require(not any(d["type"] == "crypt" or d.get("fstype") in {"crypto_LUKS", "BitLocker"}
                    for d in devices), "Encrypted storage detected; this project requires no encryption.")
    by_name = {d["name"]: d for d in devices}
    root = by_name.get(root_device, {})
    require(root.get("type") == "part" and root.get("fstype") == "ext4",
            "Supported baseline: ext4 root on a direct partition (no LVM/RAID).")
    matches = {d["name"]: d for d in devices if (d.get("uuid") or "").lower() == swap_uuid.lower()}
    require(len(matches) == 1, "Swap UUID must resolve to exactly one partition.")
    swap = next(iter(matches.values()))
    require(swap["type"] == "part" and swap["fstype"] == "swap", "Selected UUID is not a swap partition.")
    require(swap.get("pkname") and swap["pkname"] == root.get("pkname"),
            "Swap must be on the same Debian drive as root.")
    require(swap["size"] >= 24 * GIB - 1024**2, "Swap partition must be approximately 24 GiB or larger.")
    efi = by_name.get(efi_device, {})
    require(efi.get("fstype") == "vfat" and efi.get("pkname") == root.get("pkname"),
            "Mount the Debian drive's independent EFI partition at /boot/efi.")
    require(swap["name"] in active, "Selected swap is not active; fix installer setup first.")
    require(swap["name"] in persistent, "Selected swap needs an existing /etc/fstab entry.")
    require(all(name == swap["name"] or name.startswith("/dev/zram") for name in active),
            "Unexpected additional disk swap; resolve the resume design first.")
    return swap


def tokens(path):
    return read(path).replace("[", "").replace("]", "").split()


def check_resume_conflicts(swap_uuid):
    expected = f"UUID={swap_uuid}".lower()
    paths = [Path("/proc/cmdline"), Path("/etc/default/grub")]
    paths += list(Path("/etc/default/grub.d").glob("*.cfg"))
    for path in paths:
        if not path.exists():
            continue
        for line in read(path).splitlines():
            if line.lstrip().startswith("#"):
                continue
            require(not re.search(r"\b(?:noresume|resume_offset=)", line),
                    f"Remove incompatible noresume/resume_offset settings in {path} first.")
            for value in re.findall(r"\bresume=([^\s\"']+)", line):
                require(value.lower() == expected, f"Conflicting resume device in {path}: {value}")
    paths = [Path("/etc/initramfs-tools/initramfs.conf")]
    paths += list(Path("/etc/initramfs-tools/conf.d").glob("*"))
    managed = Path("/etc/initramfs-tools/conf.d/resume")
    for path in paths:
        if not path.is_file() or path == managed:
            continue
        for line in read(path).splitlines():
            match = re.match(r"\s*RESUME\s*=\s*['\"]?([^\s'\"#]+)", line)
            require(not match or match[1].lower() == expected, f"Conflicting RESUME in {path}.")


def sleep_assignments(text):
    section = None
    result = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
        elif section == "Sleep" and "=" in line:
            key, value = line.split("=", 1)
            result.append((key.strip(), value.strip()))
    return result


def check_sleep_conflicts():
    desired = dict(sleep_assignments(read(ROOT / "system/sleep/60-workstation.conf")))
    managed = Path("/etc/systemd/sleep.conf.d/60-workstation.conf")
    for directory in ("/usr/lib/systemd", "/usr/local/lib/systemd", "/run/systemd", "/etc/systemd"):
        base = Path(directory)
        paths = [base / "sleep.conf", *sorted((base / "sleep.conf.d").glob("*.conf"))]
        for path in paths:
            if path == managed or not path.is_file():
                continue
            for key, value in sleep_assignments(read(path)):
                require(key not in desired or value == desired[key],
                        f"Conflicting sleep option {key}={value} in {path}; reconcile before setup/verification.")


def system_facts(config):
    require(os.geteuid() == 0, "Run system preview/verification with sudo for hardware inspection.")
    require("HP EliteDesk 805 G6" in read("/sys/class/dmi/id/product_name"),
            "This system phase targets an HP EliteDesk 805 G6 only.")
    for command in ("lsblk", "findmnt", "swapon", "nmcli", "ethtool", "sshd", "update-initramfs", "lsinitramfs"):
        require(shutil.which(command, path=ENV["PATH"]), f"Missing {command}; run the packages phase first.")
    require(Path("/boot/grub/grub.cfg").is_file(), "Expected installer-managed GRUB on Debian.")
    secure = Path("/sys/firmware/efi/efivars/SecureBoot-8be4df61-93ca-11d2-aa0d-00e098032b8c")
    require(secure.exists() and secure.read_bytes()[4:] == b"\x00", "Verify UEFI boot and disable Secure Boot in firmware.")
    lockdown = Path("/sys/kernel/security/lockdown")
    require(not lockdown.exists() or "[none]" in read(lockdown), "Kernel lockdown prevents this hibernation design.")
    require({"mem", "disk"} <= set(tokens("/sys/power/state")), "Kernel must offer mem and disk sleep states.")
    require("deep" in tokens("/sys/power/mem_sleep"), "S3/deep is unavailable; inspect firmware before continuing.")
    require("platform" in tokens("/sys/power/disk"), "ACPI platform hibernation is unavailable.")
    require(any(Path("/sys/class/rtc").glob("rtc*/wakealarm")), "No RTC wake alarm found for timed hibernation.")
    devices = flatten(json.loads(run("lsblk", "--json", "--bytes", "--paths", "--output",
                                    "NAME,TYPE,FSTYPE,UUID,SIZE,PKNAME,MOUNTPOINTS"))["blockdevices"])
    root = run("findmnt", "--noheadings", "--output", "SOURCE", "--mountpoint", "/")
    efi = run("findmnt", "--noheadings", "--output", "SOURCE", "--mountpoint", "/boot/efi")
    active = json.loads(run("swapon", "--show", "--json", "--bytes", "--output", "NAME,SIZE"))["swapdevices"]
    entries = json.loads(run("findmnt", "--fstab", "--evaluate", "--json", "--types", "swap", "--output", "SOURCE"))["filesystems"]
    swap = validate_storage(devices, config["storage"]["swap_uuid"], os.path.realpath(root), os.path.realpath(efi),
                            [os.path.realpath(x["name"]) for x in active],
                            [os.path.realpath(x["source"]) for x in entries])
    check_resume_conflicts(config["storage"]["swap_uuid"])
    check_sleep_conflicts()
    iface, connection = config["network"]["interface"], config["network"]["connection_uuid"]
    require(run("systemctl", "is-active", "NetworkManager") == "active", "NetworkManager must already manage Ethernet.")
    require(run("nmcli", "-g", "GENERAL.CON-UUID", "device", "show", iface).lower() == connection.lower(),
            "Selected NetworkManager connection must be active on the selected NIC.")
    require(run("nmcli", "-g", "connection.type", "connection", "show", "uuid", connection) == "802-3-ethernet",
            "Select a wired Ethernet connection.")
    ethtool = run("ethtool", iface)
    supported = re.search(r"Supports Wake-on:\s*(\S+)", ethtool)
    current = re.search(r"^\s*Wake-on:\s*(\S+)", ethtool, re.MULTILINE)
    require(supported and "g" in supported[1] and current, "NIC does not expose magic-packet WoL support.")
    run("/usr/sbin/sshd", "-t")
    return {"swap": swap, "interface": iface, "connection_uuid": connection,
            "wol_live": current[1],
            "wol_profile": run("nmcli", "-g", "802-3-ethernet.wake-on-lan", "connection", "show", "uuid", connection)}


def system_files(config):
    return {
        Path("/etc/initramfs-tools/conf.d/resume"): read(ROOT / "system/resume/resume.in").replace(
            "@SWAP_UUID@", config["storage"]["swap_uuid"]),
        Path("/etc/systemd/sleep.conf.d/60-workstation.conf"): read(ROOT / "system/sleep/60-workstation.conf"),
        Path("/etc/ssh/sshd_config.d/00-workstation.conf"): read(ROOT / "system/ssh/00-workstation.conf"),
    }


def apply_system(config, changes):
    facts = system_facts(config)  # Complete all hardware checks before the first write.
    print(json.dumps(facts, indent=2))
    if changes.apply:
        changes.save("network-before.json", json.dumps(facts, indent=2) + "\n")
    for path, data in system_files(config).items():
        changes.file(path, data)
    # Always rebuild: a previous run may have failed after writing resume config.
    changes.command("update-initramfs", "-u", "-k", "all")
    changes.command("/usr/sbin/sshd", "-t")
    if changes.apply:
        effective = dict(line.split(" ", 1) for line in run("/usr/sbin/sshd", "-T").splitlines())
        require(effective.get("permitrootlogin") == "no" and effective.get("x11forwarding") == "no",
                "Existing SSH configuration overrides the drop-in; resolve before reloading SSH.")
    changes.command("systemctl", "enable", "--now", "ssh")
    changes.command("systemctl", "reload", "ssh")
    if facts["wol_profile"] not in {"magic", "64", "64 (magic)"}:
        changes.command("nmcli", "connection", "modify", "uuid", facts["connection_uuid"],
                        "802-3-ethernet.wake-on-lan", "magic")
    if facts["wol_live"] != "g":
        changes.command("ethtool", "-s", facts["interface"], "wol", "g")
    print("No reboot or sleep was triggered. Reboot manually into Debian, then run scripts/verify.")


def apply_packages(config, changes):
    names = packages(config)
    print("APT sources must already provide trixie, trixie-updates and trixie-security with non-free-firmware.")
    print("APT may start installed services, including SSH and NetworkManager. Use a local console.")
    source = Path("/etc/apt/sources.list.d/workstation-tailscale.list")
    if config["packages"]["tailscale"]:
        sources = [Path("/etc/apt/sources.list")]
        sources += list(Path("/etc/apt/sources.list.d").glob("*.list"))
        sources += list(Path("/etc/apt/sources.list.d").glob("*.sources"))
        for other in sources:
            if other.exists() and other != source:
                require("pkgs.tailscale.com" not in read(other), f"Reconcile existing Tailscale source {other} first.")
    changes.command("apt-get", "update")
    changes.command("apt-get", "--no-remove", "install", "--yes", *names)
    if config["packages"]["tailscale"]:
        url = "https://pkgs.tailscale.com/stable/debian/trixie.noarmor.gpg"
        print(f"Tailscale signing key: {url} (HTTPS trust on first install; scoped Signed-By)")
        key = Path("/etc/apt/keyrings/workstation-tailscale.gpg")
        if not key.exists():
            if changes.apply:
                result = subprocess.run(["curl", "--fail", "--silent", "--show-error", "--location",
                                         "--proto", "=https", "--proto-redir", "=https", url], capture_output=True, env=ENV)
                require(result.returncode == 0 and result.stdout, "Could not download Tailscale key.")
                changes.file(key, result.stdout)
            else:
                print(f"WOULD download signing key to {key}")
        changes.file(source, "deb [arch=amd64 signed-by=/etc/apt/keyrings/workstation-tailscale.gpg] "
                     "https://pkgs.tailscale.com/stable/debian trixie main\n")
        changes.command("apt-get", "update")
        changes.command("apt-get", "--no-remove", "install", "--yes", "tailscale")
        changes.command("systemctl", "enable", "--now", "tailscaled")
        print("Authenticate separately on Debian: sudo tailscale up (standard OpenSSH; Tailscale SSH is not enabled).")
    if changes.apply:
        changes.save("installed-packages.tsv", run("dpkg-query", "-W", "-f=${binary:Package}\t${Version}\n") + "\n")
        changes.save("kernel.txt", run("uname", "-a") + "\n")


def user_files(home):
    files = {home / ".zshrc": ROOT / "dotfiles/zsh/zshrc",
            home / ".zsh_aliases": ROOT / "dotfiles/zsh/zsh_aliases",
            home / ".tmux.conf": ROOT / "dotfiles/tmux/tmux.conf",
            home / ".vimrc": ROOT / "dotfiles/vim/vimrc",
            home / ".config/i3/config": ROOT / "dotfiles/i3/config",
            home / ".xinitrc": ROOT / "dotfiles/i3/xinitrc"}
    runtime = ROOT / "dotfiles/vim/runtime"
    files.update({home / ".vim" / source.relative_to(runtime): source
                  for source in sorted(runtime.rglob("*")) if source.is_file()})
    return files


def apply_user(changes):
    require(os.geteuid() != 0 and not os.environ.get("SUDO_USER"), "Run user setup as your normal user, without sudo.")
    home = Path.home()
    files = user_files(home)
    conflicts = [str(p) for p, src in files.items() if p.is_symlink() or
                 (p.exists() and (not p.is_file() or p.read_bytes() != src.read_bytes()))]
    require(not conflicts, "Existing dotfiles preserved. Merge or move these yourself before applying:\n" + "\n".join(conflicts))
    for path, source in files.items():
        changes.file(path, source.read_bytes(), 0o755 if path.name == ".xinitrc" else 0o644)
    print("Use startx at a local console. To choose zsh as your login shell: chsh -s /usr/bin/zsh")


def preflight():
    print("Read-only inventory; missing tools are expected before package installation.")
    commands = [("uname", "-a"), ("lsblk", "-o", "NAME,MODEL,SERIAL,SIZE,FSTYPE,UUID,MOUNTPOINTS"),
                ("findmnt", "/"), ("findmnt", "/boot/efi"), ("swapon", "--show", "--bytes"),
                ("mokutil", "--sb-state"), ("nmcli", "-f", "NAME,UUID,TYPE,DEVICE", "connection", "show"),
                ("ip", "-brief", "link")]
    for command in commands:
        print("\n$ " + shlex.join(command))
        try:
            print(run(*command))
        except (SetupError, FileNotFoundError) as error:
            print(f"UNAVAILABLE: {error}")
    for path in ("/sys/class/dmi/id/product_name", "/sys/class/dmi/id/bios_version",
                 "/sys/power/state", "/sys/power/mem_sleep", "/sys/power/disk",
                 "/sys/power/resume", "/sys/kernel/security/lockdown", "/proc/cmdline"):
        print(f"{path}: {read(path).strip() if Path(path).exists() else 'unavailable'}")


def verify(config):
    facts = system_facts(config)
    errors = []

    def check(ok, message):
        print(f"{'PASS' if ok else 'FAIL'}: {message}")
        if not ok:
            errors.append(message)

    for path, data in system_files(config).items():
        check(path.is_file() and path.read_text() == data, str(path))
    # Compare live kernel resume device: a matching file alone cannot prove boot integration.
    device = os.stat(facts["swap"]["name"]).st_rdev
    expected = f"{os.major(device)}:{os.minor(device)}"
    check(read("/sys/power/resume").strip() == expected, f"live resume device is {expected}; reboot after setup")
    check(read("/sys/power/resume_offset").strip() == "0", "partition resume offset is zero")
    image = Path("/boot") / f"initrd.img-{run('uname', '-r')}"
    check(image.is_file() and "conf/conf.d/resume" in run("lsinitramfs", str(image)).splitlines(),
          "running kernel's initramfs contains resume configuration")
    check(facts["wol_live"] == "g", "live magic-packet WoL")
    check(facts["wol_profile"] in {"magic", "64", "64 (magic)"}, "persistent NetworkManager WoL")
    effective = dict(line.split(" ", 1) for line in run("/usr/sbin/sshd", "-T").splitlines())
    check(effective.get("permitrootlogin") == "no", "SSH root login disabled")
    check(effective.get("x11forwarding") == "no", "SSH X11 forwarding disabled")
    for service in ("ssh", "NetworkManager") + (("tailscaled",) if config["packages"]["tailscale"] else ()):
        for state in ("is-active", "is-enabled"):
            try:
                run("systemctl", state, service)
                check(True, f"{service} {state}")
            except SetupError:
                check(False, f"{service} {state}")
    for method in ("CanSuspend", "CanHibernate", "CanSuspendThenHibernate"):
        try:
            reply = run("busctl", "call", "org.freedesktop.login1", "/org/freedesktop/login1",
                        "org.freedesktop.login1.Manager", method)
            check(reply == 's "yes"', f"logind {method}: {reply}")
        except SetupError as error:
            check(False, str(error))
    for name in packages(config) + (["tailscale"] if config["packages"]["tailscale"] else []):
        try:
            check(run("dpkg-query", "-W", "-f=${db:Status-Status}", name) == "installed", f"package {name}")
        except SetupError:
            check(False, f"package {name}")
    if config["packages"]["tailscale"]:
        try:
            status = json.loads(run("tailscale", "status", "--json"))
            check(status.get("BackendState") == "Running", "Tailscale authenticated and running")
        except (SetupError, FileNotFoundError, ValueError) as error:
            check(False, f"Tailscale status: {error}")
    print("Read-only checks cannot establish S3/S4/RTC/WoL reliability. Complete docs/acceptance-tests.md.")
    require(not errors, f"{len(errors)} checks failed.")


def main():
    guard()  # No filesystem changes or Linux commands before host validation.
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("packages", "system", "user", "preflight", "verify"))
    parser.add_argument("--config", type=Path, default=ROOT / "config/workstation.toml")
    parser.add_argument("--apply", action="store_true", help="apply changes; default is preview")
    args = parser.parse_args()
    require(not args.apply or args.phase not in {"preflight", "verify"}, "preflight/verify are read-only.")
    if args.phase == "preflight":
        preflight()
        return
    if args.phase == "user":
        changes = Changes(args.apply, Path.home() / ".local/state/workstation-setup")
        apply_user(changes)
        return
    config = load_config(args.config, identifiers=args.phase in {"system", "verify"})
    require(not args.apply or os.geteuid() == 0, "Use sudo for packages/system --apply on Debian.")
    changes = Changes(args.apply, "/var/lib/workstation-setup")
    if args.phase == "packages":
        apply_packages(config, changes)
    elif args.phase == "system":
        apply_system(config, changes)
    else:
        verify(config)


if __name__ == "__main__":
    try:
        main()
    except (SetupError, OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
