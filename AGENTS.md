# Debian 13 workstation setup

## Purpose and target

Build a reproducible, reviewable configuration repository for use after a fresh
Debian 13 installation on an HP EliteDesk 805 G6 Mini:

- AMD Ryzen 5 PRO 4650GE, 16 GB RAM, AMD integrated graphics, NVMe storage.
- Windows and Debian dual-boot on separate NVMe drives.
- Daily environment: i3 on X11, tmux, vim, zsh, Python 3.13, C/C++, Cairo/Pango,
  ffmpeg, ImageMagick, LaTeX, Tailscale, and SSH.
- Approximately 24 GB of disk-backed swap and verified S3 suspend, S4 hibernate,
  suspend-then-hibernate, and Wake-on-LAN.

## Confirmed configuration decisions

- No disk encryption whatsoever, including root, data, and swap. Do not introduce
  encrypted storage or encrypted swap.
- Secure Boot is off. Document this as a firmware prerequisite and verify it on
  the target; do not automate firmware changes.
- Suspend-then-hibernate should transition to hibernation after two hours.
- The user approved the proposed repository layout and implementation plan.

## Current phase and approval boundary

Implementation of the approved plan is authorized. Develop and validate the
repository on macOS, but perform installation and hardware acceptance testing
only on the Debian target. Do not silently choose destructive defaults.

## Host and execution safety

- Development currently takes place on macOS. Never run Linux installation,
  package-management, bootloader, partitioning, swap, systemd, or power-management
  commands on this Mac. Treat Debian commands in documentation as target-only.
- After plan approval, local validation must be non-mutating toward the host:
  static checks, fixture tests, and explicitly suitable isolated environments.
- Future entry points must reject unsupported operating systems and releases
  before any changes. Separate unprivileged user setup from privileged changes.
- Do not partition or format drives, change firmware settings, or modify Windows
  volumes or its EFI files as part of post-install automation. Never select a
  target disk by enumeration order. Document installer prerequisites separately.
- Never trigger suspend, hibernate, reboot, or power-off during ordinary setup or
  checks. Disruptive hardware tests require explicit invocation on the target.

## Implementation requirements after approval

- Prefer Debian 13 packages and documented upstream interfaces. Record package
  choices, external repositories, versions where appropriate, and prerequisites.
  Distinguish repeatable configuration from immutable package reproduction.
- Make changes idempotent, scoped, inspectable, and reversible where practical.
  Preserve existing user configuration; avoid unconditional overwrites and
  duplication. Explain proposed changes before privileged mutations.
- Store machine-specific choices separately from reusable configuration. Do not
  commit passwords, SSH private keys, Tailscale credentials, or other secrets.
- Use virtual environments for Python project dependencies; do not overwrite the
  Debian-managed Python installation with global pip installs.
- Restrict remote-access changes to the intended policy; preserve working SSH
  access and make Tailscale authentication an explicit interactive step.
- Discover the actual filesystem, encryption, bootloader, swap, kernel power
  states, and network device before configuring resume or Wake-on-LAN.
- Treat the swap size as an approximately 24 GB disk-backed requirement; document
  the selected unit and swap strategy. Zram alone does not satisfy this target.
- Hibernation design must account for stable resume identifiers, swapfile offsets
  when applicable, and initramfs. Verify that storage is unencrypted and Secure
  Boot is off, and report any remaining kernel restrictions.
- S3, S4, suspend-then-hibernate, and Wake-on-LAN are acceptance targets, not
  promises based on the model name. Verify firmware and kernel support on the
  actual machine; report unsupported states rather than silently substituting
  another state. Test wake behavior separately for each relevant power state.
- Never access a hibernated operating system's filesystems from the other OS.
  Document Windows Fast Startup and shared-volume risks for dual boot.
- Document recovery and rollback before changes affecting boot, resume, or
  remote access. Validate basic suspend and hibernate independently before the
  combined suspend-then-hibernate test.

## Verification and communication

- Consult current Debian and upstream documentation for implementation details.
- Keep static validation separate from hardware acceptance tests. A successful
  syntax check or VM test does not establish physical sleep/wake reliability.
- Report what changed, what was tested, and what still needs target validation.
- Keep target installation and disruptive hardware tests separate from repository
  development. Plan approval does not authorize running them on this Mac.
