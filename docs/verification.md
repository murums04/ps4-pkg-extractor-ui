# Verification

Release checks cover the application, bundled extractor, installers and update requests. Synthetic PKGs contain generated metadata and independently encrypted PFS payloads, with no game files.

## Application tests

The release workflow runs the test suite on Windows x64, Ubuntu 22.04 x64 and macOS 15 arm64 with Python 3.12 and PySide6 Essentials 6.10.3. Each rebuilt release must pass all three jobs.

| Check | Result |
| --- | --- |
| Local macOS arm64 test suite, 0.1.1 | 148 tests |
| Actual patched native engine on macOS arm64, 0.1.1 | 82 checks |
| Packaged macOS ZIP and DMG, 0.1.1 | Cocoa startup, exact payload extraction, corrupt-input rejection, version, architecture, signature and checksums passed |
| Manual packaged macOS UI, 0.1.1 | About, file selection, extraction, details and queue reset passed; nested Unicode output matched the fixture in a folder with a trailing space, and the input remained unchanged |
| Packaged Windows application, 0.1.0 | Native window opens; bundled extraction succeeds with a restricted PATH and no development Python |
| Windows setup, 0.1.0 | Installed to an isolated project folder, opened the app, extracted a fixture and uninstalled |
| Distribution inputs | Pinned source hashes, version and notices checked |
| Earlier UI inspection, 0.1.0 | Default 1060×780, minimum 900×660 with details open, and About inspected |

The tests cover:

- Bounded PKG/SFO metadata reads and game/update/DLC classification.
- Nonzero exits, documented zero-exit failures, incomplete progress and missing engines.
- Cancellation, child-process shutdown, staging cleanup and numbered output folders.
- UI queue behavior, retry, failed-job continuation and close during extraction.
- The compiled engine processing synthetic metadata-only packages, including Unicode paths and a filename collision that caused the original Windows binary to open the wrong file.
- AES-CBC metadata with known plaintext at lengths 1, 15, 16, 17, 31, 32 and 532 bytes for all four NP entry types. Each extraction runs twice; a truncated final block must fail and leave no output.
- Encrypted PFS payloads with exact compressed/uncompressed output; rejected checksums, truncated streams, short decompression and invalid metadata. Output-open, short-write and flush failures must fail without publishing partial output.
- Rejected unsafe PFS names, malformed directory records, inode aliases and symlinked package folders; valid nested Unicode paths and explicit output-base symlinks remain supported.
- CLI report errors before extraction and output-folder names containing spaces or a home-directory shortcut.
- License-only DLC with an unset total-size field, plus rejection of inconsistent metadata.
- Separate title-ID export folders, `-patch` folders and numbered duplicate CUSA folders, without an extra filename directory.
- One automatic startup request to this repository's latest stable release, manual retry, HTTP errors and invalid responses.
- Platform-specific download selection, rejection of another repository's release URL and About update actions.

The workflow tests the Windows UTF-8 manifest with Japanese, German and emoji names. Windows builds compile the pinned source with MSYS2 UCRT64 and link the native dependencies statically. The backend provenance record includes the upstream commit, correction digest and executable hashes.

The Windows installer test uses a temporary installation and removes it after checking startup and extraction.

Source review found missing native compatibility declarations. The project-owned `packaging/native/compatibility.h` supplies `<optional>` and maps the upstream Darwin file-seek call to `fseeko`, preserving the pinned source files. Git attributes preserve upstream bytes during Windows checkouts.

## Native release checks

The [desktop build workflow](../.github/workflows/build.yml) builds and tests every distribution on its target operating system. Publication requires all three jobs to pass.

| Distribution | Workflow checks |
| --- | --- |
| Windows setup | Temporary installation, native app startup, exact synthetic extraction, invalid-input rejection and uninstall |
| Linux portable tar.gz | Extracted archive, executable permissions, native X11 window and extraction |
| Linux DEB | Extracted payload, desktop entry, system installation, reinstallation, extraction and removal |
| macOS arm64 ZIP | Extracted app, matching architecture, ad-hoc signature, native Cocoa window and extraction |
| macOS arm64 DMG | Read-only mount, Applications link, app copy, signature, native window and extraction |

Packaged checks remove development Python and Qt paths and restrict PATH to system directories. Tests verify unchanged input files, exact extracted fixture bytes and rejection of invalid PKGs. Every packaged copy also makes a real startup request to the GitHub release API. Before a public release exists, GitHub returns 404; after publication, the installed Windows copy must report the current release.

The runtime packages contain the app, extractor, needed libraries and license notices, without test suites or build scripts.

## Additional Windows checks

Earlier checks for 0.1.0 used a real game PKG, its update and a license-only DLC. Two extractions of each input compared all files by SHA-256: 28,831 game files, 442 update files and ten DLC files. Input hashes were checked before and after extraction.

An independent RSA/AES implementation decrypts the packages' NP metadata for a byte-for-byte comparison. The original extractor read beyond an undersized ciphertext buffer, producing varying final bytes in `sce_sys/npbind.dat`. The project-owned patch reads the entire padded block, checks its bounds and read length, decrypts it, and trims the result to the logical entry size. Synthetic regression tests reproduced this defect before the patch.

The original vendored source remains byte-identical to its pinned revision. CMake applies `packaging/native/np-entry-padding.patch` and `packaging/native/extraction-errors.patch` to build-directory copies on every target platform.

These proprietary inputs, extracted contents and local paths are excluded from the repository and release packages. Automated regression tests use generated metadata and encrypted PFS payload fixtures.

## Runtime limits and signing

Windows executables are unsigned and require Windows 10 version 1903 or newer. macOS apps require Apple Silicon and macOS 15 or newer; they are ad-hoc signed and not notarized. Linux packages target Ubuntu 22.04 or newer.

Native write and decompression failures abort extraction. These checks do not certify the full integrity of game contents.
