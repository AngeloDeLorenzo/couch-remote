# Release Checklist

## 1.0.0

- [x] Remove machine-specific paths from application code
- [x] Use an empty first-run configuration
- [x] Store pairing certificates under `~/.config/couch-remote`
- [x] Add Android TV diagnostics
- [x] Add configurable key mappings
- [x] Add desktop launcher
- [x] Add AppStream metadata
- [x] Add scalable app icon
- [x] Add Flatpak manifest
- [x] Add changelog
- [x] Add basic automated tests
- [x] Validate Python syntax
- [x] Validate desktop metadata when tools are available
- [x] Build Python wheel and source distribution
- [x] Install Python wheel in a clean virtual environment
- [x] Build Flatpak locally
- [x] Install Flatpak locally
- [x] Run Flatpak CLI smoke test
- [x] Capture public screenshot with a generic TV name
- [ ] Test pairing on at least two additional Android TV or Google TV devices
- [x] Regenerate Flatpak manifest with pinned/offline Python dependency sources
- [x] Create Git tag `v1.0.0`
- [x] Push `main` and `v1.0.0` to GitHub
- [x] Create GitHub release with wheel and source distribution

## Known Limitations

- Only Android TV and Google TV devices are supported.
- Some TV models expose manufacturer-specific key behavior. Use **Settings** and **Test Keys** to remap actions when needed.
- Wake-on-LAN depends on the TV keeping its network interface awake in standby.
- The current Flatpak manifest uses pinned Python wheels suitable for x86_64 builds. Multi-architecture Flathub submission may need additional wheels or source-based dependency builds.
