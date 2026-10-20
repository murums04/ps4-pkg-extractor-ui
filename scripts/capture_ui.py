import os
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))
os.environ.setdefault("QT_QPA_PLATFORM", "windows" if sys.platform == "win32" else "offscreen")

from PySide6.QtWidgets import QApplication
from pkg_extractor_ui.window import MainWindow
from pkg_extractor_ui.about import AboutDialog
from tests.fixtures import write_pkg
from qt_fonts import load_capture_fonts


def main():
    work_root = ROOT / ".work"
    work_root.mkdir(exist_ok=True)
    images = ROOT / "docs" / "images"
    images.mkdir(parents=True, exist_ok=True)
    app = QApplication([])
    load_capture_fonts()
    app.setStyle("Fusion")
    with TemporaryDirectory(prefix="ui-capture-", dir=work_root) as directory:
        work = Path(directory)
        window = MainWindow()
        window.show()
        window.add_files([
            write_pkg(work, "example-game.pkg"),
            write_pkg(work, "example-update.pkg", "gp", 0x100000),
            write_pkg(work, "example-dlc.pkg", "ac"),
        ])
        window.output_edit.setText(str(work / "PKG output"))
        window.start_extraction()
        deadline = time.monotonic() + 15
        while window.worker is not None and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.01)
        assert window.worker is None and list(window.results.values()) == ["Extracted"] * 3
        window.output_edit.setText("PKG output")
        window.table.clearSelection()
        window.table.clearFocus()
        app.processEvents()
        assert window.grab().save(str(images / "app.png"))
        window.resize(window.minimumSize())
        window.toggle_details()
        app.processEvents()
        assert window.grab().save(str(images / "minimum.png"))
        about = AboutDialog(window.update_checker, window)
        about.show()
        app.processEvents()
        assert about.grab().save(str(images / "about.png"))
        about.close()
        window.close()
    print("UI_CAPTURED_FROM_METADATA_FIXTURES")


if __name__ == "__main__":
    main()
