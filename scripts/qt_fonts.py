import os
import sys
from pathlib import Path

from PySide6.QtGui import QFontDatabase


def load_capture_fonts():
    if sys.platform == "win32" and not QFontDatabase.families():
        folder = Path(os.environ["SystemRoot"]) / "Fonts"
        for name in ("segoeui.ttf", "seguisb.ttf", "segoeuib.ttf", "arial.ttf", "arialbd.ttf", "consola.ttf"):
            if QFontDatabase.addApplicationFont(str(folder / name)) < 0:
                raise RuntimeError(f"Could not load the system font for capture: {name}")
