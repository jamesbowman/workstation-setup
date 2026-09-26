"""Portable tests: temporary files and mocked commands, never live Linux setup."""

import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("workstation", ROOT / "scripts/lib/workstation.py")
ws = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ws)
SWAP_UUID = "22222222-2222-2222-2222-222222222222"


class QuietTest(unittest.TestCase):
    def setUp(self):
        output = contextlib.redirect_stdout(io.StringIO())
        output.__enter__()
        self.addCleanup(output.__exit__, None, None, None)
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)


class GuardTests(QuietTest):
    def test_mac_rejected_before_os_release_or_commands(self):
        with patch.object(ws.platform, "system", return_value="Darwin"), \
                patch.object(ws, "read") as read, patch.object(ws.subprocess, "run") as execute:
            with self.assertRaisesRegex(ws.SetupError, "macOS"):
                ws.main()
            read.assert_not_called()
            execute.assert_not_called()

    def test_unsupported_linux_rejected(self):
        for release in ('ID=ubuntu\nVERSION_ID="13"', 'ID=debian\nVERSION_ID="12"'):
            with self.subTest(release=release), patch.object(ws.platform, "system", return_value="Linux"), \
                    patch.object(ws, "read", return_value=release), patch.object(ws.subprocess, "run") as execute:
                with self.assertRaisesRegex(ws.SetupError, "Only Debian 13"):
                    ws.guard()
                execute.assert_not_called()

    def test_read_only_commands_reject_apply(self):
        for phase in ("preflight", "verify"):
            with self.subTest(phase=phase), patch.object(ws, "guard"), \
                    patch.object(ws.sys, "argv", ["workstation.py", phase, "--apply"]), \
                    patch.object(ws.subprocess, "run") as execute:
                with self.assertRaisesRegex(ws.SetupError, "read-only"):
                    ws.main()
                execute.assert_not_called()


class GforthTests(QuietTest):
    def test_preview_does_not_download_build_or_write(self):
        with patch.object(ws.os, "geteuid", return_value=1000), \
                patch.dict(ws.os.environ, {}, clear=True), \
                patch.object(ws.subprocess, "run") as execute, \
                patch.object(ws.tempfile, "mkdtemp") as create:
            ws.build_gforth(False)
            execute.assert_not_called()
            create.assert_not_called()

    def test_source_checksum_mismatch_is_rejected(self):
        source = self.directory / "source.tar.xz"
        source.write_bytes(b"different archive")
        with self.assertRaisesRegex(ws.SetupError, "SHA256 mismatch"):
            ws.check_sha256(source, "0" * 64)
        ws.check_sha256(source, ws.hashlib.sha256(source.read_bytes()).hexdigest())

    def test_build_refuses_root_before_running_commands(self):
        with patch.object(ws.os, "geteuid", return_value=0), \
                patch.object(ws.subprocess, "run") as execute:
            with self.assertRaisesRegex(ws.SetupError, "without sudo"):
                ws.build_gforth(True)
            execute.assert_not_called()


class ConfigTests(QuietTest):
    def test_ifupdown_needs_no_connection_uuid_and_old_configs_still_work(self):
        template = (ROOT / "config/workstation.example.toml").read_text()
        configured = template.replace('swap_uuid = ""', f'swap_uuid = "{SWAP_UUID}"').replace(
            'interface = ""', 'interface = "eno1"')
        path = self.directory / "config.toml"
        path.write_text(configured)
        config = ws.load_config(path, identifiers=True)
        self.assertEqual(config["network"]["manager"], "ifupdown")
        self.assertIn("ifupdown", ws.packages(config))
        old = "\n".join(line for line in configured.splitlines() if not line.startswith("manager ="))
        path.write_text(old)
        with self.assertRaisesRegex(ws.SetupError, "connection_uuid"):
            ws.load_config(path, identifiers=True)
        path.write_text(old.replace('connection_uuid = ""', f'connection_uuid = "{SWAP_UUID}"'))
        self.assertEqual(ws.load_config(path, identifiers=True)["network"]["manager"], "networkmanager")

    def test_example_allows_package_preview_but_not_system(self):
        path = ROOT / "config/workstation.example.toml"
        config = ws.load_config(path)
        self.assertIn("python3.13", ws.packages(config))
        with self.assertRaisesRegex(ws.SetupError, "real UUID"):
            ws.load_config(path, identifiers=True)

    def test_unknown_keys_and_injection_are_rejected(self):
        template = (ROOT / "config/workstation.example.toml").read_text()
        variants = [template + '\nunknown = true\n',
                    template.replace('swap_uuid = ""', 'swap_uuid = "$(touch /tmp/unsafe)"'),
                    template.replace('interface = ""', 'interface = "--help"'),
                    template.replace('"base", ', ''),
                    template.replace('tailscale = true', 'tailscale = "yes"')]
        for text in variants:
            with self.subTest(text=text):
                path = self.directory / "config.toml"
                path.write_text(text)
                with self.assertRaises(ws.SetupError):
                    ws.load_config(path)


class NetworkTests(QuietTest):
    def setUp(self):
        super().setUp()
        self.config = {"network": {"manager": "ifupdown", "interface": "eno1", "connection_uuid": ""},
                       "storage": {"swap_uuid": SWAP_UUID}}
        self.responses = {
            ("ifquery", "--no-mappings", "eno1"): "",
            ("ifquery", "--state", "eno1"): "eno1=eno1",
            ("nmcli", "-g", "GENERAL.STATE", "device", "show", "eno1"): "10 (unmanaged)",
            ("ethtool", "eno1"): "Supports Wake-on: g\nWake-on: d\n",
        }

    def test_ifupdown_active_with_nm_unmanaged_or_absent(self):
        for returncode in (0, 3, 4):
            with self.subTest(returncode=returncode), patch.object(ws.shutil, "which", return_value="/usr/sbin/ifquery"), \
                    patch.object(ws.subprocess, "run", return_value=Mock(returncode=returncode)), \
                    patch.object(ws, "run", side_effect=lambda *args: self.responses[args]) as command:
                facts = ws.network_facts(self.config)
                self.assertEqual(facts["manager"], "ifupdown")
                self.assertEqual(facts["wol_live"], "d")
                self.assertIsNone(facts["wol_profile"])
                if returncode:
                    self.assertFalse(any(call.args[0] == "nmcli" for call in command.call_args_list))

    def test_dual_ownership_is_rejected(self):
        self.responses[("nmcli", "-g", "GENERAL.STATE", "device", "show", "eno1")] = "100 (connected)"
        with patch.object(ws.shutil, "which", return_value="/usr/sbin/ifquery"), \
                patch.object(ws.subprocess, "run", return_value=Mock(returncode=0)), \
                patch.object(ws, "run", side_effect=lambda *args: self.responses[args]):
            with self.assertRaisesRegex(ws.SetupError, "unmanaged"):
                ws.network_facts(self.config)

    def test_ifupdown_must_record_interface_as_up(self):
        self.responses[("ifquery", "--state", "eno1")] = ""
        with patch.object(ws.shutil, "which", return_value="/usr/sbin/ifquery"), \
                patch.object(ws, "run", side_effect=lambda *args: self.responses[args]):
            with self.assertRaisesRegex(ws.SetupError, "recorded as up"):
                ws.network_facts(self.config)

    def test_ifupdown_apply_only_changes_wake_flag_and_installs_executable_hook(self):
        facts = {"manager": "ifupdown", "interface": "eno1", "connection_uuid": "",
                 "wol_live": "d", "wol_profile": None}
        changes = Mock(apply=True)
        with patch.object(ws, "system_facts", return_value=facts), \
                patch.object(ws, "run", return_value="permitrootlogin no\nx11forwarding no"):
            ws.apply_system(self.config, changes)
        hooks = [call for call in changes.file.call_args_list if call.args[0] == ws.WOL_HOOK]
        self.assertEqual(len(hooks), 1)
        self.assertEqual(hooks[0].args[2], 0o755)
        self.assertIn('"eno1"', hooks[0].args[1])
        changes.command.assert_any_call("ethtool", "-s", "eno1", "wol", "g")
        for call in changes.command.call_args_list:
            self.assertNotIn(call.args[0], {"nmcli", "ifup", "ifdown", "ip"})
            self.assertFalse("NetworkManager" in call.args or "networking" in call.args)
        self.assertNotIn(Path("/etc/network/interfaces"), [call.args[0] for call in changes.file.call_args_list])

    def test_hook_skips_other_interfaces_and_targets_selected_interface(self):
        # Run the shell hook with a harmless stand-in, never the host's ethtool.
        import os
        import subprocess
        hook = ws.system_files(self.config)[ws.WOL_HOOK]
        marker = self.directory / "called"
        stub = self.directory / "ethtool-stub"
        stub.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$MARKER"\n')
        stub.chmod(0o755)
        hook = hook.replace("/usr/sbin/ethtool", str(stub))
        script = self.directory / "hook"
        script.write_text(hook)
        for interface in ("lo", "wlp4s0", "--all", ""):
            subprocess.run(["sh", str(script)], env=dict(os.environ, IFACE=interface, MARKER=str(marker)), check=True)
            self.assertFalse(marker.exists())
        subprocess.run(["sh", str(script)], env=dict(os.environ, IFACE="eno1", MARKER=str(marker)), check=True)
        self.assertEqual(marker.read_text(), "-s\neno1\nwol\ng\n")


class StorageTests(QuietTest):
    def test_active_swap_uses_supported_read_only_output(self):
        for output, expected in (("", []),
                                 ("/dev/nvme0n1p2\n", ["/dev/nvme0n1p2"]),
                                 ("/dev/nvme0n1p2\n/dev/zram0\n", ["/dev/nvme0n1p2", "/dev/zram0"])):
            with self.subTest(output=output), patch.object(ws, "run", return_value=output) as command:
                self.assertEqual(ws.active_swap_devices(), expected)
                command.assert_called_once_with("swapon", "--show=NAME", "--noheadings", "--raw")

    def setUp(self):
        super().setUp()
        self.devices = ws.flatten(json.loads((ROOT / "tests/fixtures/storage.json").read_text())["blockdevices"])
        self.options = dict(swap_uuid=SWAP_UUID, root_device="/dev/nvme1n1p2", efi_device="/dev/nvme1n1p1",
                            active=["/dev/nvme1n1p3"], persistent=["/dev/nvme1n1p3"])

    def test_debian_can_be_second_drive(self):
        result = ws.validate_storage(self.devices, **self.options)
        self.assertEqual(result["name"], "/dev/nvme1n1p3")

    def test_decimal_24gb_swap_is_accepted(self):
        # Conservative regression using the target's reported usable swap size.
        swap = next(d for d in self.devices if d.get("uuid") == SWAP_UUID)
        swap["size"] = 23_999_803_392
        self.assertEqual(ws.validate_storage(self.devices, **self.options), swap)

    def test_swap_below_alignment_tolerance_is_rejected(self):
        swap = next(d for d in self.devices if d.get("uuid") == SWAP_UUID)
        swap["size"] = 24_000_000_000 - 1024**2 - 1
        with self.assertRaisesRegex(ws.SetupError, "24 GB"):
            ws.validate_storage(self.devices, **self.options)

    def test_wrong_efi_unknown_swap_inactive_or_nonpersistent(self):
        for change in ({"efi_device": "/dev/nvme0n1p1"}, {"swap_uuid": "unknown"},
                       {"active": []}, {"persistent": []}, {"active": ["/dev/nvme1n1p3", "/swapfile"]}):
            with self.subTest(change=change), self.assertRaises(ws.SetupError):
                ws.validate_storage(self.devices, **(self.options | change))

    def test_undersized_wrong_disk_or_nonpartition_swap(self):
        for change in ({"size": 16 * ws.GIB}, {"pkname": "/dev/nvme0n1"}, {"type": "lvm"}, {"fstype": "ext4"}):
            devices = copy.deepcopy(self.devices)
            next(d for d in devices if d.get("uuid") == SWAP_UUID).update(change)
            with self.subTest(change=change), self.assertRaises(ws.SetupError):
                ws.validate_storage(devices, **self.options)

    def test_duplicate_uuid_encryption_and_btrfs_rejected(self):
        variants = []
        duplicate = copy.deepcopy(self.devices)
        duplicate.append(dict(next(d for d in duplicate if d.get("uuid") == SWAP_UUID), name="/dev/sda3"))
        variants.append(duplicate)
        encrypted = copy.deepcopy(self.devices)
        encrypted[0]["fstype"] = "crypto_LUKS"
        variants.append(encrypted)
        btrfs = copy.deepcopy(self.devices)
        next(d for d in btrfs if d["name"] == "/dev/nvme1n1p2")["fstype"] = "btrfs"
        variants.append(btrfs)
        for devices in variants:
            with self.subTest(devices=devices), self.assertRaises(ws.SetupError):
                ws.validate_storage(devices, **self.options)


class ConflictTests(QuietTest):
    def test_active_sleep_override_blocks_setup(self):
        template = (ROOT / "system/sleep/60-workstation.conf").read_text()

        def content(path):
            if Path(path) == ROOT / "system/sleep/60-workstation.conf":
                return template
            return "[Sleep]\n# HibernateDelaySec=2h\nHibernateDelaySec=2min\n"

        with patch.object(ws.Path, "glob", return_value=[]), \
                patch.object(ws.Path, "is_file", return_value=True), patch.object(ws, "read", side_effect=content):
            with self.assertRaisesRegex(ws.SetupError, "HibernateDelaySec=2min"):
                ws.check_sleep_conflicts()

    def test_commented_sleep_defaults_do_not_override(self):
        self.assertEqual(ws.sleep_assignments("[Sleep]\n# MemorySleepMode=s2idle\n; AllowSuspend=no\n"), [])

    def test_conflicting_kernel_resume_prevents_setup(self):
        for cmdline in ("root=UUID=example noresume", "resume=UUID=wrong", "resume_offset=42"):
            with self.subTest(cmdline=cmdline), patch.object(ws.Path, "glob", return_value=[]), \
                    patch.object(ws.Path, "exists", return_value=True), patch.object(ws, "read", return_value=cmdline):
                with self.assertRaises(ws.SetupError):
                    ws.check_resume_conflicts(SWAP_UUID)


class ChangeTests(QuietTest):
    def test_preview_never_writes_or_runs_commands(self):
        destination = self.directory / "etc/settings"
        state = self.directory / "state"
        changes = ws.Changes(False, state)
        with patch.object(ws.subprocess, "run") as execute:
            self.assertTrue(changes.file(destination, "new\n"))
            changes.command("apt-get", "install", "example")
            execute.assert_not_called()
        self.assertFalse(destination.exists())
        self.assertFalse(state.exists())

    def test_atomic_backup_and_identical_rerun(self):
        destination = self.directory / "settings"
        destination.write_text("original\n")
        destination.chmod(0o640)
        changes = ws.Changes(True, self.directory / "state")
        self.assertTrue(changes.file(destination, "managed\n"))
        manifest = json.loads((changes.backup / "manifest.json").read_text())
        self.assertEqual(Path(manifest[0]["backup"]).read_text(), "original\n")
        self.assertEqual(manifest[0]["mode"], 0o640)
        self.assertEqual(destination.read_text(), "managed\n")
        second = ws.Changes(True, self.directory / "state")
        self.assertFalse(second.file(destination, "managed\n"))
        self.assertIsNone(second.backup)

    def test_symlink_target_preserved(self):
        original = self.directory / "original"
        original.write_text("keep")
        link = self.directory / "link"
        link.symlink_to(original)
        with self.assertRaisesRegex(ws.SetupError, "symlink"):
            ws.Changes(True, self.directory / "state").file(link, "replace")
        self.assertEqual(original.read_text(), "keep")

    def test_user_conflict_blocks_all_writes(self):
        home = self.directory
        (home / ".vimrc").write_text("personal vim settings")
        changes = ws.Changes(True, home / "state")
        with patch.object(ws.os, "geteuid", return_value=1000), patch.object(ws.Path, "home", return_value=home), \
                patch.dict(ws.os.environ, {}, clear=True):
            with self.assertRaisesRegex(ws.SetupError, "Existing dotfiles preserved"):
                ws.apply_user(changes)
        self.assertFalse((home / ".zshrc").exists())
        self.assertFalse((home / "state").exists())

    def test_failed_system_preflight_prevents_any_mutation(self):
        changes = Mock()
        with patch.object(ws, "system_facts", side_effect=ws.SetupError("S3 unsupported")):
            with self.assertRaisesRegex(ws.SetupError, "S3 unsupported"):
                ws.apply_system({}, changes)
        self.assertEqual(changes.mock_calls, [])

    def test_user_runtime_and_aliases_install_and_repeat_cleanly(self):
        home = self.directory
        (home / ".vim/plugin").mkdir(parents=True)
        unrelated = home / ".vim/plugin/personal.vim"
        unrelated.write_text('" Personal plugin\n')
        with patch.object(ws.os, "geteuid", return_value=1000), patch.object(ws.Path, "home", return_value=home), \
                patch.dict(ws.os.environ, {}, clear=True):
            ws.apply_user(ws.Changes(True, home / "state"))
            for path in (".zsh_aliases", ".vim/plugin/mru.vim", ".vim/doc/mru.txt", ".vim/compiler/python.vim"):
                self.assertTrue((home / path).is_file(), path)
            second = ws.Changes(True, home / "state")
            ws.apply_user(second)
            self.assertIsNone(second.backup)
        self.assertEqual(unrelated.read_text(), '" Personal plugin\n')

    def test_existing_plugin_conflict_blocks_user_install(self):
        home = self.directory
        plugin = home / ".vim/plugin/mru.vim"
        plugin.parent.mkdir(parents=True)
        plugin.write_text('" Locally edited MRU plugin\n')
        with patch.object(ws.os, "geteuid", return_value=1000), patch.object(ws.Path, "home", return_value=home), \
                patch.dict(ws.os.environ, {}, clear=True):
            with self.assertRaisesRegex(ws.SetupError, "Existing dotfiles preserved"):
                ws.apply_user(ws.Changes(True, home / "state"))
        self.assertFalse((home / ".zshrc").exists())
        self.assertEqual(plugin.read_text(), '" Locally edited MRU plugin\n')

    def test_successful_system_plan_never_executes_or_sleeps(self):
        facts = {"swap": {}, "interface": "enp2s0", "connection_uuid": SWAP_UUID,
                 "wol_live": "d", "wol_profile": "default"}
        changes = ws.Changes(False, self.directory / "state")
        with patch.object(ws, "system_facts", return_value=facts), \
                patch.object(ws, "system_files", return_value={self.directory / "resume": "RESUME=UUID=example\n"}), \
                patch.object(ws.subprocess, "run") as execute:
            ws.apply_system({}, changes)
            execute.assert_not_called()
        self.assertFalse((self.directory / "resume").exists())

    def test_unchanged_resume_still_rebuilds_after_interrupted_run(self):
        facts = {"swap": {}, "interface": "enp2s0", "connection_uuid": SWAP_UUID,
                 "wol_live": "g", "wol_profile": "64 (magic)"}
        changes = Mock(apply=True)
        changes.file.return_value = False
        with patch.object(ws, "system_facts", return_value=facts), \
                patch.object(ws, "system_files", return_value={}), \
                patch.object(ws, "run", return_value="permitrootlogin no\nx11forwarding no"):
            ws.apply_system({}, changes)
        changes.command.assert_any_call("update-initramfs", "-u", "-k", "all")
        self.assertFalse(any(call.args[0] in {"nmcli", "ethtool"} for call in changes.command.call_args_list))


if __name__ == "__main__":
    unittest.main()
