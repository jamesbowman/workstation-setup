# Suspend, resume, and Wake-on-LAN

Setup writes `/etc/initramfs-tools/conf.d/resume` with the selected swap UUID
and rebuilds installed kernels' initramfs images. Debian's
[RESUME setting](https://manpages.debian.org/trixie/initramfs-tools-core/initramfs.conf.5.en.html)
selects that device. A dedicated swap partition needs no file offset. Conflicting
resume kernel arguments or other RESUME assignments stop setup. The system phase
does not edit GRUB/EFI files; kernel package installation can run Debian's normal
boot maintenance hooks.

The sleep drop-in selects `mem`, `MemorySleepMode=deep`, ACPI platform hibernation,
and `HibernateDelaySec=2h`. The timed transition needs working RTC/firmware wake.
These are supported configuration options in
[Debian 13 systemd](https://manpages.debian.org/trixie/systemd/systemd-sleep.conf.5.en.html).

On Debian, `systemctl suspend` requests S3, `systemctl hibernate` requests S4,
and `systemctl suspend-then-hibernate` requests the combined mode. **Ordinary
suspend does not acquire the two-hour timer.** No idle or power-button policy is
changed. No setup or verification script triggers a power transition.

Existing conflicting sleep settings stop system setup and verification, even
when a later drop-in could override them. Reconcile those files explicitly;
remove the temporary acceptance-test timer override before running verification.

S3 must be exposed as `deep` in `/sys/power/mem_sleep`; `s2idle` does not meet this
requirement. Setup stops if deep is absent. A kernel parameter cannot create an
unsupported firmware state. See [kernel sleep states](https://docs.kernel.org/admin-guide/pm/sleep-states.html).
`[s2idle] deep` before the first sleep is acceptable: systemd selects deep when
the operation begins.

24 decimal GB (about 22.35 GiB) exceeds 16 GiB RAM, but available swap and memory
pressure still matter. A partition created as `24 GB` does not need resizing to
24 GiB for this setup; both sizes satisfy the requested approximate capacity.
Inspect `free -h` and `swapon --show` before loaded tests; do not bypass systemd's
hibernation checks. Setup never creates, resizes, clears, or activates swap.

## Wake-on-LAN

Setup enables magic-packet wake through the existing network manager: an if-up
hook for ifupdown, or the selected active Ethernet profile for NetworkManager.
It sets the live NIC flag with ethtool without cycling the connection.
The previous settings are saved. Test after reboot, S3, and S4: drivers/firmware
can clear wake flags across transitions. S5 wake is an independent optional test.

Use wired Ethernet and a powered LAN sender. Record the NIC MAC and observe link
LEDs while sleeping. The workstation's own Tailscale daemon cannot receive while
asleep. For remote wake, connect to an always-on tailnet peer on the LAN and have
that peer send a local magic packet. A connection to the sleeping workstation's
Tailscale address cannot wake it.

For failures, inspect firmware LAN wake/power-saving settings, ethtool capability
and flags, switch connectivity, and broadcast delivery. Windows driver settings
can also affect NIC state when leaving Windows; test the dual-boot sequence.
`wol g` alone does not prove successful wake.
