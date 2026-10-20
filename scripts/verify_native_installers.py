import argparse
import os
import platform
import plistlib
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

from package_release import hash_file
from verify import ROOT, __version__, check_executable


def check_runtime(folder):
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md", "licenses/Python.txt"):
        assert (folder / name).is_file(), f"Missing notice: {name}"
    for name in ("README.md", "CHANGELOG.md", "docs", "tests", "scripts"):
        assert not (folder / name).exists(), f"Unexpected development file: {name}"


def check_application(executable, work, label):
    assert os.access(executable, os.X_OK), executable
    work.mkdir()
    check_executable(executable, work)
    print(f"{label}: native UI, exact extraction, input preservation and invalid-input rejection passed")


def verify_linux(work, install):
    prefix = f"ps4-pkg-extractor-ui-{__version__}-linux-x64"
    portable = work / "portable"
    with tarfile.open(ROOT / "packages" / f"{prefix}-portable.tar.gz") as archive:
        archive.extractall(portable, filter="data")
    payload = portable / "ps4-pkg-extractor-ui"
    check_runtime(payload)
    check_application(payload / "ps4-pkg-extractor-ui", work / "portable-check", "Linux portable")

    package = ROOT / "packages" / f"{prefix}.deb"
    extracted = work / "debian"
    subprocess.run(["dpkg-deb", "--extract", str(package), str(extracted)], check=True)
    check_runtime(extracted / "opt/ps4-pkg-extractor-ui")
    desktop = extracted / "usr/share/applications/ps4-pkg-extractor-ui.desktop"
    subprocess.run(["desktop-file-validate", str(desktop)], check=True)
    check_application(extracted / "opt/ps4-pkg-extractor-ui/ps4-pkg-extractor-ui",
                      work / "debian-check", "Linux DEB payload")
    if install:
        status = subprocess.run(["dpkg-query", "-W", "-f=${Status}", "ps4-pkg-extractor-ui"],
                                capture_output=True, text=True)
        destination = Path("/opt/ps4-pkg-extractor-ui")
        desktop = Path("/usr/share/applications/ps4-pkg-extractor-ui.desktop")
        if (status.returncode == 0 and "installed" in status.stdout) or destination.exists() or desktop.exists():
            raise RuntimeError("An existing installation was found; refusing to replace it.")
        try:
            subprocess.run(["sudo", "apt-get", "install", "-y", str(package)], check=True)
            check_application(destination / "ps4-pkg-extractor-ui", work / "installed-check", "Linux installed")
            subprocess.run(["sudo", "dpkg", "-i", str(package)], check=True)
            check_application(destination / "ps4-pkg-extractor-ui", work / "reinstall-check", "Linux reinstalled")
        finally:
            subprocess.run(["sudo", "apt-get", "purge", "-y", "ps4-pkg-extractor-ui"], check=True)
        assert not destination.exists() and not desktop.exists()
        print("LINUX_INSTALL_REINSTALL_REMOVAL_VERIFIED")


def check_macos_application(application, work, label):
    check_runtime(application / "Contents/Resources")
    with (application / "Contents/Info.plist").open("rb") as stream:
        assert plistlib.load(stream)["LSMinimumSystemVersion"] == "15.0"
    subprocess.run(["codesign", "--verify", "--deep", "--strict", str(application)], check=True)
    executable = application / "Contents/MacOS/PS4 PKG Extractor UI"
    architecture = subprocess.check_output(["lipo", "-archs", str(executable)], text=True).strip()
    assert architecture == platform.machine(), architecture
    check_application(executable, work, label)


def verify_macos(work):
    architecture = {"arm64": "arm64", "x86_64": "x64"}[platform.machine()]
    prefix = f"ps4-pkg-extractor-ui-{__version__}-macos-{architecture}"
    portable = work / "portable"
    subprocess.run(["ditto", "-x", "-k", str(ROOT / "packages" / f"{prefix}-portable.zip"),
                    str(portable)], check=True)
    check_macos_application(portable / "PS4 PKG Extractor UI.app", work / "portable-check", "macOS ZIP")
    package = ROOT / "packages" / f"{prefix}.dmg"
    mount = work / "mounted"
    mount.mkdir()
    subprocess.run(["hdiutil", "attach", str(package), "-readonly", "-nobrowse",
                    "-mountpoint", str(mount)], check=True)
    application = work / "installed/PS4 PKG Extractor UI.app"
    try:
        assert (mount / "Applications").is_symlink()
        shutil.copytree(mount / application.name, application, symlinks=True)
    finally:
        subprocess.run(["hdiutil", "detach", str(mount)], check=True)
    check_macos_application(application, work / "dmg-check", "macOS DMG application copy")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true",
                        help="Test Linux install/reinstall/removal on a disposable native runner")
    args = parser.parse_args()
    if sys.platform not in ("linux", "darwin"):
        raise RuntimeError("Run this check on Linux or macOS.")
    target = "linux-x64" if sys.platform == "linux" else "macos-" + (
        "arm64" if platform.machine() == "arm64" else "x64")
    manifest = ROOT / "packages" / f"SHA256SUMS-{target}.txt"
    for line in manifest.read_text(encoding="utf-8").splitlines():
        digest, name = line.split("  ", 1)
        assert Path(name).name == name
        assert hash_file(ROOT / "packages" / name) == digest, name
    work_root = ROOT / ".work"
    work_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="native-install-check-", dir=work_root) as directory:
        if sys.platform == "linux":
            verify_linux(Path(directory), args.install)
        else:
            verify_macos(Path(directory))
    print(f"NATIVE_DISTRIBUTION_VERIFIED: {target}")


if __name__ == "__main__":
    main()
