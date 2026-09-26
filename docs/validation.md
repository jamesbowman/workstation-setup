# Repository validation

## Existing installer networking and decimal swap capacity

The portable suite now has 30 passing tests, including ifupdown discovery,
NetworkManager ownership conflicts, optional connection UUIDs, scoped hook
execution with a harmless ethtool stand-in, and preservation of networking during
system setup. The hook passes shell syntax validation. The target's approximately
24 decimal GB swap capacity has a regression test, alongside undersized-swap
rejection. These checks ran on macOS; actual WoL persistence and network-manager
service validation remain target checks.

The target run exposed an unsupported `swapon --json` assumption. Active swap
discovery now uses the documented `--show=NAME --noheadings --raw` interface;
the regression covers empty, single-device, and multiple-device output. Capacity
still comes from lsblk. No swap activation/deactivation is performed. See the
[Debian swapon manual](https://manpages.debian.org/trixie/mount/swapon.8.en.html).

## Dotfile update (2026-09-25)

Personal dotfiles were validated with isolated temporary-home Vim/zsh sessions
and a tmux server using a private socket on macOS. The fixture suite was extended
for vendored Vim assets and aliases; see [dotfile notes](dotfiles.md). Six new
package names were confirmed in Debian trixie:
[tig](https://packages.debian.org/trixie/tig),
[gh](https://packages.debian.org/trixie/gh),
[xfce4-terminal](https://packages.debian.org/trixie/xfce4-terminal),
[fonts-terminus-otb](https://packages.debian.org/trixie/fonts-terminus-otb),
[xclip](https://packages.debian.org/trixie/xclip), and
[scrot](https://packages.debian.org/trixie/scrot).
i3/X11 and physical power tests remain pending on Debian.

## Initial setup validation

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
