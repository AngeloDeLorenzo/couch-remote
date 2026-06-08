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


if __name__ == "__main__":
    unittest.main()
