import tempfile
import unittest
from pathlib import Path
from unittest import mock

from couch_remote import cli


class ConfigTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.patches = [
            mock.patch.object(cli, "BASE", self.base),
            mock.patch.object(cli, "DEVICES", self.base / "devices.json"),
            mock.patch.object(cli, "LEGACY_DEVICES", self.base / "missing-legacy.json"),
            mock.patch.object(cli, "LEGACY_CERT", self.base / "missing-client.pem"),
            mock.patch.object(cli, "LEGACY_KEY", self.base / "missing-key.pem"),
        ]
        for patcher in self.patches:
            patcher.start()

    def tearDown(self):
        for patcher in reversed(self.patches):
            patcher.stop()
        self.tmp.cleanup()

    def test_first_run_config_is_empty(self):
        config = cli.load_config()
        self.assertEqual(config, {"default": "", "devices": {}})

    def test_put_device_creates_default_androidtv_profile(self):
        device = cli.put_device("Test TV", "192.168.1.20", "aa:bb:cc:dd:ee:ff")

        self.assertEqual(device["backend"], "androidtv")
        self.assertEqual(device["host"], "192.168.1.20")
        self.assertEqual(device["mac"], "aa:bb:cc:dd:ee:ff")
        self.assertEqual(cli.get_device()["name"], "Test TV")
        self.assertIn("volume_up", device["actions"])

    def test_action_mapping_and_reset(self):
        cli.put_device("Test TV", "192.168.1.20")
        cli.set_action_mapping(None, "subtitle", ["TV_MEDIA_CONTEXT_MENU"])

        self.assertEqual(cli.get_device()["actions"]["subtitle"], "TV_MEDIA_CONTEXT_MENU")

        cli.reset_action_mapping(None, "subtitle")
        self.assertEqual(cli.get_device()["actions"]["subtitle"], cli.DEFAULT_ACTION_MAP["subtitle"])

    def test_macro_mapping(self):
        cli.put_device("Test TV", "192.168.1.20")
        cli.set_action_mapping(None, "service-menu", ["settings", "down", "ok"])

        device = cli.get_device()
        self.assertEqual(device["macros"]["service_menu"], ["SETTINGS", "DPAD_DOWN", "DPAD_CENTER"])
        self.assertEqual(cli.resolve_action(device, "service-menu"), ["SETTINGS", "DPAD_DOWN", "DPAD_CENTER"])

    def test_subcommand_options_are_preserved(self):
        parser = cli.build_parser()
        args = parser.parse_args(["pair", "--name", "Test TV", "--host", "192.168.1.20"])

        self.assertEqual(args.args, ["pair", "--name", "Test TV", "--host", "192.168.1.20"])

    def test_snap_refresh_relocates_and_persists_copied_credentials(self):
        current = self.base / "snap/couch-remote/4"
        base = current / ".config/couch-remote"
        old = current.parent / "1/.config/couch-remote/devices/Test-TV"
        with mock.patch.dict(cli.os.environ, {"SNAP_USER_DATA": str(current)}), \
             mock.patch.object(cli, "BASE", base), \
             mock.patch.object(cli, "DEVICES", base / "devices.json"):
            cli.put_device("Test TV", "192.168.1.20", cert=str(old / "client.pem"), key=str(old / "key.pem"))
            target = base / "devices/Test-TV"
            (target / "client.pem").write_text("test certificate")
            (target / "key.pem").write_text("test key")
            device = cli.get_device()
            self.assertEqual(device["cert"], str(target / "client.pem"))
            self.assertEqual(device["key"], str(target / "key.pem"))
            persisted = cli.json.loads(cli.DEVICES.read_text())
            self.assertEqual(persisted["devices"]["Test TV"]["cert"], device["cert"])
            self.assertEqual(cli.get_device(), device)

    def test_snap_refresh_preserves_custom_or_incomplete_credentials(self):
        current = self.base / "snap/couch-remote/4"
        base = current / ".config/couch-remote"
        old = current.parent / "1/.config/couch-remote/devices/Test-TV"
        with mock.patch.dict(cli.os.environ, {"SNAP_USER_DATA": str(current)}), \
             mock.patch.object(cli, "BASE", base):
            target = base / "devices/Test-TV"
            target.mkdir(parents=True)
            (target / "client.pem").write_text("test certificate")
            device = {"name": "Test TV", "cert": str(old / "client.pem"), "key": str(old / "key.pem")}
            original = dict(device)
            cli.relocate_snap_credentials(device)
            self.assertEqual(device, original)
            (target / "key.pem").write_text("test key")
            device["cert"] = str(self.base / "custom.pem")
            original = dict(device)
            cli.relocate_snap_credentials(device)
            self.assertEqual(device, original)

    def test_non_snap_credentials_are_unchanged(self):
        device = {"name": "Test TV", "cert": "/custom/client.pem", "key": "/custom/key.pem"}
        original = dict(device)
        with mock.patch.dict(cli.os.environ, {}, clear=True):
            cli.relocate_snap_credentials(device)
        self.assertEqual(device, original)


if __name__ == "__main__":
    unittest.main()
