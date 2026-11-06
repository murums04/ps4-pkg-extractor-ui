# murums PS4 PKG Extractor UI 0.1.1

- Stop extraction on native file-write and decompression errors.
- Reject unsafe package output paths.
- Fixed CLI report errors and output-folder paths.
- Update Pillow, cryptography and setuptools.
- macOS builds now target Apple Silicon only.

| Platform | Installer | Portable |
| --- | --- | --- |
| Windows x64 | [Setup EXE](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.1/ps4-pkg-extractor-ui-0.1.1-windows-x64-setup.exe) | [ZIP](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.1/ps4-pkg-extractor-ui-0.1.1-windows-x64-portable.zip) |
| macOS · Apple Silicon | [DMG](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.1/ps4-pkg-extractor-ui-0.1.1-macos-arm64.dmg) | [ZIP](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.1/ps4-pkg-extractor-ui-0.1.1-macos-arm64-portable.zip) |
| Linux x64 | [DEB](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.1/ps4-pkg-extractor-ui-0.1.1-linux-x64.deb) | [tar.gz](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.1/ps4-pkg-extractor-ui-0.1.1-linux-x64-portable.tar.gz) |

Choose an installer for normal use. Portable packages need full extraction. Python, Qt and the extractor are included; GitHub's **Source code** downloads do not contain the app.

[SHA-256 checksums](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.1/SHA256SUMS.txt) · [Source ZIP](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.1/ps4-pkg-extractor-ui-0.1.1-source.zip).

Local macOS arm64 checks pass 148 tests, including 82 with the native extractor. Generated encrypted PFS fixtures cover exact payload output, invalid paths, decompression failures and write failures. The release workflow requires all three platform jobs to pass before publication.

Earlier Windows checks for 0.1.0 extracted a real game, update and license-only DLC twice, compared all output files by SHA-256 and checked encrypted metadata against an independent decryption. The source patch corrects the varying final bytes previously produced in `sce_sys/npbind.dat`.

Windows executables are unsigned and require Windows 10 version 1903 or newer. macOS requires Apple Silicon and version 15 or newer; apps are ad-hoc signed and not notarized. Linux packages target Ubuntu 22.04 or newer. The extractor does not certify the full integrity of game contents.

[Installation and supported systems](https://github.com/murums04/ps4-pkg-extractor-ui/blob/v0.1.1/docs/building.md) · [Test coverage](https://github.com/murums04/ps4-pkg-extractor-ui/blob/v0.1.1/docs/verification.md).

UI: GPL-3.0-only. Extractor: GPL-2.0-or-later. Bundled dependency notices and corresponding source references are included.
