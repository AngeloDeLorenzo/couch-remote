#!/usr/bin/env python3
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk  # noqa: E402

CLI_COMMAND = shutil.which("couch-remote") or shutil.which("tv")
BASE = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "couch-remote"
LOG = BASE / "tv-gui.log"
DEVICES = BASE / "devices.json"


def cli_command() -> list[str]:
    if CLI_COMMAND:
        return [CLI_COMMAND]
    return [sys.executable, "-m", "couch_remote"]


class Remote(Gtk.Window):
    def __init__(self):
        super().__init__(title="Couch Remote")
        self.set_border_width(16)
        self.set_resizable(False)
        self.get_style_context().add_class("remote-window")
        self.load_css()

        self.commands = queue.Queue()
        threading.Thread(target=self.worker, daemon=True).start()

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_size_request(318, -1)
        root.get_style_context().add_class("remote-shell")
        self.add(root)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        header.get_style_context().add_class("remote-header")
        root.pack_start(header, False, False, 0)
        self.device_label = Gtk.Label(label=self.default_device_name())
        self.device_label.set_xalign(0)
        self.device_label.get_style_context().add_class("device-label")
        header.pack_start(self.device_label, True, True, 0)
        settings = Gtk.Button(label="⚙")
        settings.set_size_request(42, 34)
        settings.get_style_context().add_class("remote-button")
        settings.get_style_context().add_class("icon-button")
        settings.connect("clicked", self.open_settings)
        header.pack_start(settings, False, False, 0)

        top = self.grid(spacing=8, homogeneous=True)
        top.set_margin_bottom(2)
        root.pack_start(top, False, False, 0)
        self.add_button(top, "⏻", ["power"], 0, 0, style="power-button")
        self.add_button(top, "Input", ["input"], 1, 0, style="secondary-button")
        self.add_button(top, "TV", ["tv"], 2, 0, style="secondary-button")

        numbers = self.grid(spacing=8, homogeneous=True)
        numbers.set_margin_bottom(5)
        root.pack_start(numbers, False, False, 0)
        labels = (
            ("1", "1"), ("2", "2"), ("3", "3"),
            ("4", "4"), ("5", "5"), ("6", "6"),
            ("7", "7"), ("8", "8"), ("9", "9"),
            ("LANG", "language"), ("0", "0"), ("SUB", "subtitle"),
        )
        for index, (label, key) in enumerate(labels):
            self.add_button(numbers, label, [key], index % 3, index // 3, height=44, style="number-button")

        home = self.grid(spacing=7, homogeneous=True)
        home.set_margin_bottom(5)
        root.pack_start(home, False, False, 0)
        self.add_button(home, "⌂", ["home"], 0, 0, width=286, height=48, style="home-button", colspan=3)

        rocker = self.grid(spacing=8, homogeneous=True)
        rocker.set_margin_bottom(5)
        root.pack_start(rocker, False, False, 0)
        self.add_button(rocker, "+\nV", ["volume_up"], 0, 0, rowspan=2, height=82)
        self.add_button(rocker, "Mute", ["mute"], 1, 0)
        self.add_button(rocker, "P\n▲", ["channel_up"], 2, 0, rowspan=2, height=82)
        self.add_button(rocker, "SUB", ["subtitle"], 1, 1)
        self.add_button(rocker, "-\nV", ["volume_down"], 0, 2, rowspan=2, height=82)
        self.add_button(rocker, "Guide", ["guide"], 1, 2)
        self.add_button(rocker, "P\n▼", ["channel_down"], 2, 2, rowspan=2, height=82)
        self.add_button(rocker, "Info", ["info"], 1, 3)

        dpad = self.grid(spacing=7, homogeneous=True)
        dpad.set_margin_bottom(4)
        root.pack_start(dpad, False, False, 0)
        self.add_button(dpad, "Guide", ["guide"], 0, 0)
        self.add_button(dpad, "▲", ["up"], 1, 0, style="dpad-button")
        self.add_button(dpad, "Info", ["info"], 2, 0)
        self.add_button(dpad, "◀", ["left"], 0, 1, style="dpad-button")
        self.add_button(dpad, "OK", ["ok"], 1, 1, style="ok-button")
        self.add_button(dpad, "▶", ["right"], 2, 1, style="dpad-button")
        self.add_button(dpad, "Back", ["back"], 0, 2)
        self.add_button(dpad, "▼", ["down"], 1, 2, style="dpad-button")
        self.add_button(dpad, "Exit", ["exit"], 2, 2)

        apps = self.grid(spacing=8, homogeneous=True)
        apps.set_margin_bottom(2)
        root.pack_start(apps, False, False, 0)
        self.add_button(apps, "Netflix", ["launch", "netflix"], 0, 0, style="app-button")
        self.add_button(apps, "YouTube", ["launch", "youtube"], 1, 0, style="youtube-button")
        self.add_button(apps, "Prime", ["launch", "prime"], 2, 0, style="app-button")

        utility = self.grid(spacing=8, homogeneous=True)
        utility.set_margin_bottom(4)
        root.pack_start(utility, False, False, 0)
        self.add_button(utility, "Menu", ["menu"], 0, 0)
        self.add_button(utility, "Search", ["search"], 1, 0)
        self.add_button(utility, "Keyboard", ["keyboard"], 2, 0)

        media = self.grid(spacing=7, homogeneous=True)
        media.set_margin_bottom(2)
        root.pack_start(media, False, False, 0)
        self.add_button(media, "◀◀", ["rewind"], 0, 0, width=66, style="media-button")
        self.add_button(media, "▶", ["play"], 1, 0, width=66, style="play-button")
        self.add_button(media, "Ⅱ", ["pause"], 2, 0, width=66, style="media-button")
        self.add_button(media, "▶▶", ["fast_forward"], 3, 0, width=66, style="media-button")
        self.add_button(media, "●", ["record"], 0, 1, width=66, style="record-button")
        self.add_button(media, "■", ["stop"], 1, 1, width=66, style="media-button")
        self.add_button(media, "TXT", ["teletext"], 2, 1, width=66, style="media-button", colspan=2)

        colors = self.grid(spacing=7, homogeneous=True)
        root.pack_start(colors, False, False, 0)
        self.add_button(colors, "", ["red"], 0, 0, width=66, style="red-button", height=30)
        self.add_button(colors, "", ["green"], 1, 0, width=66, style="green-button", height=30)
        self.add_button(colors, "", ["yellow"], 2, 0, width=66, style="yellow-button", height=30)
        self.add_button(colors, "", ["blue"], 3, 0, width=66, style="blue-button", height=30)

        self.status = Gtk.Label(label="Ready")
        self.status.get_style_context().add_class("status-label")
        root.pack_start(self.status, False, False, 0)

    def grid(self, spacing=6, homogeneous=False):
        grid = Gtk.Grid(column_spacing=spacing, row_spacing=spacing)
        grid.set_column_homogeneous(homogeneous)
        grid.set_row_homogeneous(False)
        grid.get_style_context().add_class("button-cluster")
        return grid

    def add_button(self, grid, label, args, col, row, width=86, height=40, style=None, colspan=1, rowspan=1):
        button = Gtk.Button(label=label)
        button.set_size_request(width, height)
        button.get_style_context().add_class("remote-button")
        if style:
            button.get_style_context().add_class(style)
        button.connect("clicked", lambda _button: self.run_tv(args))
        grid.attach(button, col, row, colspan, rowspan)
        return button

    def load_css(self):
        css = b"""
        window.remote-window {
            background: #0f1115;
        }
        box.remote-shell {
            background: linear-gradient(to bottom, #252832, #151820 58%, #101218);
            border: 1px solid #07080a;
            border-radius: 18px;
            padding: 14px;
            box-shadow:
                inset 0 1px rgba(255,255,255,0.10),
                inset 0 -1px rgba(0,0,0,0.65),
                0 12px 28px rgba(0,0,0,0.42);
        }
        box.remote-header {
            padding: 0 2px 2px 2px;
        }
        grid.button-cluster {
            background: transparent;
            border: none;
            padding: 0;
            box-shadow: none;
        }
        button.remote-button {
            background: linear-gradient(to bottom, #3a3e47, #252932);
            border: 1px solid #050609;
            border-radius: 9px;
            color: #f3f4f6;
            font-weight: 600;
            padding: 4px 6px;
            text-shadow: none;
            box-shadow:
                inset 0 1px rgba(255,255,255,0.16),
                inset 0 -1px rgba(0,0,0,0.38),
                0 3px 6px rgba(0,0,0,0.48);
        }
        button.remote-button:hover {
            background: linear-gradient(to bottom, #444956, #2b303a);
        }
        button.remote-button:active {
            background: linear-gradient(to bottom, #20242c, #303540);
            box-shadow:
                inset 0 2px 5px rgba(0,0,0,0.58),
                inset 0 1px rgba(255,255,255,0.04);
        }
        button.power-button {
            background: linear-gradient(to bottom, #e52431, #99121b);
            color: white;
            font-size: 20px;
            box-shadow:
                inset 0 1px rgba(255,255,255,0.22),
                inset 0 -1px rgba(0,0,0,0.35),
                0 2px 5px rgba(143, 13, 23, 0.45);
        }
        button.secondary-button {
            background: linear-gradient(to bottom, #30343d, #20242b);
        }
        button.number-button {
            background: linear-gradient(to bottom, #3a3f48, #282d35);
            font-size: 13px;
            border-radius: 8px;
        }
        button.icon-button {
            font-size: 16px;
            padding: 0;
        }
        button.home-button {
            background: linear-gradient(to bottom, #313741, #20252e);
            border-radius: 10px;
            font-size: 28px;
            padding: 0;
        }
        button.dpad-button {
            background: linear-gradient(to bottom, #454b57, #2d333d);
            font-size: 20px;
        }
        button.ok-button {
            background: linear-gradient(to bottom, #2380df, #145199);
            border-radius: 22px;
            font-size: 17px;
            box-shadow:
                inset 0 1px rgba(255,255,255,0.22),
                inset 0 -1px rgba(0,0,0,0.42),
                0 2px 6px rgba(20, 81, 153, 0.45);
        }
        button.media-button {
            background: linear-gradient(to bottom, #333842, #222731);
            font-size: 17px;
        }
        button.play-button {
            background: linear-gradient(to bottom, #2f9468, #1c5f42);
            font-size: 18px;
        }
        button.app-button {
            background: linear-gradient(to bottom, #ffffff, #dce0e6);
            color: #c8102e;
        }
        button.youtube-button {
            background: linear-gradient(to bottom, #f02b33, #b9131a);
            color: white;
        }
        button.record-button {
            background: linear-gradient(to bottom, #333842, #222731);
            color: #f44336;
            font-size: 18px;
        }
        button.red-button { background: linear-gradient(to bottom, #ee3038, #b9141c); }
        button.green-button { background: linear-gradient(to bottom, #22c069, #0b7e43); }
        button.yellow-button { background: linear-gradient(to bottom, #ffe567, #e1b80f); color: #171717; }
        button.blue-button { background: linear-gradient(to bottom, #35a2ff, #1168bc); }
        label.status-label {
            background: rgba(0,0,0,0.24);
            border-radius: 7px;
            color: #c9d0dc;
            font-size: 12px;
            min-height: 18px;
            padding: 4px 7px;
        }
        label.device-label {
            color: #f6f7f9;
            font-weight: 700;
            font-size: 14px;
            text-shadow: 0 1px rgba(0,0,0,0.75);
        }
        entry {
            background: linear-gradient(to bottom, #2a2e36, #1f232b);
            border: 1px solid #090a0c;
            border-radius: 8px;
            color: #f3f4f6;
            padding: 6px 8px;
            box-shadow: inset 0 1px 3px rgba(0,0,0,0.55);
        }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css)
        Gtk.StyleContext.add_provider_for_screen(
            self.get_screen(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )

    def load_devices(self):
        try:
            with DEVICES.open("r", encoding="utf-8") as fh:
                return json.load(fh)
        except Exception:
            return {"default": "", "devices": {}}

    def default_device_name(self):
        config = self.load_devices()
        return config.get("default") or "No TV"

    def refresh_device_label(self):
        self.device_label.set_text(self.default_device_name())

    def set_status(self, text):
        self.status.set_text(text)
        return False

    def run_tv(self, args):
        if args == ["keyboard"]:
            self.open_keyboard()
            return
        self.commands.put(args)
        GLib.idle_add(self.set_status, f"Queued: {' '.join(args)}")

    def open_keyboard(self):
        dialog = KeyboardDialog(self)
        response = dialog.run()
        text = dialog.text()
        dialog.destroy()
        if response == Gtk.ResponseType.OK and text:
            self.run_tv(["text", text])

    def run_tv_capture(self, args):
        return subprocess.run([*cli_command(), *args], text=True, capture_output=True, timeout=30)

    def open_settings(self, *_args):
        dialog = SettingsDialog(self)
        dialog.run()
        dialog.destroy()
        self.refresh_device_label()

    def worker(self):
        while True:
            args = self.commands.get()
            self._run_tv(args)
            self.commands.task_done()

    def _run_tv(self, args):
        raw_commands = {"launch", "text", "wake"}
        command = [*cli_command(), *args] if args and args[0] in raw_commands else [*cli_command(), "action", *args]
        GLib.idle_add(self.set_status, f"Sending: {' '.join(args)}")
        try:
            result = subprocess.run(command, text=True, capture_output=True, timeout=20)
            LOG.parent.mkdir(parents=True, exist_ok=True)
            with LOG.open("a", encoding="utf-8") as log:
                log.write(f"$ {' '.join(command)}\n")
                log.write(f"exit={result.returncode}\n")
                if result.stdout:
                    log.write(result.stdout)
                if result.stderr:
                    log.write(result.stderr)
                log.write("\n")
            if result.returncode == 0:
                GLib.idle_add(self.set_status, f"OK: {' '.join(args)}")
            else:
                message = result.stderr.strip() or result.stdout.strip() or "Error"
                GLib.idle_add(self.set_status, message)
        except Exception as exc:
            with LOG.open("a", encoding="utf-8") as log:
                log.write(f"$ {' '.join(command)}\n{exc}\n\n")
            GLib.idle_add(self.set_status, str(exc))


class SettingsDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="TV Setup", transient_for=parent, flags=0)
        self.set_default_size(680, 420)
        self.parent = parent
        self.add_button("Close", Gtk.ResponseType.CLOSE)

        area = self.get_content_area()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)
        area.add(box)

        actions = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.pack_start(actions, False, False, 0)

        setup_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.pack_start(setup_actions, False, False, 0)
        self.scan_button = Gtk.Button(label="Scan Network")
        self.scan_button.connect("clicked", self.on_scan)
        setup_actions.pack_start(self.scan_button, False, False, 0)
        self.pair_button = Gtk.Button(label="Pair Selected")
        self.pair_button.connect("clicked", self.on_pair)
        setup_actions.pack_start(self.pair_button, False, False, 0)
        self.add_button = Gtk.Button(label="Add Manually")
        self.add_button.connect("clicked", self.on_add_manual)
        setup_actions.pack_start(self.add_button, False, False, 0)
        self.use_button = Gtk.Button(label="Use Selected")
        self.use_button.connect("clicked", self.on_use)
        setup_actions.pack_start(self.use_button, False, False, 0)
        self.remove_button = Gtk.Button(label="Remove")
        self.remove_button.connect("clicked", self.on_remove)
        setup_actions.pack_start(self.remove_button, False, False, 0)

        tools_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        actions.pack_start(tools_actions, False, False, 0)
        self.wake_button = Gtk.Button(label="Wake LAN")
        self.wake_button.connect("clicked", self.on_wake)
        tools_actions.pack_start(self.wake_button, False, False, 0)
        self.test_button = Gtk.Button(label="Test Keys")
        self.test_button.connect("clicked", self.on_test_keys)
        tools_actions.pack_start(self.test_button, False, False, 0)
        self.diagnostics_button = Gtk.Button(label="Diagnostics")
        self.diagnostics_button.connect("clicked", self.on_diagnostics)
        tools_actions.pack_start(self.diagnostics_button, False, False, 0)

        self.store = Gtk.ListStore(str, str, str, str, bool)
        self.view = Gtk.TreeView(model=self.store)
        for index, title in enumerate(("Name", "Backend", "IP", "MAC", "Saved")):
            renderer = Gtk.CellRendererText()
            column = Gtk.TreeViewColumn(title, renderer, text=index)
            column.set_expand(index == 0)
            self.view.append_column(column)
        self.view.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.add(self.view)
        box.pack_start(scroll, True, True, 0)

        self.status = Gtk.Label(label="Ready")
        self.status.set_xalign(0)
        box.pack_start(self.status, False, False, 0)
        self.load_saved()
        self.show_all()

    def set_status(self, text):
        self.status.set_text(text)

    def load_saved(self):
        self.store.clear()
        config = self.parent.load_devices()
        default = config.get("default")
        for name, device in config.get("devices", {}).items():
            label = f"{name} *" if name == default else name
            self.store.append([
                label,
                device.get("backend", "androidtv"),
                device.get("host", ""),
                device.get("mac", ""),
                True,
            ])

    def selected(self):
        model, tree_iter = self.view.get_selection().get_selected()
        if not tree_iter:
            return None
        return {
            "name": model[tree_iter][0].replace(" *", ""),
            "backend": model[tree_iter][1],
            "host": model[tree_iter][2],
            "mac": model[tree_iter][3],
            "saved": model[tree_iter][4],
        }

    def on_scan(self, *_args):
        self.set_status("Scanning...")
        threading.Thread(target=self.scan_worker, daemon=True).start()

    def scan_worker(self):
        result = self.parent.run_tv_capture(["scan"])
        GLib.idle_add(self.apply_scan, result)

    def apply_scan(self, result):
        if result.returncode != 0:
            self.set_status(result.stderr.strip() or "Scan failed")
            return False
        self.load_saved()
        saved_hosts = {row[2] for row in self.store}
        count = 0
        for line in result.stdout.splitlines():
            if not (re_match := re.match(r"\d+\.\s+(.*?)\t([0-9a-fA-F:.]+)\t?(.*)", line)):
                continue
            name, host, mac = re_match.groups()
            if host not in saved_hosts:
                self.store.append([name, "androidtv", host, "", False])
                count += 1
        self.set_status(f"Found {count} new devices")
        return False

    def on_add_manual(self, *_args):
        dialog = ManualDeviceDialog(self)
        response = dialog.run()
        values = dialog.values()
        dialog.destroy()
        if response != Gtk.ResponseType.OK:
            return
        if not values["name"] or not values["host"]:
            self.set_status("Name and IP are required")
            return
        command = ["add", values["name"], values["host"]]
        if values["mac"]:
            command.append(values["mac"])
        result = self.parent.run_tv_capture(command)
        self.set_status(result.stdout.strip() if result.returncode == 0 else result.stderr.strip())
        self.load_saved()
        self.parent.refresh_device_label()

    def on_use(self, *_args):
        device = self.selected()
        if not device:
            self.set_status("Select a TV")
            return
        result = self.parent.run_tv_capture(["use", device["name"]])
        self.set_status(result.stdout.strip() if result.returncode == 0 else result.stderr.strip())
        self.load_saved()

    def on_remove(self, *_args):
        device = self.selected()
        if not device:
            self.set_status("Select a TV")
            return
        result = self.parent.run_tv_capture(["remove", device["name"]])
        self.set_status(result.stdout.strip() if result.returncode == 0 else result.stderr.strip())
        self.load_saved()
        self.parent.refresh_device_label()

    def on_wake(self, *_args):
        device = self.selected()
        if not device:
            self.set_status("Select a TV")
            return
        result = self.parent.run_tv_capture(["--device", device["name"], "wake"])
        self.set_status(result.stdout.strip() if result.returncode == 0 else result.stderr.strip())

    def on_pair(self, *_args):
        device = self.selected()
        if not device:
            self.set_status("Select a TV")
            return
        self.set_status("Starting pairing request...")
        threading.Thread(target=self.pair_worker, args=(device,), daemon=True).start()

    def ask_code(self):
        dialog = Gtk.Dialog(title="Pairing Code", transient_for=self, flags=0)
        dialog.add_button("Cancel", Gtk.ResponseType.CANCEL)
        dialog.add_button("Pair", Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        box.set_border_width(10)
        label = Gtk.Label(label="Enter the code shown on the TV:")
        label.set_xalign(0)
        entry = Gtk.Entry()
        entry.set_activates_default(True)
        box.pack_start(label, False, False, 6)
        box.pack_start(entry, False, False, 6)
        dialog.set_default_response(Gtk.ResponseType.OK)
        dialog.show_all()
        response = dialog.run()
        code = entry.get_text().strip()
        dialog.destroy()
        return code if response == Gtk.ResponseType.OK else ""

    def pair_worker(self, device):
        proc = subprocess.Popen(
            [*cli_command(), "pair", "--name", device["name"], "--host", device["host"], "--mac", device["mac"]],
            text=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout = []
        try:
            while True:
                line = proc.stdout.readline()
                if not line:
                    break
                stdout.append(line)
                if "PAIRING_CODE?" in line:
                    code_box = queue.Queue(maxsize=1)
                    GLib.idle_add(lambda: code_box.put(self.ask_code()) or False)
                    code = code_box.get()
                    if not code:
                        proc.kill()
                        GLib.idle_add(self.set_status, "Pairing canceled")
                        return
                    proc.stdin.write(code + "\n")
                    proc.stdin.flush()
            stderr = proc.stderr.read()
            returncode = proc.wait(timeout=45)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.communicate()
            GLib.idle_add(self.set_status, "Pairing timed out. Check that the TV is on and accepts remote pairing.")
            return
        result = subprocess.CompletedProcess(proc.args, returncode, "".join(stdout), stderr)
        GLib.idle_add(self.after_pair, result)

    def after_pair(self, result):
        self.set_status(result.stdout.strip() if result.returncode == 0 else result.stderr.strip())
        self.load_saved()
        self.parent.refresh_device_label()
        return False

    def on_test_keys(self, *_args):
        device = self.selected()
        if not device:
            self.set_status("Select a TV")
            return
        dialog = KeyTesterDialog(self, device["name"])
        dialog.run()
        dialog.destroy()
        self.load_saved()

    def on_diagnostics(self, *_args):
        device = self.selected()
        if not device:
            self.set_status("Select a TV")
            return
        self.set_status("Running diagnostics...")
        threading.Thread(target=self.diagnostics_worker, args=(device["name"],), daemon=True).start()

    def diagnostics_worker(self, device_name):
        result = self.parent.run_tv_capture(["--device", device_name, "diagnose"])
        output = result.stdout if result.returncode == 0 else result.stderr or result.stdout
        GLib.idle_add(self.show_diagnostics, device_name, output.strip() or "No output")

    def show_diagnostics(self, device_name, output):
        dialog = Gtk.Dialog(title=f"Diagnostics: {device_name}", transient_for=self, flags=0)
        dialog.add_button("Close", Gtk.ResponseType.CLOSE)
        dialog.set_default_size(620, 420)
        box = dialog.get_content_area()
        box.set_border_width(10)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        view = Gtk.TextView()
        view.set_editable(False)
        view.set_monospace(True)
        view.get_buffer().set_text(output)
        scroll.add(view)
        box.add(scroll)
        dialog.show_all()
        dialog.run()
        dialog.destroy()
        self.set_status("Diagnostics complete")
        return False


class ManualDeviceDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="Add TV", transient_for=parent, flags=0)
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Add", Gtk.ResponseType.OK)
        self.set_default_size(360, 180)

        box = self.get_content_area()
        box.set_border_width(10)
        grid = Gtk.Grid(column_spacing=10, row_spacing=10)
        box.add(grid)

        self.name = Gtk.Entry()
        self.name.set_text("Living Room TV")
        self.host = Gtk.Entry()
        self.host.set_placeholder_text("192.168.1.50")
        self.mac = Gtk.Entry()
        self.mac.set_placeholder_text("optional, for Wake-on-LAN")

        for row, (label, widget) in enumerate((("Name", self.name), ("IP address", self.host), ("MAC", self.mac))):
            text = Gtk.Label(label=label)
            text.set_xalign(0)
            grid.attach(text, 0, row, 1, 1)
            grid.attach(widget, 1, row, 1, 1)

        self.show_all()

    def values(self):
        return {
            "name": self.name.get_text().strip(),
            "host": self.host.get_text().strip(),
            "mac": self.mac.get_text().strip(),
        }


class KeyboardDialog(Gtk.Dialog):
    def __init__(self, parent):
        super().__init__(title="Type on TV", transient_for=parent, flags=0)
        self.add_button("Cancel", Gtk.ResponseType.CANCEL)
        self.add_button("Send", Gtk.ResponseType.OK)
        self.set_default_size(420, 120)

        box = self.get_content_area()
        box.set_border_width(10)
        self.entry = Gtk.Entry()
        self.entry.set_activates_default(True)
        self.entry.set_placeholder_text("Text to send to the focused TV field")
        box.pack_start(self.entry, False, False, 0)
        self.set_default_response(Gtk.ResponseType.OK)
        self.show_all()

    def text(self):
        return self.entry.get_text().strip()


class KeyTesterDialog(Gtk.Dialog):
    ACTIONS = (
        "subtitle",
        "teletext",
        "input",
        "guide",
        "info",
        "menu",
        "settings",
        "search",
        "language",
        "captions",
        "red",
        "green",
        "yellow",
        "blue",
    )

    def __init__(self, parent, device_name):
        super().__init__(title="Key Tester", transient_for=parent, flags=0)
        self.parent = parent
        self.device_name = device_name
        self.add_button("Close", Gtk.ResponseType.CLOSE)
        self.set_default_size(460, 420)

        area = self.get_content_area()
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_border_width(10)
        area.add(box)

        hint = Gtk.Label(label="Send candidate keys. When one works, assign it to an action.")
        hint.set_xalign(0)
        box.pack_start(hint, False, False, 0)

        self.store = Gtk.ListStore(str)
        result = self.parent.parent.run_tv_capture(["candidates"])
        for line in result.stdout.splitlines():
            if line.strip():
                self.store.append([line.strip()])

        self.view = Gtk.TreeView(model=self.store)
        self.view.append_column(Gtk.TreeViewColumn("Key", Gtk.CellRendererText(), text=0))
        self.view.get_selection().set_mode(Gtk.SelectionMode.SINGLE)
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.add(self.view)
        box.pack_start(scroll, True, True, 0)

        controls = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        box.pack_start(controls, False, False, 0)
        send = Gtk.Button(label="Send Key")
        send.connect("clicked", self.on_send)
        controls.pack_start(send, False, False, 0)

        self.action = Gtk.ComboBoxText()
        for action in self.ACTIONS:
            self.action.append_text(action)
        self.action.set_active(0)
        controls.pack_start(self.action, True, True, 0)

        assign = Gtk.Button(label="Assign to Action")
        assign.connect("clicked", self.on_assign)
        controls.pack_start(assign, False, False, 0)

        self.status = Gtk.Label(label="Ready")
        self.status.set_xalign(0)
        box.pack_start(self.status, False, False, 0)
        self.show_all()

    def selected_key(self):
        model, tree_iter = self.view.get_selection().get_selected()
        if not tree_iter:
            return ""
        return model[tree_iter][0]

    def set_status(self, text):
        self.status.set_text(text)

    def on_send(self, *_args):
        key = self.selected_key()
        if not key:
            self.set_status("Select a key")
            return
        threading.Thread(target=self.send_worker, args=(key,), daemon=True).start()

    def send_worker(self, key):
        result = self.parent.parent.run_tv_capture(["--device", self.device_name, "key", key])
        GLib.idle_add(
            self.set_status,
            f"Sent {key}" if result.returncode == 0 else result.stderr.strip() or "Send failed",
        )

    def on_assign(self, *_args):
        key = self.selected_key()
        action = self.action.get_active_text()
        if not key or not action:
            self.set_status("Select a key and an action")
            return
        result = self.parent.parent.run_tv_capture(["--device", self.device_name, "map", action, key])
        self.set_status(result.stdout.strip() if result.returncode == 0 else result.stderr.strip() or "Mapping failed")


def main():
    win = Remote()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
