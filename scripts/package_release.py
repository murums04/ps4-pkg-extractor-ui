import argparse
import hashlib
import platform
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pkg_extractor_ui import __version__

PREFIX = f"ps4-pkg-extractor-ui-{__version__}"
SOURCE_FOLDERS = ("src", "tests", "scripts", "packaging", "assets", "licenses", "vendor", ".github")
SOURCE_FILES = ("README.md", "LICENSE", "THIRD_PARTY_NOTICES.md", "CHANGELOG.md",
                "pyproject.toml", "requirements-build.txt", ".gitignore", ".gitattributes",
                "docs/building.md", "docs/verification.md", "docs/release-notes.md",
                "docs/images/logo.png", "docs/images/app.png")
LINUX_DEPENDENCIES = (
    "libc6 (>= 2.35), libstdc++6, libgcc-s1, libglib2.0-0, libgl1, libegl1, libopengl0, "
    "libdbus-1-3, libfontconfig1, libfreetype6, libx11-6, libx11-xcb1, libxext6, "
    "libxcb1, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, "
    "libxcb-randr0, libxcb-render0, libxcb-render-util0, libxcb-shape0, libxcb-shm0, "
    "libxcb-sync1, libxcb-xfixes0, libxcb-xinerama0, libxcb-xkb1, libxkbcommon0, libxkbcommon-x11-0"
)


def hash_file(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def copy_notices(destination):
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(ROOT / name, destination / name)
    runtime = {"win32": "Windows-runtime", "linux": "Linux-runtime", "darwin": "macOS-runtime"}[sys.platform]
    for path in (ROOT / "licenses").iterdir():
        if path.name.endswith("-runtime") and path.name != runtime:
            continue
        target = destination / "licenses" / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if path.is_dir():
            shutil.copytree(path, target, dirs_exist_ok=True)
        else:
            shutil.copy2(path, target)


def create_source_archive(output):
    files = [ROOT / name for name in SOURCE_FILES]
    for folder in SOURCE_FOLDERS:
        files.extend(path for path in (ROOT / folder).rglob("*")
                     if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc")
    archive_path = output / f"{PREFIX}-source.zip"
    with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(files):
            archive.write(path, Path(PREFIX) / path.relative_to(ROOT))
    return archive_path


def package_windows(dist, output, iscc):
    if iscc is None or not iscc.is_file():
        raise RuntimeError("Pass --iscc with the path to the Inno Setup compiler.")
    payload = dist / "ps4-pkg-extractor-ui"
    copy_notices(payload)
    portable = output / f"{PREFIX}-windows-x64-portable.zip"
    with zipfile.ZipFile(portable, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(payload.rglob("*")):
            if path.is_file():
                archive.write(path, Path("ps4-pkg-extractor-ui") / path.relative_to(payload))
    subprocess.run([str(iscc), "/Q", f"/DPayloadDirectory={payload}",
                    f"/DOutputDirectory={output}", str(ROOT / "packaging" / "installer.iss")], check=True)
    return [portable, output / f"{PREFIX}-windows-x64-setup.exe"], "windows-x64"


def package_linux(dist, output, work):
    payload = dist / "ps4-pkg-extractor-ui"
    copy_notices(payload)
    portable = output / f"{PREFIX}-linux-x64-portable.tar.gz"
    with tarfile.open(portable, "w:gz") as archive:
        archive.add(payload, arcname=payload.name)
    stage = work / "deb"
    shutil.copytree(payload, stage / "opt" / payload.name, symlinks=True)
    control = stage / "DEBIAN"
    control.mkdir()
    (control / "control").write_text(
        f"Package: ps4-pkg-extractor-ui\nVersion: {__version__}\nArchitecture: amd64\n"
        "Maintainer: murums\nSection: utils\nPriority: optional\n"
        f"Depends: {LINUX_DEPENDENCIES}\n"
        "Description: Desktop UI for the shadPS4Plus PKG extractor\n"
        " Extracts PS4 packages into separate folders using a bundled extractor.\n", encoding="utf-8")
    desktop = stage / "usr/share/applications"
    desktop.mkdir(parents=True)
    shutil.copy2(ROOT / "packaging/ps4-pkg-extractor-ui.desktop", desktop)
    icons = stage / "usr/share/icons/hicolor/256x256/apps"
    icons.mkdir(parents=True)
    shutil.copy2(ROOT / "assets/icon.png", icons / "ps4-pkg-extractor-ui.png")
    docs = stage / "usr/share/doc/ps4-pkg-extractor-ui"
    docs.mkdir(parents=True)
    shutil.copy2(ROOT / "LICENSE", docs / "copyright")
    installer = output / f"{PREFIX}-linux-x64.deb"
    subprocess.run(["dpkg-deb", "--root-owner-group", "--build", str(stage), str(installer)], check=True)
    return [portable, installer], "linux-x64"


def package_macos(dist, output, work):
    architecture = platform.machine()
    if architecture not in ("arm64", "x86_64"):
        raise RuntimeError(f"Unsupported macOS architecture: {architecture}")
    target = "macos-" + ("arm64" if architecture == "arm64" else "x64")
    application = dist / "PS4 PKG Extractor UI.app"
    copy_notices(application / "Contents/Resources")
    subprocess.run(["codesign", "--force", "--deep", "--sign", "-", str(application)], check=True)
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(application)], check=True)
    portable = output / f"{PREFIX}-{target}-portable.zip"
    subprocess.run(["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent",
                    str(application), str(portable)], check=True)
    stage = work / "dmg"
    stage.mkdir()
    shutil.copytree(application, stage / application.name, symlinks=True)
    (stage / "Applications").symlink_to("/Applications", target_is_directory=True)
    image = output / f"{PREFIX}-{target}.dmg"
    subprocess.run(["hdiutil", "create", "-volname", "PS4 PKG Extractor UI",
                    "-srcfolder", str(stage), "-ov", "-format", "UDZO", str(image)], check=True)
    return [portable, image], target


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dist-dir", type=Path, default=ROOT / "packages" / "local")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "packages")
    parser.add_argument("--iscc", type=Path)
    args = parser.parse_args()
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    work_root = ROOT / ".work"
    work_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="packaging-", dir=work_root) as directory:
        if sys.platform == "win32":
            assets, target = package_windows(args.dist_dir.resolve(), output, args.iscc)
        elif sys.platform == "darwin":
            assets, target = package_macos(args.dist_dir.resolve(), output, Path(directory))
        elif sys.platform == "linux":
            assets, target = package_linux(args.dist_dir.resolve(), output, Path(directory))
        else:
            raise RuntimeError("Unsupported packaging platform.")
    assets.append(create_source_archive(output))
    (output / f"SHA256SUMS-{target}.txt").write_text(
        "".join(f"{hash_file(path)}  {path.name}\n" for path in assets), encoding="utf-8")
    print(f"PACKAGES_CREATED: {target}")


if __name__ == "__main__":
    main()
