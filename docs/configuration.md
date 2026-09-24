# Configuration and operation

All target commands here are for Debian. Use a local console for initial package
and network setup. Review repository changes before running it as root.

| Command | Privilege | Default behavior |
| --- | --- | --- |
| `scripts/preflight` | user; sudo for fuller output | Read-only inventory; missing tools reported |
| `scripts/bootstrap packages` | sudo for `--apply` | Preview packages and external source |
| `scripts/bootstrap system` | sudo, including preview | Validate hardware; display diffs and commands |
| `scripts/bootstrap user` | normal user, never sudo | Preview dotfiles; stop on differing files |
| `scripts/verify` | sudo | Read-only state checks; nonzero on failure |

Use `--config /absolute/path/to/workstation.toml` to select a configuration for
packages/system/verify. Preflight and user setup need no TOML. No phase runs
another implicitly. Resolve failures before proceeding.

Copy the example TOML. Empty identifiers are allowed for package installation;
system/verify require actual UUIDs and the wired interface. Obtain them from
preflight, `lsblk -f`, and `nmcli -f NAME,UUID,TYPE,DEVICE connection show`.
No credentials belong in TOML, and it is never evaluated as shell code.

## Packages and reproducibility

The base profile is mandatory. Omit other profiles to reduce installation size;
add them and rerun later. LaTeX uses a practical selection, not `texlive-full`.
Desktop includes Mesa, PipeWire, Xorg, i3, screen locking, a policy agent, and
NetworkManager's tray applet. Verify actual graphics/NIC devices with `lspci -nnk`.

APT uses recommendations and `--no-remove`; no distribution upgrade or automatic
package removal is requested. Preview lists package requests; dependencies are
resolved only on Debian. Package scripts can start SSH, NetworkManager, and
Tailscale. Use a local console, since installing networking packages can affect
an existing setup.

Tailscale uses its official stable trixie source. On first installation its key
is fetched over HTTPS and scoped with `signed-by`. No downloaded shell script
is executed. Existing Tailscale sources must be reconciled first. Existing keys
are not silently refreshed: inspect upstream key changes after signature errors.
The initial key download trusts the official HTTPS endpoint. See
[upstream instructions](https://pkgs.tailscale.com/stable/#debian-trixie).
`tailscale = false` skips installation; it does not remove or disconnect Tailscale.

Package versions follow APT sources. Successful package runs save
`installed-packages.tsv` and `kernel.txt` under `/var/lib/workstation-setup/run-*`.
Preserve these, the Git commit, local TOML, APT sources, firmware version, and
acceptance results for auditing. Reports containing machine details stay out of
Git. Identical binary reproduction would require a deliberate Debian snapshot
date and retained third-party packages; this project does not freeze security
updates or claim immutable binary reproduction. Repeat acceptance after kernel
and firmware updates.

## Remote access

The SSH drop-in disables root login and X11 forwarding, preserving the existing
user authentication/listener policy. Effective settings are validated before
reload. This is **not** a tailnet-only firewall: standard OpenSSH may accept LAN
connections. No router ports are opened.

Install your public key in `~/.ssh/authorized_keys` (directory mode 700, file
600). Test a second key-authenticated session before optionally disabling
passwords yourself. Keep console access and never commit private keys.

Run `sudo tailscale up` interactively and check `tailscale status`. This provides
ordinary tailnet access to OpenSSH, not Tailscale SSH, subnet routing, or an exit
node. Tailnet policy must permit the intended connections.

## User environment

User setup installs `.zshrc`, `.tmux.conf`, `.vimrc`, `.config/i3/config`, and
`.xinitrc` only when absent or identical. Any differing file stops the entire
phase before writes; inspect, manually merge or rename, then rerun. The scripts
do not overwrite your prior settings.

Run `startx` from a local console. Super+Enter opens xterm, Super+d runs dmenu,
and Super+Control+l locks. `xss-lock` integrates screen locking with suspend.
No idle-sleep policy or sleep hotkey is installed before hardware acceptance.
Test locking before relying on unattended suspend. Select zsh with
`chsh -s /usr/bin/zsh`; local additions can use `~/.zshrc.local` and
`~/.vimrc.local`.

Keep Python 3.13 Debian-managed. For each project:

```sh
python3.13 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
```

Use pipx for isolated applications. System Python has the distro Cairo/GI/Pango
bindings; a venv can explicitly use `--system-site-packages` when needed. Never
use `sudo pip` or `--break-system-packages`. ImageMagick's distro security policy
is preserved; PDF operations may need a separate tool or a reviewed policy.
