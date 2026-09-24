# Target acceptance tests

Status: **not yet run on hardware**. Save work, use a local console, and keep a
rescue USB available. Invoke each disruptive command yourself. Record date,
BIOS, kernel, Git commit, swap UUID, NIC/driver, displays/peripherals, sender,
and results under `reports/` (ignored by Git). VM/static tests cannot establish
physical reliability.

## Baseline after a manual reboot

1. Run `sudo ./scripts/verify` and resolve failures. An unset live resume device
   may mean you have not rebooted into the rebuilt initramfs.
2. Inspect `systemd-analyze cat-config systemd/sleep.conf` for overrides; effective
   policy must retain deep sleep, platform hibernation, and 2h.
3. Run `startx`. Check resolution and `glxinfo -B` for AMD hardware rendering,
   keyboard/mouse, audio, and networking. Inspect user services `pipewire`,
   `pipewire-pulse`, and `wireplumber` if audio fails.
4. Exercise tmux, vim, zsh, a Python 3.13 venv, and small C/C++ programs. Check
   `pkg-config --modversion cairo pangocairo`, `ffmpeg -version`,
   `convert -version`, and build a small document with `latexmk -pdf`.
5. Test key-authenticated SSH from another computer and over Tailscale. Verify
   the intended user works and root login is denied.
6. Lock with Super+Control+l and verify a password is required. Confirm xss-lock
   is running in i3. Keep identifiable tmux state to test session preservation.

## Power and wake matrix

| Test | Explicit target action | Required observation |
| --- | --- | --- |
| S3/local wake | `systemctl suspend` | Low-power entry, locked preserved session on wake |
| S3/LAN wake | Suspend, then LAN magic packet | Wake without local input; display/network recover |
| S4/local wake | `systemctl hibernate` | Power-down and restored session, not a fresh login |
| S4/LAN wake | Hibernate, then magic packet | Firmware wake and restore of the same image |
| Combined | `systemctl suspend-then-hibernate` | S3, timed RTC wake, S4, successful later resume |
| S5 (optional) | Full shutdown, then magic packet | Power-on, tracked separately from S3/S4 |

A Linux LAN sender with wakeonlan installed can use `wakeonlan MAC_ADDRESS`
with the actual NIC address. Check that the broadcast reaches the target LAN;
do not send through the sleeping target's Tailscale IP.

Repeat each required S3/S4 and WoL test at least **five times**, including an
overnight interval. Repeat with a realistic memory workload after checking free
swap, and with normal peripherals/displays connected. After wake check screen
lock, tmux state, graphics, audio, USB, LAN, SSH, and Tailscale. Inspect:

```sh
journalctl -b -k
journalctl -b -u systemd-suspend.service -u systemd-hibernate.service -u systemd-suspend-then-hibernate.service
```

S3 needs evidence of deep-suspend entry; display blanking is insufficient. S4
needs preserved session state, distinguishing resume from a fresh boot.

## Timer test

First prove independent suspend and hibernate. For a short combined test,
manually create `/etc/systemd/sleep.conf.d/90-workstation-test.conf` on Debian:

```ini
[Sleep]
HibernateDelaySec=2min
```

Invoke the combined verb and leave the machine untouched through hibernation.
Observe RTC wake/transition and inspect logs after resume. Remove the test file,
inspect merged configuration, and perform a full **two-hour** test plus an
overnight test. Run verification again after removing all test overrides.

## Dual boot and acceptance

Fully shut down Debian, boot Windows through the firmware menu, fully shut down
Windows with Fast Startup disabled, then boot Debian and repeat LAN wake tests.
Never switch OS while keeping a hibernated session that might share filesystems.
Confirm independent EFI files remain on each drive.

Record PASS, FAIL, or UNTESTED for every result. Missing S3, failed timed wake,
resume failure, or required WoL failure keeps acceptance incomplete. Do not
substitute s2idle or drop S4 wake to report success.
