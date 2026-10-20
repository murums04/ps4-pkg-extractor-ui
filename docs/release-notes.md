# murums PS4 PKG Extractor UI 0.1.0

First release of the PKG extractor UI by **murums**, based on [AzaharPlus/shadPS4Plus](https://github.com/AzaharPlus/shadPS4Plus).

- Queue games, updates and DLC with drag and drop, progress and cancellation.
- Extract each package into its own title-ID folder, with `-patch` for updates and numbered duplicates.
- Support license-only DLC and corrected encrypted-metadata reads in the bundled extractor.
- Check GitHub for updates at startup and through About; install updates manually.

| Platform | Installer | Portable |
| --- | --- | --- |
| Windows x64 | [Setup EXE](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.0/ps4-pkg-extractor-ui-0.1.0-windows-x64-setup.exe) | [ZIP](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.0/ps4-pkg-extractor-ui-0.1.0-windows-x64-portable.zip) |
| macOS · Apple Silicon | [DMG](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.0/ps4-pkg-extractor-ui-0.1.0-macos-arm64.dmg) | [ZIP](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.0/ps4-pkg-extractor-ui-0.1.0-macos-arm64-portable.zip) |
| macOS · Intel | [DMG](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.0/ps4-pkg-extractor-ui-0.1.0-macos-x64.dmg) | [ZIP](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.0/ps4-pkg-extractor-ui-0.1.0-macos-x64-portable.zip) |
| Linux x64 | [DEB](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.0/ps4-pkg-extractor-ui-0.1.0-linux-x64.deb) | [tar.gz](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.0/ps4-pkg-extractor-ui-0.1.0-linux-x64-portable.tar.gz) |

Choose an installer for normal use. Portable packages need full extraction. Python, Qt and the extractor are included; GitHub's **Source code** downloads do not contain the app.

[SHA-256 checksums](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.0/SHA256SUMS.txt) · [Source ZIP](https://github.com/murums04/ps4-pkg-extractor-ui/releases/download/v0.1.0/ps4-pkg-extractor-ui-0.1.0-source.zip).

Release checks cover 87 tests, including 37 checks with the actual native extractor; native app startup, GitHub update requests, synthetic extraction and invalid-input rejection. The four-target build workflow also checks the Windows installer, Linux install/reinstall/removal and both macOS ZIP/DMG copies. All four jobs must pass before publication.

Additional Windows checks extract a real game, update and license-only DLC twice, compare all output files by SHA-256 and check encrypted metadata against an independent decryption. The source patch corrects the varying final bytes previously produced in `sce_sys/npbind.dat`.

Windows executables are unsigned. Windows 10 remains untested. macOS 15 or newer is required; apps are ad-hoc signed and not notarized. Linux packages target Ubuntu 22.04 or newer. Real game checks on Linux and macOS have not been performed; the upstream extractor's integrity-checking limits still apply.

[Installation and supported systems](https://github.com/murums04/ps4-pkg-extractor-ui/blob/v0.1.0/docs/building.md) · [Test coverage](https://github.com/murums04/ps4-pkg-extractor-ui/blob/v0.1.0/docs/verification.md).

UI: GPL-3.0-only. Extractor: GPL-2.0-or-later. Bundled dependency notices and corresponding source references are included.
