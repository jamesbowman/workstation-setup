# Recovery and rollback

Read before system setup. Keep console access and a rescue USB. Phases are not
transactions: APT changes, service enablement, and initramfs rebuilds can partially
complete. The script does not automatically undo a failed phase.

## Files and records

System run records live in `/var/lib/workstation-setup/run-*`; user runs use
`~/.local/state/workstation-setup/run-*`. `manifest.json` records original copies,
destination paths, prior mode/UID/GID, and whether the destination existed.
Backups are inside mode-700 directories. Inspect the exact run printed by the
command, rather than assuming the most recent run is the one to undo.

For each file being rolled back, preserve intervening edits first. If `existed`
is true, copy its recorded backup to the destination and restore recorded
ownership and mode. If false, remove only the newly created managed file. Then
restore dependent generated state/live settings below. Do not roll back unrelated
files or remove packages blindly.

Reruns replace managed system files but refuse symlinks. User setup refuses
differing existing dotfiles. System reruns deliberately rebuild initramfs even
when the resume file matches, repairing an interrupted earlier rebuild.

## Resume and boot

If resume hangs, edit one Debian GRUB boot entry temporarily and add `noresume`
to the kernel command line. This abandons the previous hibernated session. Do
not use this to access a filesystem still used by another hibernated OS. Try a
previously working kernel in GRUB's advanced menu if a kernel update is involved.

From working Debian, restore/remove `/etc/initramfs-tools/conf.d/resume` according
to its backup. Inspect other RESUME assignments and kernel arguments, then run:

```sh
sudo update-initramfs -u -k all
```

If intentionally disabling hibernation, set `RESUME=none` explicitly instead of
relying on automatic swap selection. Restore/remove the managed sleep drop-in
as appropriate. Remove the temporary noresume edit before testing again; setup
rejects that argument.

If Debian cannot boot, use installer rescue mode, identify **Debian** partitions
by UUID/serial, and enter its rescue shell/chroot to repair configuration and
rebuild initramfs. Do not format drives or reinstall Windows EFI files. Do not
run the full bootstrap in a rescue chroot.

## Networking and SSH

`network-before.json` records the interface, connection UUID, previous profile
WoL property, and live flags. From a local console, restore them using
`nmcli connection modify uuid UUID 802-3-ethernet.wake-on-lan VALUE` and
`ethtool -s INTERFACE wol FLAGS`. If nmcli printed a number and descriptive suffix,
use the numeric value. No deliberate disconnect is needed.

Restore/remove `/etc/ssh/sshd_config.d/00-workstation.conf`, validate with
`sudo /usr/sbin/sshd -t`, and run `sudo systemctl reload ssh`. Keep the old session
open while testing a second login. A validation failure leaves the current
daemon running, but fix disk configuration before reboot/restart. Service
enablement may also need manual rollback; consider access requirements first.

## Packages and Tailscale

Consult `/var/log/apt/history.log`, `/var/log/dpkg.log`, and saved inventories.
Use Debian's normal APT/dpkg recovery for interrupted package transactions before
rerunning packages; do not blindly autoremove or downgrade.

To undo the Tailscale source addition, restore/remove the source and key using
the manifest and refresh APT metadata. This does not uninstall Tailscale or
revoke registration. Explicitly disconnect/revoke the device if intended.
Credentials never belong in repository backups.
