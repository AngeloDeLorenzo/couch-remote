# Couch Remote

Couch Remote is a GTK remote control for Android TV and Google TV devices on the local network.

It provides a physical remote-style interface, network discovery, pairing, saved TV profiles, Wake-on-LAN, configurable key mappings, text input, diagnostics, app launching, and a command line interface.

![Couch Remote main window](docs/screenshots/main-window.png)

## Features

- Android TV / Google TV pairing over Android TV Remote v2
- Local network discovery with Avahi
- Multiple saved TV profiles
- Wake-on-LAN support
- Configurable action-to-key mappings per TV
- Key tester for model-specific buttons
- Text input from the computer keyboard
- Connection diagnostics
- GTK desktop interface
- Command line interface

## Install For Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
```

The GTK interface also requires PyGObject and GTK 3 from the system packages. Discovery requires `avahi-browse`.

On Debian-based systems:

```bash
sudo apt install python3-gi gir1.2-gtk-3.0 avahi-utils
```

## Usage

Start the graphical interface:

```bash
couch-remote-gui
```

From **Settings**, scan for Android TV devices, select one, then start pairing. The TV will show a code that must be entered in Couch Remote.

Command line examples:

```bash
couch-remote scan
couch-remote pair --name "Living Room TV" --host 192.168.1.50
couch-remote devices
couch-remote use "Living Room TV"
couch-remote status
couch-remote diagnose
couch-remote action volume_up
couch-remote text "search text"
couch-remote launch youtube
```

## Key Mapping

Couch Remote sends logical actions such as `volume_up`, `subtitle`, `teletext`, `guide`, and `ok`. Every action can be remapped per device:

```bash
couch-remote actions
couch-remote candidates
couch-remote map subtitle CAPTIONS
couch-remote map subtitle TV_MEDIA_CONTEXT_MENU
couch-remote map service_menu SETTINGS DPAD_DOWN DPAD_CENTER
couch-remote reset-map subtitle
```

The GTK app exposes the same workflow through **Settings** and **Test Keys**.

## Diagnostics

When a TV stops responding, run:

```bash
couch-remote diagnose
```

The diagnostics report checks the selected profile, certificate files, name/IP resolution, Android TV and Cast ports, and the Android TV Remote connection state. The same report is available from **Settings** and **Diagnostics** in the GTK app.

## Data And Privacy

Couch Remote stores device profiles and pairing certificates locally in:

```text
~/.config/couch-remote
```

Pairing certificates are required to control Android TV devices. Couch Remote does not send telemetry.

## Packaging

A Flatpak manifest is provided in:

```text
packaging/flatpak/io.github.angelodelorenzo.couch-remote.yml
```

The app id is:

```text
io.github.angelodelorenzo.couch-remote
```

## Limitations

Couch Remote 1.0 supports Android TV and Google TV only. Other TV ecosystems such as LG webOS, Samsung, Roku, and HDMI-CEC are intentionally out of scope for this release.

Some Android TV models use manufacturer-specific behavior for buttons such as subtitles, teletext, language, and colored keys. Use the key tester to find and remap the working code for your model.
