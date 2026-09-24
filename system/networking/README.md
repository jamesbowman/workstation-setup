# Wired Wake-on-LAN

The system phase modifies only `802-3-ethernet.wake-on-lan` on the explicitly
selected, active NetworkManager connection, setting it to `magic`. It also sets
the current NIC state with `ethtool -s INTERFACE wol g`. It never cycles the
connection or changes addresses, routes, DNS, or interface ownership.

The prior profile property and live NIC wake flags are recorded in the run's
`network-before.json`. A reboot verifies profile persistence; S3/S4 tests verify
firmware and driver behavior. Other network managers require a separate design.
