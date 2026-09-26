# Wired Wake-on-LAN

Select the existing manager in TOML; migrating a working interface is unnecessary.

- **ifupdown:** install `ifupdown-wol.in` as the executable
  `/etc/network/if-up.d/workstation-wol`, scoped to the configured interface.
  Leave `connection_uuid` empty. No edits to interfaces files are made.
- **networkmanager:** change only `802-3-ethernet.wake-on-lan` on the explicitly
  selected, active connection, setting it to `magic`.

Both paths set the current NIC state with `ethtool -s INTERFACE wol g`. Neither
cycles the connection nor changes addresses, routes, DNS, or interface ownership.
If NetworkManager is running alongside ifupdown it must leave the selected
Ethernet device unmanaged. Ordinary ifupdown if-up hooks must be enabled.

The prior profile property and live NIC wake flags are recorded in the run's
`network-before.json` (the profile property is null for ifupdown). A reboot
verifies persistence; S3/S4 tests verify firmware and driver behavior. Other
network managers require a separate design.

References: [ifquery](https://manpages.debian.org/trixie/ifupdown/ifquery.8.en.html)
and [ifupdown hooks](https://manpages.debian.org/trixie/ifupdown/interfaces.5.en.html).
