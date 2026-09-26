# Fresh-install prerequisites

Use the [Debian 13 amd64 installer](https://www.debian.org/releases/trixie/amd64/).
Keep a rescue USB available. This repository begins after OS installation; it
does not partition, format, install GRUB, or edit firmware.

## Firmware and drives

1. Record the HP firmware version and inspect HP updates for this exact unit.
   Perform firmware updates separately.
2. Use UEFI mode and turn Secure Boot **off**. Do not enable disk encryption,
   BitLocker/device encryption, LUKS, or encrypted swap on either OS.
3. Look for S3/legacy sleep, LAN wake, and power-saving options that cut NIC
   power. Names and availability vary; do not assume firmware exposes S3.
4. Identify both NVMes by model, serial, and capacity. During Debian installation,
   disconnect the Windows drive when practical so the installer cannot reuse its
   EFI partition. Otherwise verify every partition and bootloader destination.
5. On the **Debian NVMe**, create GPT with an approximately 1 GiB FAT32 EFI System
   Partition mounted at `/boot/efi`, ext4 `/`, and an **approximately 24 GB Linux
   swap partition**. Entering `24 GB` in the installer gives about 22.35 GiB,
   displayed as roughly 22.4G by lsblk; this meets the original requirement.
   A 24 GiB partition (25,769,803,776 bytes) is also accepted. The size check
   allows 1 MiB below 24 decimal GB for installer alignment. Use direct
   partitions; system setup rejects LVM, RAID, encryption, Btrfs, and swapfiles.
6. Have the installer enable swap and add its UUID to `/etc/fstab`. Install
   Debian's UEFI GRUB on the Debian drive's EFI partition. Do not mount the
   Windows EFI partition as `/boot/efi`.

The system phase requires an explicit swap UUID and checks that root, swap, and
the mounted EFI partition share a parent drive. No disk is chosen by its number.

## Base OS

Install standard system utilities, a normal user, sudo, Python 3.13, and Git.
If necessary, install `sudo python3 git` using the root account **on Debian**,
grant the intended administrator sudo access, and log in again. Clone this
repository as the normal user.

Use sources named `trixie`, `trixie-updates`, and `trixie-security`, with `main`
and `non-free-firmware`. Avoid the moving alias `stable`. The scripts preserve
installer sources. Fix unavailable APT candidates before rerunning packages.

The desktop profile supplies Xorg/i3 with `startx` and no display manager. Avoid
another installer desktop unless you intend to reconcile its sleep, screen-lock,
display-manager, and networking configuration yourself.

## Wired networking

Keep the installer's working wired networking. If Ethernet is defined in
`/etc/network/interfaces` or an included file and appears unmanaged in nmcli,
select `manager = "ifupdown"`, set the interface name, and leave `connection_uuid`
empty. System setup installs a per-interface WoL hook and sets the live wake flag
without changing interfaces files, DHCP, routes, DNS, or restarting networking.

If NetworkManager already manages Ethernet, select `manager = "networkmanager"`
and supply the active connection UUID. Both backends are supported; migration is
not required. NetworkManager may manage Wi-Fi while ifupdown manages Ethernet.
Do not allow both managers to own the same interface.

## Dual boot

Disable Windows Fast Startup and fully shut down before switching OS. Test both
systems using the firmware boot menu. Setup does not add OS-prober configuration
or modify Windows EFI files.

Resume **Debian** after hibernating Debian before booting Windows; likewise resume
and shut down hibernated Windows before accessing its filesystems from Linux.
Do not permit writes to the other OS's volumes or shared volumes while an OS
retains a hibernated session. Separate drives do not make this safe.
