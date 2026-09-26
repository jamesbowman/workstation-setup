# Debian 13 workstation setup

Post-install configuration for an **HP EliteDesk 805 G6 Mini**, Ryzen 5 PRO
4650GE, 16 GB RAM, AMD graphics, and NVMe storage. Windows and Debian live on
separate drives. Target: i3/X11, tmux, vim, zsh, Python 3.13, C/C++, Cairo/Pango,
ffmpeg, ImageMagick, LaTeX, Tailscale, and OpenSSH.

The baseline is **unencrypted ext4**, a dedicated **approximately 24 GB swap partition**,
UEFI/GRUB with an independent Debian EFI partition, **Secure Boot off**, wired
ifupdown or NetworkManager networking, S3 suspend, S4 hibernation, a **two-hour**
suspend-then-hibernate delay, and magic-packet Wake-on-LAN. Power and wake
reliability must be demonstrated on the physical machine.

## Start here

Read [installation prerequisites](docs/installation.md), then
[configuration](docs/configuration.md). All commands below are **Debian-only**.
The launchers reject macOS; do not attempt installation on the development Mac.

```sh
cp config/workstation.example.toml config/workstation.toml
./scripts/preflight
./scripts/bootstrap packages                    # preview
sudo ./scripts/bootstrap packages --apply       # local console recommended
```

Fill in the swap UUID, Ethernet interface, and existing network manager in
`config/workstation.toml`, using the preflight output. Leave `connection_uuid`
empty for ifupdown; NetworkManager requires its active connection UUID. Read
[recovery](docs/recovery.md) before the next stage.

```sh
sudo ./scripts/bootstrap system                 # validated preview and diffs
sudo ./scripts/bootstrap system --apply
./scripts/bootstrap user                        # as the desktop user
./scripts/bootstrap user --apply
sudo tailscale up                               # interactive authentication
chsh -s /usr/bin/zsh                             # optional login-shell selection
```

Reboot manually into Debian, then run `sudo ./scripts/verify` and the
[hardware acceptance tests](docs/acceptance-tests.md). Use `startx` from a local
console to enter i3. No display manager is installed.

## Design

- `packages/`: selectable Debian manifests; Tailscale uses its official source.
- `config/`: explicit machine identifiers in TOML; the local copy is ignored by Git.
- `dotfiles/`: personal i3, tmux, vim, and zsh configurations adapted from
  [mysettings and local preferences](docs/dotfiles.md); differing files are preserved.
- `system/`: inspectable sleep, resume, and SSH templates; WoL policy notes.
- `scripts/`: guarded shell entry points and a Python 3.13 standard-library helper
  for TOML, safe argument lists, previews, backups, and validation.
- `tests/`: portable fixture tests, with no real installation commands.
- `docs/`: installation, operation, recovery, and physical acceptance procedures.

Modifying phases preview by default and require `--apply`. System file originals
are backed up per run under `/var/lib/workstation-setup/`. Failures can leave a
partially completed phase; resolve the error and rerun or follow recovery docs.
No formatting, firmware changes, bootloader installation, reboot, or sleep tests
are performed by the scripts.

This reproduces package selections and configuration, **not identical package
versions indefinitely**. Debian security updates remain available. Package runs
save installed versions and kernel information for auditing.

## Development checks (safe on macOS)

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v
for file in scripts/bootstrap scripts/preflight scripts/verify scripts/lib/entry.sh; do
    sh -n "$file"
done
zsh -n dotfiles/zsh/zshrc
git diff --check
```

Tests use temporary directories and fixtures. Debian configuration validation
and hardware acceptance remain target-only.
See [validation scope and pending target checks](docs/validation.md).

For Gforth 0.7.3 compatibility, use the optional
[pinned source-package build](docs/gforth.md). It does not add testing repositories.
