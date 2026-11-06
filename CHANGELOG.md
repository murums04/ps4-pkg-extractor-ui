# Changelog

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
