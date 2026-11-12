# Changelog

## 0.1.2

- Queue: adding packages after a batch extracts only new packages; "Extract remaining" skips extracted packages.
- Input: dropped folders add their PKG files; the whole window accepts drops.
- Output: relative paths are rejected with a hint; the folder is rechecked when the window regains focus.
- Updates: an "Update available" button appears in the main window.
- Extraction: staging cleanup problems are logged instead of replacing the actual result or error; a hung extractor no longer crashes the CLI.
- Metadata: non-UTF-8 display strings in param.sfo no longer reject a package; incomplete or split packages get a clearer message.
- Extraction: checks free space in the output folder before starting.
- UI: Delete removes selected rows, aligned table header with rounded corners, labeled About links, summaries without zero counts.
- Tests run on a fresh checkout and skip symlink checks where Windows denies symlinks.

## 0.1.1

- Fail extraction on native file-write and decompression errors.
- Reject unsafe package output paths.
- Fixed CLI report errors and output-folder paths.
- Updated Pillow to 13.0.0, cryptography to 50.0.0 and setuptools to 84.1.0.
- Removed macOS Intel builds and downloads; macOS now targets Apple Silicon only.

## 0.1.0

- PKG queue, drag and drop, output selection, progress and cancellation.
- Game, update and DLC recognition; separate output folders.
- Dark navy and mint interface with queue details and an About dialog.
- GitHub update checks at startup and on demand; manual update installation.
- License-only DLC support, including packages with an unset total-size field.
- Bundled shadPS4Plus 1.1 extractor with corrected encrypted-metadata reads and Windows Unicode paths.
- Windows setup/ZIP, Linux DEB/tar.gz and macOS DMG/ZIP for Apple Silicon and Intel.
