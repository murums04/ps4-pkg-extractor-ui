# Third-party notices

## User interface

Copyright 2026 murums. GPL-3.0-only; see LICENSE.

## PKG extractor

AzaharPlus/shadPS4Plus, derived from the shadPS4 Emulator Project.

- Source: https://github.com/AzaharPlus/shadPS4Plus
- Release: `PKG_EXTRACTOR_1_1`
- Commit: `771a8d58aff540448c7cbace7c40a66a5daf010d`
- License: GPL-2.0-or-later, including individual file copyright notices. See `licenses/Extractor/GPL-2.0.txt`.
- The required source closure is included under `vendor/shadps4plus`, with per-file Git blob identities and SHA-256 values in `SOURCE.json`. The complete upstream source remains available at the referenced commit.
- All platforms compile the pinned source with the CMake configuration in `packaging/native`.
- `packaging/native/np-entry-padding.patch` corrects encrypted metadata reads, checks complete ciphertext blocks and verifies writes of decrypted entries. The build applies this project-owned patch to a build-directory copy; the vendored upstream files remain unchanged.
- Windows builds use MSYS2 UCRT64 and add an application manifest for UTF-8 filenames and long-path awareness. The preparation script records the upstream revision, patch digest and executable hashes.

Crypto++ is linked by the engine. Upstream references commit `effed0d0b865afc23ed67e0916f83734e4b9b3b7` of https://github.com/weidai11/cryptopp . Its compilation license and individual notices are in `licenses/Extractor/Crypto++.txt`.

zlib uses the zlib license; see `licenses/Extractor/zlib.txt`. Source: https://github.com/madler/zlib .

Windows links Crypto++, zlib and the GCC/MinGW runtime statically. The package includes their installed version records and licenses under `licenses/Windows-runtime`. GCC runtime libraries use GPL-3.0-or-later with the GCC Runtime Library Exception; MinGW-w64 and winpthreads notices are included there. Sources: https://gcc.gnu.org/ and https://www.mingw-w64.org/ . MSYS2 packaging recipes: https://github.com/msys2/MINGW-packages .

Native Linux packages collect distribution copyright files and installed package/source versions for bundled libraries. Native macOS builds collect Homebrew formula metadata and license files before packaging.

## Python and Qt

- Python 3.12: Python Software Foundation License and included notices, `licenses/Python.txt`. Source: https://www.python.org/downloads/source/
- OpenSSL: Apache-2.0; `licenses/OpenSSL.txt`. Source: https://github.com/openssl/openssl
- PySide6 Essentials and Shiboken6 6.10.3: The Qt Company Ltd. and contributors. Open-source terms include LGPL-3.0 and GPL-3.0; notices are collected under `licenses/Qt/pyside-setup`. Source: https://github.com/pyside/pyside-setup/tree/v6.10.3
- Qt 6.10.3: The Qt Company Ltd. and contributors, LGPL-3.0 shared libraries and applicable third-party notices in `licenses/Qt`. Sources: https://github.com/qt/qtbase/tree/v6.10.3 and https://github.com/qt/qtsvg/tree/v6.10.3
- PyInstaller: GPL-2.0-or-later with its bootloader distribution exception; `licenses/PyInstaller.txt`. Source: https://github.com/pyinstaller/pyinstaller
- Inno Setup: Copyright Jordan Russell and Martijn Laan; `licenses/InnoSetup.txt`. Source: https://jrsoftware.org/
- Microsoft Visual C++ runtime files are redistributed as supplied by the official Python and Qt wheels.

Qt remains dynamically linked. Users can replace its shared libraries with compatible modified builds; the application does not prevent replacement or reverse engineering for debugging those modifications. Modified macOS bundles need a new local signature.

The Qt notice collection includes more components than this application uses. A source ZIP accompanies each distribution; build instructions and dependency source locations support rebuilding with modified dependencies.

## Brand assets

The unmodified white GitHub Invertocat (`assets/github.svg`) comes from the [GitHub Brand Toolkit](https://brand.github.com/foundations/logo). It identifies links to the author's profile and the upstream project. GitHub trademarks are not covered by the application's GPL.

The Ko-fi cup (`assets/kofi.png`) comes from the [Ko-fi Creator Kit](https://more.ko-fi.com/brand-assets) and links to https://ko-fi.com/murums . It belongs to Ko-fi and is not covered by the application's GPL.
