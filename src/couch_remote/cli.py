#!/usr/bin/env python3
import argparse
import asyncio
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from androidtvremote2 import AndroidTVRemote

BASE = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "couch-remote"
DEVICES = BASE / "devices.json"
OLD_BASE = Path.home() / ".local/share/tv-remote"
LEGACY_DEVICES = OLD_BASE / "devices.json"
LEGACY_CERT = OLD_BASE / "client.pem"
LEGACY_KEY = OLD_BASE / "key.pem"
DEFAULT_NAME = "Living Room TV"
CLIENT_NAME = "Couch Remote"
VERSION = "1.0.2"

ALIASES = {
    "ok": "DPAD_CENTER",
    "enter": "DPAD_CENTER",
    "su": "DPAD_UP",
    "giu": "DPAD_DOWN",
    "giù": "DPAD_DOWN",
    "sinistra": "DPAD_LEFT",
    "destra": "DPAD_RIGHT",
    "back": "BACK",
    "indietro": "BACK",
    "home": "HOME",
    "menu": "MENU",
    "exit": "ESCAPE",
    "esci": "ESCAPE",
    "input": "TV_INPUT",
    "source": "TV_INPUT",
    "sorgente": "TV_INPUT",
    "guide": "GUIDE",
    "guida": "GUIDE",
    "info": "INFO",
    "settings": "SETTINGS",
    "impostazioni": "SETTINGS",
    "search": "SEARCH",
    "cerca": "SEARCH",
    "lang": "LANGUAGE_SWITCH",
    "lingua": "LANGUAGE_SWITCH",
    "text": "TV_TELETEXT",
    "txt": "TV_TELETEXT",
    "teletext": "TV_TELETEXT",
    "captions": "CAPTIONS",
    "sottotitoli": "CAPTIONS",
    "power": "POWER",
    "off": "POWER",
    "tvpower": "TV_POWER",
    "tv": "TV",
    "mute": "MUTE",
    "vol+": "VOLUME_UP",
    "volup": "VOLUME_UP",
    "volume+": "VOLUME_UP",
    "vol-": "VOLUME_DOWN",
    "voldown": "VOLUME_DOWN",
    "volume-": "VOLUME_DOWN",
    "ch+": "CHANNEL_UP",
    "canale+": "CHANNEL_UP",
    "ch-": "CHANNEL_DOWN",
    "canale-": "CHANNEL_DOWN",
    "play": "MEDIA_PLAY",
    "pause": "MEDIA_PAUSE",
    "pausa": "MEDIA_PAUSE",
    "playpause": "MEDIA_PLAY_PAUSE",
    "stop": "MEDIA_STOP",
    "rew": "MEDIA_REWIND",
    "ff": "MEDIA_FAST_FORWARD",
    "prev": "MEDIA_PREVIOUS",
    "next": "MEDIA_NEXT",
    "rec": "MEDIA_RECORD",
    "red": "PROG_RED",
    "green": "PROG_GREEN",
    "yellow": "PROG_YELLOW",
    "blue": "PROG_BLUE",
    "rosso": "PROG_RED",
    "verde": "PROG_GREEN",
    "giallo": "PROG_YELLOW",
    "blu": "PROG_BLUE",
}

APP_LINKS = {
    "youtube": "https://www.youtube.com/tv",
    "netflix": "https://www.netflix.com/title",
    "prime": "https://app.primevideo.com",
    "disney": "https://www.disneyplus.com",
}

DEFAULT_ACTION_MAP = {
    "back": "BACK",
    "blue": "PROG_BLUE",
    "captions": "CAPTIONS",
    "channel_down": "CHANNEL_DOWN",
    "channel_up": "CHANNEL_UP",
    "down": "DPAD_DOWN",
    "exit": "ESCAPE",
    "fast_forward": "MEDIA_FAST_FORWARD",
    "green": "PROG_GREEN",
    "guide": "GUIDE",
    "home": "HOME",
    "info": "INFO",
    "input": "TV_INPUT",
    "language": "LANGUAGE_SWITCH",
    "left": "DPAD_LEFT",
    "menu": "MENU",
    "mute": "MUTE",
    "pause": "MEDIA_PAUSE",
    "play": "MEDIA_PLAY",
    "ok": "DPAD_CENTER",
    "play_pause": "MEDIA_PLAY_PAUSE",
    "power": "POWER",
    "record": "MEDIA_RECORD",
    "red": "PROG_RED",
    "rewind": "MEDIA_REWIND",
    "right": "DPAD_RIGHT",
    "search": "SEARCH",
    "settings": "SETTINGS",
    "stop": "MEDIA_STOP",
    "subtitle": "CAPTIONS",
    "teletext": "TV_TELETEXT",
    "tv": "TV",
    "up": "DPAD_UP",
    "volume_down": "VOLUME_DOWN",
    "volume_up": "VOLUME_UP",
    "yellow": "PROG_YELLOW",
}

ACTION_ALIASES = {
    "ch+": "channel_up",
    "ch-": "channel_down",
    "sub": "subtitle",
    "txt": "teletext",
    "vol+": "volume_up",
    "vol-": "volume_down",
}

KEY_TEST_CANDIDATES = [
    "CAPTIONS",
    "TV_MEDIA_CONTEXT_MENU",
    "TV_CONTENTS_MENU",
    "MEDIA_AUDIO_TRACK",
    "LANGUAGE_SWITCH",
    "TV_AUDIO_DESCRIPTION",
    "TV_DATA_SERVICE",
    "BUTTON_SELECT",
    "BUTTON_1",
    "BUTTON_2",
    "BUTTON_3",
    "BUTTON_4",
    "BUTTON_5",
    "BUTTON_6",
    "BUTTON_7",
    "BUTTON_8",
    "BUTTON_9",
    "BUTTON_10",
    "BUTTON_11",
    "BUTTON_12",
]


def slugify(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", value.strip()).strip("-")
    return slug or "tv"


def default_config() -> dict:
    return {"default": "", "devices": {}}


def normalize_device(device: dict) -> dict:
    device.setdefault("backend", "androidtv")
    device.setdefault("actions", {})
    device.setdefault("macros", {})
    for action, key in DEFAULT_ACTION_MAP.items():
        device["actions"].setdefault(action, key)
    return device


def load_config() -> dict:
    BASE.mkdir(parents=True, exist_ok=True)
    if not DEVICES.exists():
        if LEGACY_DEVICES.exists():
            with LEGACY_DEVICES.open("r", encoding="utf-8") as fh:
                config = json.load(fh)
            for device in config.get("devices", {}).values():
                normalize_device(device)
                old_cert = Path(device.get("cert", ""))
                old_key = Path(device.get("key", ""))
                device_dir = BASE / "devices" / slugify(device.get("name", "tv"))
                device_dir.mkdir(parents=True, exist_ok=True)
                device["cert"] = str(device_dir / "client.pem")
                device["key"] = str(device_dir / "key.pem")
                if old_cert.exists() and not Path(device["cert"]).exists():
                    shutil.copy2(old_cert, device["cert"])
                if old_key.exists() and not Path(device["key"]).exists():
                    shutil.copy2(old_key, device["key"])
            save_config(config)
            secure_private_files(config)
            return config
        config = default_config()
        save_config(config)
        return config
    with DEVICES.open("r", encoding="utf-8") as fh:
        config = json.load(fh)
    changed = False
    for device in config.get("devices", {}).values():
        before = json.dumps(device, sort_keys=True)
        normalize_device(device)
        changed = changed or before != json.dumps(device, sort_keys=True)
    if changed:
        save_config(config)
    return config


def save_config(config: dict) -> None:
    BASE.mkdir(parents=True, exist_ok=True)
    tmp = DEVICES.with_name(f"{DEVICES.name}.{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        json.dump(config, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    tmp.replace(DEVICES)
    os.chmod(DEVICES, 0o600)


def secure_private_files(config: dict) -> None:
    for device in config.get("devices", {}).values():
        for field in ("cert", "key"):
            path = Path(device.get(field, ""))
            if path.exists():
                os.chmod(path, 0o600)


def get_device(name: str | None = None) -> dict:
    config = load_config()
    wanted = name or config.get("default")
    devices = config.get("devices", {})
    if wanted not in devices:
        names = ", ".join(devices) or "none"
        raise ValueError(f"Device not found: {wanted}. Saved devices: {names}")
    return devices[wanted]


def set_default(name: str) -> None:
    config = load_config()
    if name not in config.get("devices", {}):
        raise ValueError(f"Device not found: {name}")
    config["default"] = name
    save_config(config)


def remove_device(name: str) -> None:
    config = load_config()
    devices = config.get("devices", {})
    if name not in devices:
        raise ValueError(f"Device not found: {name}")
    del devices[name]
    if config.get("default") == name:
        config["default"] = next(iter(devices), "")
    save_config(config)


def put_device(name: str, host: str, mac: str = "", cert: str | None = None, key: str | None = None) -> dict:
    config = load_config()
    device_dir = BASE / "devices" / slugify(name)
    device_dir.mkdir(parents=True, exist_ok=True)
    device = {
        "name": name,
        "backend": "androidtv",
        "host": host,
        "mac": mac,
        "cert": cert or str(device_dir / "client.pem"),
        "key": key or str(device_dir / "key.pem"),
        "actions": dict(DEFAULT_ACTION_MAP),
        "macros": {},
    }
    config.setdefault("devices", {})[name] = device
    config["default"] = name
    save_config(config)
    return device


def normalize_key(value: str) -> str:
    lower = value.lower()
    if lower in ALIASES:
        return ALIASES[lower]
    if value.isdigit():
        return value
    return value.upper()


def normalize_action(value: str) -> str:
    lower = value.lower().replace("-", "_")
    return ACTION_ALIASES.get(lower, lower)


def normalize_mapping_token(value: str) -> str:
    action = normalize_action(value)
    if action in DEFAULT_ACTION_MAP:
        return DEFAULT_ACTION_MAP[action]
    return normalize_key(value)


def resolve_action(device: dict, action: str) -> str | list[str]:
    action = normalize_action(action)
    if action in device.get("macros", {}):
        return device["macros"][action]
    if action in device.get("actions", {}):
        return device["actions"][action]
    if action in DEFAULT_ACTION_MAP:
        return DEFAULT_ACTION_MAP[action]
    return normalize_key(action)


def set_action_mapping(device_name: str | None, action: str, key_or_sequence: list[str]) -> None:
    config = load_config()
    name = device_name or config.get("default")
    device = config["devices"][name]
    action = normalize_action(action)
    if len(key_or_sequence) > 1:
        device.setdefault("macros", {})[action] = [normalize_mapping_token(key) for key in key_or_sequence]
        device.setdefault("actions", {}).pop(action, None)
    else:
        device.setdefault("actions", {})[action] = normalize_mapping_token(key_or_sequence[0])
        device.setdefault("macros", {}).pop(action, None)
    save_config(config)


def reset_action_mapping(device_name: str | None, action: str | None = None) -> None:
    config = load_config()
    name = device_name or config.get("default")
    device = config["devices"][name]
    if action:
        normalized = normalize_action(action)
        device.setdefault("actions", {})[normalized] = DEFAULT_ACTION_MAP[normalized]
        device.setdefault("macros", {}).pop(normalized, None)
    else:
        device["actions"] = dict(DEFAULT_ACTION_MAP)
        device["macros"] = {}
    save_config(config)


def wake(device: dict) -> None:
    mac = device.get("mac", "").replace(":", "")
    if not mac:
        raise ValueError("Missing MAC address for Wake-on-LAN")
    packet = bytes.fromhex("ff" * 6 + mac * 16)
    host = device["host"]
    subnet = ".".join(host.split(".")[:3]) + ".255" if host.count(".") == 3 else "255.255.255.255"
    targets = [("255.255.255.255", 9), (subnet, 9), (host, 9), ("255.255.255.255", 7), (subnet, 7)]
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    for target in targets:
        sock.sendto(packet, target)


def remote_for(device: dict) -> AndroidTVRemote:
    return AndroidTVRemote(CLIENT_NAME, device["cert"], device["key"], device["host"], enable_ime=True)


async def connect_remote(remote: AndroidTVRemote, timeout: float = 8.0) -> None:
    try:
        await asyncio.wait_for(remote.async_connect(), timeout=timeout)
    except TimeoutError as exc:
        raise TimeoutError("Timed out while connecting to Android TV Remote service") from exc


async def ensure_cert(remote: AndroidTVRemote) -> None:
    Path(remote._certfile).parent.mkdir(parents=True, exist_ok=True)
    await remote.async_generate_cert_if_missing()


async def wait_until_ready(remote: AndroidTVRemote) -> None:
    for _ in range(20):
        if remote.current_app or remote.volume_info is not None:
            return
        await asyncio.sleep(0.1)
    await asyncio.sleep(0.5)


async def send_keys(device: dict, keys: list[str]) -> None:
    remote = remote_for(device)
    try:
        await connect_remote(remote)
        await wait_until_ready(remote)
        for raw in keys:
            key = normalize_key(raw)
            if key.isdigit() and len(key) > 1:
                for digit in key:
                    remote.send_key_command(digit)
                    await asyncio.sleep(0.25)
                continue
            remote.send_key_command(key)
            await asyncio.sleep(0.35)
    finally:
        remote.disconnect()


async def send_actions(device: dict, actions: list[str]) -> None:
    keys: list[str] = []
    for action in actions:
        resolved = resolve_action(device, action)
        if isinstance(resolved, list):
            keys.extend(resolved)
        else:
            keys.append(resolved)
    await send_keys(device, keys)


async def send_text(device: dict, text: str) -> None:
    remote = remote_for(device)
    try:
        await connect_remote(remote)
        await wait_until_ready(remote)
        remote.send_text(text)
        await asyncio.sleep(0.3)
    finally:
        remote.disconnect()


async def status(device: dict) -> None:
    remote = remote_for(device)
    try:
        await connect_remote(remote)
        await asyncio.sleep(0.5)
        print(f"{device['name']}: on={remote.is_on} app={remote.current_app or '-'} host={device['host']}")
        if remote.volume_info:
            volume = remote.volume_info
            print(f"volume={volume['level']}/{volume['max']} muted={volume['muted']}")
    finally:
        remote.disconnect()


def tcp_check(host: str, port: int, timeout: float = 1.5) -> tuple[bool, str]:
    start = time.monotonic()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            elapsed = int((time.monotonic() - start) * 1000)
            return True, f"open ({elapsed} ms)"
    except OSError as exc:
        return False, str(exc)


async def diagnose(device: dict) -> None:
    print(f"Device: {device['name']}")
    print(f"Backend: {device.get('backend', 'androidtv')}")
    print(f"Host: {device.get('host', '-')}")
    print(f"MAC: {device.get('mac') or '-'}")
    for label in ("cert", "key"):
        path = Path(device.get(label, ""))
        state = "ok" if path.exists() else "missing"
        print(f"{label.upper()}: {state} {path}")

    host = device["host"]
    try:
        resolved = socket.gethostbyname(host)
        print(f"DNS/IP: ok {resolved}")
    except OSError as exc:
        print(f"DNS/IP: failed {exc}")

    for port, name in ((6466, "Android TV Remote"), (8008, "Cast HTTP"), (8009, "Cast TLS")):
        ok, detail = tcp_check(host, port)
        print(f"Port {port} ({name}): {detail}")

    remote = remote_for(device)
    try:
        await connect_remote(remote)
        await asyncio.sleep(0.5)
        print("Remote connection: ok")
        print(f"Power: {'on' if remote.is_on else 'off/unknown'}")
        print(f"Current app: {remote.current_app or '-'}")
        if remote.volume_info:
            volume = remote.volume_info
            print(f"Volume: {volume['level']}/{volume['max']} muted={volume['muted']}")
        if remote.device_info:
            print(f"Device info: {remote.device_info}")
    except Exception as exc:
        print(f"Remote connection: failed {exc}")
    finally:
        remote.disconnect()


async def launch(device: dict, app: str) -> None:
    link = APP_LINKS.get(app.lower(), app)
    remote = remote_for(device)
    try:
        await connect_remote(remote)
        await wait_until_ready(remote)
        remote.send_launch_app_command(link)
        await asyncio.sleep(1)
    finally:
        remote.disconnect()


async def pair_device(name: str, host: str, code: str | None = None, mac: str = "") -> None:
    device = put_device(name, host, mac)
    remote = remote_for(device)
    await ensure_cert(remote)
    await remote.async_start_pairing()
    if not code:
        print("PAIRING_CODE?", flush=True)
        code = input("Code shown on the TV: ").strip()
    await remote.async_finish_pairing(code.strip().replace(" ", ""))
    print(f"Pairing complete: {name} ({host})")


def scan_devices() -> list[dict]:
    try:
        result = subprocess.run(
            ["avahi-browse", "-rt", "_androidtvremote2._tcp"],
            text=True,
            capture_output=True,
            timeout=8,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return []
    devices: list[dict] = []
    current: dict | None = None
    for line in result.stdout.splitlines():
        line = line.strip()
        if line.startswith("="):
            left = line.split("_androidtvremote2._tcp", 1)[0]
            parts = left.split(maxsplit=3)
            name = parts[3].strip() if len(parts) == 4 else "Android TV"
            current = {"name": name or "Android TV", "host": "", "mac": ""}
            devices.append(current)
        elif current and line.startswith("address ="):
            current["host"] = line.split("[", 1)[1].split("]", 1)[0]
        elif current and line.startswith("txt ="):
            match = re.search(r'bt=([0-9A-Fa-f:]+)', line)
            if match:
                current["bluetooth_mac"] = match.group(1).lower()
    unique: dict[tuple[str, str], dict] = {}
    for device in devices:
        if device.get("host"):
            unique[(device["name"], device["host"])] = device
    return list(unique.values())


def list_devices() -> None:
    config = load_config()
    default = config.get("default")
    for name, device in config.get("devices", {}).items():
        mark = "*" if name == default else " "
        print(f"{mark} {name}\t{device.get('backend', 'androidtv')}\t{device.get('host', '-')}\t{device.get('mac', '-')}")


def list_actions(device: dict) -> None:
    print(f"Actions for {device['name']} ({device.get('backend', 'androidtv')}):")
    actions = dict(DEFAULT_ACTION_MAP)
    actions.update(device.get("actions", {}))
    for name in sorted(actions):
        macro = device.get("macros", {}).get(name)
        value = " ".join(macro) if macro else actions[name]
        print(f"{name}\t{value}")


def list_key_candidates() -> None:
    for key in KEY_TEST_CANDIDATES:
        print(key)


def list_backends() -> None:
    print("androidtv\tAndroid TV / Google TV over Android TV Remote v2")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tv",
        description="Remote control for Android TV and Google TV.",
        epilog='Examples: couch-remote scan | couch-remote pair --name "Living Room" --host 192.168.1.57 | couch-remote 5 | couch-remote --device "Living Room" vol+',
    )
    parser.add_argument("-d", "--device", help="Saved device name")
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    parser.add_argument("args", nargs="*")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    tokens = args.args
    try:
        if args.version:
            print(f"Couch Remote {VERSION}")
            return 0
        if not tokens:
            parser.print_help()
            return 2
        cmd = tokens[0].lower()
        if cmd == "version":
            print(f"Couch Remote {VERSION}")
            return 0
        if cmd == "scan":
            found = scan_devices()
            if not found:
                print("No Android TV devices found.")
            for index, device in enumerate(found, 1):
                print(f"{index}. {device['name']}\t{device['host']}\t{device.get('mac', '')}")
            return 0
        if cmd in {"devices", "list"}:
            list_devices()
            return 0
        if cmd == "backends":
            list_backends()
            return 0
        if cmd == "actions":
            list_actions(get_device(args.device))
            return 0
        if cmd == "candidates":
            list_key_candidates()
            return 0
        if cmd == "map":
            if len(tokens) < 3:
                raise ValueError("Usage: couch-remote map ACTION KEY [KEY...]")
            set_action_mapping(args.device, tokens[1], tokens[2:])
            print(f"Mapped {tokens[1]} -> {' '.join(tokens[2:])}")
            return 0
        if cmd == "reset-map":
            action = tokens[1] if len(tokens) > 1 else None
            if action and normalize_action(action) not in DEFAULT_ACTION_MAP:
                raise ValueError(f"Unknown default action: {action}")
            reset_action_mapping(args.device, action)
            print(f"Reset mapping: {action or 'all'}")
            return 0
        if cmd == "use":
            if len(tokens) < 2:
                raise ValueError("Usage: couch-remote use NAME")
            set_default(" ".join(tokens[1:]))
            print(f"Default device: {' '.join(tokens[1:])}")
            return 0
        if cmd in {"remove", "delete"}:
            if len(tokens) < 2:
                raise ValueError("Usage: couch-remote remove NAME")
            remove_device(" ".join(tokens[1:]))
            print(f"Removed: {' '.join(tokens[1:])}")
            return 0
        if cmd == "add":
            if len(tokens) < 3:
                raise ValueError("Usage: couch-remote add NAME HOST [MAC]")
            mac = tokens[-1] if re.fullmatch(r"[0-9A-Fa-f:]{17}", tokens[-1]) else ""
            host = tokens[-2] if mac else tokens[-1]
            name_tokens = tokens[1:-2] if mac else tokens[1:-1]
            name = " ".join(name_tokens)
            put_device(name, host, mac)
            print(f"Added: {name} ({host})")
            return 0
        if cmd == "pair":
            pair_parser = argparse.ArgumentParser(prog="tv pair")
            pair_parser.add_argument("--name", required=True)
            pair_parser.add_argument("--host", required=True)
            pair_parser.add_argument("--mac", default="")
            pair_parser.add_argument("--code")
            pair_args = pair_parser.parse_args(tokens[1:])
            asyncio.run(pair_device(pair_args.name, pair_args.host, pair_args.code, pair_args.mac))
            return 0
        device = get_device(args.device)
        if cmd == "wake":
            wake(device)
            print(f"Wake-on-LAN sent to {device['name']}.")
            return 0
        if cmd == "status":
            asyncio.run(status(device))
            return 0
        if cmd in {"diagnose", "doctor"}:
            asyncio.run(diagnose(device))
            return 0
        if cmd == "launch":
            if len(tokens) < 2:
                raise ValueError("Missing app name.")
            asyncio.run(launch(device, tokens[1]))
            return 0
        if cmd == "text":
            if len(tokens) < 2:
                raise ValueError("Usage: couch-remote text TEXT")
            asyncio.run(send_text(device, " ".join(tokens[1:])))
            return 0
        if cmd == "key":
            if len(tokens) < 2:
                raise ValueError("Usage: couch-remote key KEY [KEY...]")
            asyncio.run(send_keys(device, tokens[1:]))
            return 0
        if cmd == "action":
            if len(tokens) < 2:
                raise ValueError("Usage: couch-remote action ACTION [ACTION...]")
            asyncio.run(send_actions(device, tokens[1:]))
            return 0
        asyncio.run(send_actions(device, tokens))
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
