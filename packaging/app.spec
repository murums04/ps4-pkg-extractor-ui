import sys
from pathlib import Path

root = Path(SPECPATH).parent
windows = sys.platform == "win32"
macos = sys.platform == "darwin"
name = "PS4 PKG Extractor UI" if windows or macos else "ps4-pkg-extractor-ui"
backend = root / "backend"
binaries = [(str(backend / ("pkg_extractor.exe" if windows else "pkg_extractor")), "backend")]
analysis = Analysis(
    [str(root / "packaging" / "launch.py")],
    pathex=[str(root / "src")],
    binaries=binaries,
    datas=[(str(root / "assets" / asset), "assets")
           for asset in ("icon.svg", "github.svg", "kofi.png")]
          + [(str(backend / "provenance.json"), "backend")],
    excludes=["tkinter", "pytest", "PIL", "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtTest"],
    noarchive=False,
)
archive = PYZ(analysis.pure)
options = {"version": str(root / "packaging" / "version-info.txt")} if windows else {}
executable = EXE(
    archive, analysis.scripts, [], exclude_binaries=True, name=name,
    debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
    console=not (windows or macos),
    icon=str(root / "assets" / ("icon.icns" if macos else "icon.ico")),
    **options,
)
collection = COLLECT(
    executable, analysis.binaries, analysis.datas,
    strip=False, upx=False, name="ps4-pkg-extractor-ui",
)
if macos:
    application = BUNDLE(
        collection, name="PS4 PKG Extractor UI.app",
        icon=str(root / "assets" / "icon.icns"),
        bundle_identifier="io.murums.ps4-pkg-extractor-ui",
        info_plist={
            "CFBundleShortVersionString": "0.1.0", "CFBundleVersion": "0.1.0",
            "NSHighResolutionCapable": True, "LSMinimumSystemVersion": "15.0",
        },
    )
