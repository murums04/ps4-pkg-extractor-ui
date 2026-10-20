import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QImage, QPainter
from PySide6.QtSvg import QSvgRenderer
from qt_fonts import load_capture_fonts

ROOT = Path(__file__).resolve().parents[1]


def main():
    application = QGuiApplication([])
    load_capture_fonts()
    renderer = QSvgRenderer(str(ROOT / "assets" / "icon.svg"))
    image = QImage(1024, 1024, QImage.Format.Format_ARGB32)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    target = ROOT / "assets"
    image.save(str(target / "icon-1024.png"))
    with Image.open(target / "icon-1024.png") as source:
        source.resize((256, 256), Image.Resampling.LANCZOS).save(target / "icon.png")
        source.save(target / "icon.ico", sizes=[(size, size) for size in (16, 24, 32, 48, 64, 128, 256)])
        source.save(target / "icon.icns")
    print("ICON_ASSETS_PREPARED")


if __name__ == "__main__":
    main()
