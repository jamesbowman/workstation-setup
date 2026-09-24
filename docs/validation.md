# Repository validation

Validated on macOS on 2026-09-24; no Linux installation or power-management
commands were executed on the Mac.

- Portable Python fixture tests: host/release refusal, read-only command guards,
  TOML validation, wrong-disk/EFI rejection, swap requirements, encryption and
  unsupported layout rejection, sleep/resume conflicts, no-mutation previews,
  backups, symlink refusal, user-config preservation, preflight-before-write,
  and rerun behavior after an interrupted initramfs rebuild.
- Shell entry points and xinitrc: POSIX shell syntax checks.
- Zsh configuration: zsh syntax check.
- Python source: syntax parsing on the development interpreter (Python 3.14).
- All 82 manifest package names checked against Debian trixie amd64 main and
  non-free-firmware indexes. `lxpolkit` confirmed separately using its Debian
  package file listing after replacing the unavailable policykit-1-gnome agent.
- Git whitespace checks and repository-relative documentation links checked.

This does **not** establish successful APT dependency resolution, Debian 3.13
execution, i3 configuration validation, service integration, initramfs contents,
boot/resume, hardware acceleration, screen locking, RTC transitions, or WoL.
Those checks require the Debian target and the procedures in
[acceptance-tests.md](acceptance-tests.md). ShellCheck was not installed on the
Mac; the development package profile provides it on Debian.

Before deploying changes beyond this baseline, run on Debian:

```sh
shellcheck -x scripts/bootstrap scripts/preflight scripts/verify scripts/lib/entry.sh
i3 -C -c dotfiles/i3/config
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
```

References used for implementation:

- [Debian installation guide](https://www.debian.org/releases/trixie/amd64/)
- [Debian systemd sleep settings](https://manpages.debian.org/trixie/systemd/systemd-sleep.conf.5.en.html)
- [Debian initramfs-tools RESUME](https://manpages.debian.org/trixie/initramfs-tools-core/initramfs.conf.5.en.html)
- [Kernel sleep states](https://docs.kernel.org/admin-guide/pm/sleep-states.html)
- [NetworkManager Ethernet WoL property](https://networkmanager.dev/docs/api/latest/settings-802-3-ethernet.html)
- [Debian nmcli manual](https://manpages.debian.org/trixie/network-manager/nmcli.1.en.html)
- [Tailscale Debian stable packages](https://pkgs.tailscale.com/stable/#debian-trixie)
- [Debian lxpolkit file list](https://packages.debian.org/trixie/amd64/lxpolkit/filelist)
- [Debian main package index](https://deb.debian.org/debian/dists/trixie/main/binary-amd64/Packages.xz)
- [Debian firmware package index](https://deb.debian.org/debian/dists/trixie/non-free-firmware/binary-amd64/Packages.xz)
