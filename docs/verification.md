# Verification

Release checks cover the application, bundled extractor, installers and update requests. Synthetic PKGs contain generated metadata and independently encrypted test data, with no game files. They do not exercise encrypted PFS game payloads.

## Application tests

The release workflow runs the test suite on Windows x64, Ubuntu 22.04 x64, macOS 15 arm64 and macOS 15 Intel with Python 3.12 and PySide6 Essentials 6.10.3. Each rebuilt release must pass all four jobs.

| Check | Result |
| --- | --- |
| Complete test suite | 87 tests |
| Actual patched native engine | 37 extraction checks |
| Packaged Windows application | Native window opens; bundled extraction succeeds with a restricted PATH and no development Python |
| Windows setup | Installed to an isolated project folder, opened the app, extracted a fixture and uninstalled |
| Distribution inputs | Pinned source hashes, version, notices and four platform jobs checked |
| UI inspection | Default 1060×780, minimum 900×660 with details open, and About inspected |

The tests cover:

- Bounded PKG/SFO metadata reads and game/update/DLC classification.
- Nonzero exits, documented zero-exit failures, incomplete progress and missing engines.
- Cancellation, child-process shutdown, staging cleanup and numbered output folders.
- UI queue behavior, retry, failed-job continuation and close during extraction.
- The compiled engine processing synthetic metadata-only packages, including Unicode paths and a filename collision that caused the original Windows binary to open the wrong file.
- AES-CBC metadata with known plaintext at lengths 1, 15, 16, 17, 31, 32 and 532 bytes for all four NP entry types. Each extraction runs twice; a truncated final block must fail and leave no output.
- License-only DLC with an unset total-size field, plus rejection of inconsistent metadata.
- Separate title-ID export folders, `-patch` folders and numbered duplicate CUSA folders, without an extra filename directory.
- One automatic startup request to this repository's latest stable release, manual retry, HTTP errors and invalid responses.
- Platform-specific download selection, rejection of another repository's release URL and About update actions.

The Windows UTF-8 manifest is tested with Japanese, German and emoji names. Windows builds compile the pinned source with MSYS2 UCRT64 and link the native dependencies statically. The backend provenance record includes the upstream commit, correction digest and executable hashes.

The Windows installer test uses a temporary installation and removes it after checking startup and extraction.

Source review found missing native compatibility declarations. The project-owned `packaging/native/compatibility.h` supplies `<optional>` and maps the upstream Darwin file-seek call to `fseeko`, preserving the pinned source files. Git attributes preserve upstream bytes during Windows checkouts.

## Native release checks

The [desktop build workflow](../.github/workflows/build.yml) builds and tests every distribution on its target operating system. Publication requires all four jobs to pass.

| Distribution | Verified behavior |
| --- | --- |
| Windows setup | Temporary installation, native app startup, exact synthetic extraction, invalid-input rejection and uninstall |
| Linux portable tar.gz | Extracted archive, executable permissions, native X11 window and extraction |
| Linux DEB | Extracted payload, desktop entry, system installation, reinstallation, extraction and removal |
| macOS arm64 and Intel ZIP | Extracted app, matching architecture, ad-hoc signature, native Cocoa window and extraction |
| macOS arm64 and Intel DMG | Read-only mount, Applications link, app copy, signature, native window and extraction |

Packaged checks remove development Python and Qt paths and restrict PATH to system directories. Tests verify unchanged input files, exact extracted fixture bytes and rejection of invalid PKGs. Every packaged copy also makes a real startup request to the GitHub release API. Before a public release exists, GitHub returns 404; after publication, the installed Windows copy must report the current release.

The runtime packages contain the app, extractor, needed libraries and license notices, without test suites or build scripts.

## Additional Windows checks

Local checks use a real game PKG, its update and a license-only DLC. Two extractions of each input compare all files by SHA-256: 28,831 game files, 442 update files and ten DLC files. Input hashes are checked before and after extraction.

An independent RSA/AES implementation decrypts the packages' NP metadata for a byte-for-byte comparison. The original extractor read beyond an undersized ciphertext buffer, producing varying final bytes in `sce_sys/npbind.dat`. The project-owned patch reads the entire padded block, checks its bounds and read length, decrypts it, and trims the result to the logical entry size. Synthetic regression tests reproduced this defect before the patch.

The original vendored source remains byte-identical to its pinned revision. CMake applies `packaging/native/np-entry-padding.patch` to a build-directory copy on every target platform.

These proprietary inputs, extracted contents and local paths are excluded from the repository and release packages. Automated regression tests use generated metadata-only fixtures.

## Verification limits

| Check | State |
| --- | --- |
| Full game extraction and comparison | One game/update pair and a license-only DLC checked on Windows; repeated-output and independent metadata comparisons described above |
| Real game checks on Linux and macOS; emulator boot | Not performed |
| Windows 10 version 1903 baseline | Not tested on that OS version |
| Windows Authenticode signature | Not configured |
| Apple Developer signature and notarization | Not configured |

The extractor's original file-write/decompression checks remain limited. The UI checks completion records and expected output metadata, but cannot certify the full integrity of game contents.
