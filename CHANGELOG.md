# Changelog

## 1.0.5 - 2026-06-09

- Fixed the "Pair Selected" button in the setup window, which raised an internal error (an undefined reference) and never started pairing. The 1.0.4 command-parsing fix was not enough on its own because the graphical pairing path crashed before launching the pairing command.

## 1.0.4 - 2026-06-09

- Fixed pairing command parsing when subcommand options are passed after `pair`
- Added pairing timeouts so the setup UI reports unresponsive TVs instead of appearing stuck

## 1.0.3 - 2026-06-09

- Fixed Android TV discovery inside Flatpak by using Python mDNS discovery instead of relying on the host `avahi-browse` command
- Added pinned Flatpak wheels for `zeroconf` and `ifaddr`

## 1.0.2 - 2026-06-08

- Renamed Flatpak app ID to `io.github.angelodelorenzo.couch-remote` to match the GitHub repository
- Added aarch64 Python dependency wheels to the Flatpak manifest
- Removed unnecessary XDG config filesystem permission
- Added IPC sharing required for fallback X11

## 1.0.1 - 2026-06-08

- Updated Flatpak manifest to use pinned Python wheel sources with SHA256 hashes
- Removed network access from the Flatpak build sandbox
- Verified Flatpak build with `--disable-download`

## 1.0.0 - 2026-06-08

First stable Android TV and Google TV focused release.

- Added GTK remote interface inspired by physical TV remotes
- Added Android TV Remote v2 pairing
- Added local network discovery
- Added multiple saved TV profiles
- Added Wake-on-LAN support
- Added configurable action-to-key mappings
- Added key tester for model-specific buttons
- Added text input from the computer keyboard
- Added diagnostics for connection and pairing troubleshooting
- Added command line interface
- Added desktop launcher, AppStream metadata, icon, and Flatpak manifest
