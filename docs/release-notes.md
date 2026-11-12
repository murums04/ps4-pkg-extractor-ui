- Adding packages to a finished queue extracts only the new ones; failed packages can be retried without duplicate folders.
- Dropping a folder adds the PKG files it contains; drops onto the package list work too.
- Shows available updates in the main window.
- Rejects relative output paths that would depend on the app's start folder.
- Cleanup problems no longer hide the real extraction result.
- Accepts packages with non-UTF-8 display titles; clearer message for incomplete or split packages.
- Checks free space before extraction.
- Delete removes selected packages; cleaner table header and About links.

| Platform | Installer | Portable |
| --- | --- | --- |
| Windows x64 | [Setup EXE](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.2/ps4-pkg-extractor-ui-0.1.2-windows-x64-setup.exe) | [ZIP](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.2/ps4-pkg-extractor-ui-0.1.2-windows-x64-portable.zip) |
| macOS · Apple Silicon | [DMG](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.2/ps4-pkg-extractor-ui-0.1.2-macos-arm64.dmg) | [ZIP](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.2/ps4-pkg-extractor-ui-0.1.2-macos-arm64-portable.zip) |
| Linux x64 | [DEB](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.2/ps4-pkg-extractor-ui-0.1.2-linux-x64.deb) | [tar.gz](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.2/ps4-pkg-extractor-ui-0.1.2-linux-x64-portable.tar.gz) |

[SHA-256 checksums](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.2/SHA256SUMS.txt) · [Source ZIP](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.2/ps4-pkg-extractor-ui-0.1.2-source.zip)

Requires Windows 10 1903+, macOS 15+ on Apple Silicon, or Ubuntu 22.04+. Windows executables are unsigned; Mac apps are ad-hoc signed and not notarized. Python, Qt and the extractor are included.

[Installation](https://github.com/murums04/ps4-pkg-extractor-ui/blob/v0.1.2/docs/building.md) · UI: GPL-3.0-only; extractor: GPL-2.0-or-later. Bundled dependency notices included.
