import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from pkg_extractor_ui import __version__
from pkg_extractor_ui.backend import bundled_command
from tests.fixtures import write_encrypted_np_pkg, write_license_pkg, write_pkg


def run_tests(native=False):
    command = [sys.executable, "-m", "pytest", "-q"]
    if native:
        bundled_command()
        command += ["tests/test_native_backend.py"]
    subprocess.run(command, cwd=ROOT, check=True)
    print("BACKEND_FIXTURE_VERIFIED" if native else "TEST_SUITE_VERIFIED")


def packaged_executable():
    root = ROOT / "packages" / "local"
    if sys.platform == "win32":
        return root / "ps4-pkg-extractor-ui" / "PS4 PKG Extractor UI.exe"
    if sys.platform == "darwin":
        return root / "PS4 PKG Extractor UI.app/Contents/MacOS/PS4 PKG Extractor UI"
    return root / "ps4-pkg-extractor-ui" / "ps4-pkg-extractor-ui"


def check_executable(executable: Path, work: Path):
    environment = os.environ.copy()
    for name in ("PYTHONPATH", "PYTHONHOME", "QT_PLUGIN_PATH", "QT_QPA_PLATFORM_PLUGIN_PATH",
                 "QT_QPA_PLATFORM", "LD_LIBRARY_PATH", "LD_LIBRARY_PATH_ORIG",
                 "DYLD_LIBRARY_PATH", "DYLD_FALLBACK_LIBRARY_PATH"):
        environment.pop(name, None)
    if sys.platform == "win32":
        environment["PATH"] = os.pathsep.join([environment["SYSTEMROOT"] + "/System32",
                                              environment["SYSTEMROOT"]])
    else:
        environment["PATH"] = "/usr/bin:/bin"
    expected_platform = {"win32": "windows", "darwin": "cocoa", "linux": "xcb"}[sys.platform]
    environment["QT_QPA_PLATFORM"] = expected_platform
    options = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}
    report = work / "ui.json"
    subprocess.run([str(executable), "--check-ui", str(report)], cwd=work, env=environment,
                   timeout=30, check=True, **options)
    observation = json.loads(report.read_text(encoding="utf-8"))
    assert observation["visible"] and observation["width"] >= 900
    assert observation["platform"] == expected_platform
    assert Path(observation["extractor"]).is_file()
    update_report = work / "updates.json"
    subprocess.run([str(executable), "--check-updates", str(update_report)], cwd=work, env=environment,
                   timeout=30, check=True, **options)
    update = json.loads(update_report.read_text(encoding="utf-8"))
    endpoint = "https://api.github.com/repos/murums04/ps4-pkg-extractor-ui/releases/latest"
    assert update["endpoint"] == endpoint and update["requests"] == [endpoint]
    assert update["state"] in {"current", "available", "unpublished"}
    print(f"PACKAGED_UPDATE_CHECK_VERIFIED: {expected_platform}, {update['state']}")
    source = write_pkg(work, "日本語 & fixture.pkg", extra_data=b"packaged engine check")
    original = source.read_bytes()
    report = work / "extraction.json"
    subprocess.run([str(executable), "--extract", str(source), "--output-dir", str(work / "結果"),
                    "--report", str(report)], cwd=work, env=environment, timeout=30, check=True, **options)
    result = json.loads(report.read_text(encoding="utf-8"))
    assert len(result) == 1 and result[0]["status"] == "extracted"
    assert Path(result[0]["output"]) == work / "結果" / "CUSA00001"
    output = Path(result[0]["output"]) / "sce_sys" / str(0x777777)
    assert output.read_bytes() == b"packaged engine check"
    assert source.read_bytes() == original
    plaintext = bytes((index * 37 + 11) % 256 for index in range(532))
    encrypted = write_encrypted_np_pkg(work, plaintext)
    license_pkg = write_license_pkg(work)
    originals = {path: path.read_bytes() for path in (encrypted, license_pkg)}
    encrypted_report = work / "encrypted-metadata.json"
    subprocess.run([str(executable), "--extract", str(encrypted), str(license_pkg),
                    "--output-dir", str(work / "metadata"), "--report", str(encrypted_report)],
                   cwd=work, env=environment, timeout=30, check=True, **options)
    metadata_results = json.loads(encrypted_report.read_text(encoding="utf-8"))
    assert len(metadata_results) == 2 and all(item["status"] == "extracted" for item in metadata_results)
    assert (Path(metadata_results[0]["output"]) / "sce_sys/npbind.dat").read_bytes() == plaintext
    assert (Path(metadata_results[1]["output"]) / "EXAMPLECONTENT01/sce_sys/param.sfo").is_file()
    assert [Path(item["output"]).name for item in metadata_results] == ["CUSA00001", "CUSA00001 (2)"]
    assert all(path.read_bytes() == contents for path, contents in originals.items())
    print("PACKAGED_ENCRYPTED_METADATA_AND_DLC_VERIFIED")
    bad = work / "broken.pkg"
    bad.write_bytes(b"not a package")
    bad_report = work / "failure.json"
    failed = subprocess.run([str(executable), "--extract", str(bad), "--output-dir", str(work / "out"),
                             "--report", str(bad_report)], cwd=work, env=environment, timeout=15, **options)
    assert failed.returncode == 1
    assert json.loads(bad_report.read_text(encoding="utf-8"))[0]["status"] == "failed"


def verify_package():
    executable = packaged_executable()
    assert executable.is_file(), executable
    payload = executable.parent
    if sys.platform == "darwin":
        payload = payload.parent / "Resources"
    for name in ("README.md", "CHANGELOG.md", "docs", "tests", "scripts", ".venv", ".git"):
        assert not (payload / name).exists(), f"Unexpected development file: {name}"
    for name in ("LICENSE", "THIRD_PARTY_NOTICES.md", "licenses/Python.txt"):
        assert (payload / name).is_file(), f"Missing notice: {name}"
    work_root = ROOT / ".work"
    work_root.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="package-check-", dir=work_root) as directory:
        check_executable(executable, Path(directory))
    print("WINDOWS_PACKAGE_VERIFIED" if sys.platform == "win32" else "NATIVE_PACKAGE_VERIFIED")


def verify_windows_installer():
    installer = ROOT / "packages" / f"ps4-pkg-extractor-ui-{__version__}-windows-x64-setup.exe"
    install_log = ROOT / ".work" / "installer-check.log"
    with tempfile.TemporaryDirectory(prefix="installer-check-", dir=ROOT / ".work") as directory:
        work = Path(directory)
        destination = work / "installed"
        options = {"creationflags": subprocess.CREATE_NO_WINDOW}
        try:
            subprocess.run([str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART",
                            "/SP-", "/NOICONS", "/TASKS=", f"/DIR={destination}", f"/LOG={install_log}"],
                           timeout=120, check=True, **options)
            smoke = work / "smoke"
            smoke.mkdir()
            check_executable(destination / "PS4 PKG Extractor UI.exe", smoke)
        finally:
            uninstaller = destination / "unins000.exe"
            if uninstaller.is_file():
                subprocess.run([str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                               timeout=120, check=True, **options)
        assert not (destination / "PS4 PKG Extractor UI.exe").exists()
    print("WINDOWS_INSTALLER_VERIFIED")


def verify_distribution():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["version"] == __version__
    manifest_path = ROOT / "vendor/shadps4plus/SOURCE.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["commit"] == "771a8d58aff540448c7cbace7c40a66a5daf010d"
    for name, hashes in manifest["files"].items():
        data = (manifest_path.parent / name).read_bytes()
        assert hashlib.sha256(data).hexdigest() == hashes["sha256"], name
        assert hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest() == hashes["git_blob"]
    required = ["LICENSE", "THIRD_PARTY_NOTICES.md", "docs/building.md", "docs/verification.md",
                "packaging/installer.iss", "packaging/native/CMakeLists.txt",
                "packaging/native/compatibility.h", "packaging/app.spec",
                "packaging/native/np-entry-padding.patch",
                "packaging/ps4-pkg-extractor-ui.desktop", ".github/workflows/build.yml",
                "scripts/collect_linux_licenses.py", "scripts/collect_macos_licenses.py",
                "scripts/collect_windows_backend_licenses.py",
                "scripts/verify_native_installers.py",
                "licenses/Python.txt", "licenses/Extractor/GPL-2.0.txt",
                "licenses/Extractor/Crypto++.txt", "licenses/Extractor/zlib.txt",
                "licenses/Extractor/libc++.txt", "assets/icon.ico", "assets/icon.icns"]
    for name in required:
        assert (ROOT / name).stat().st_size > 0, name
    workflow = (ROOT / ".github/workflows/build.yml").read_text(encoding="utf-8")
    for runner in ("windows-latest", "macos-15", "macos-15-intel", "ubuntu-22.04"):
        assert runner in workflow, runner
    for script in (ROOT / "scripts").glob("*.py"):
        compile(script.read_text(encoding="utf-8"), str(script), "exec")
    source = ROOT / "packages" / f"ps4-pkg-extractor-ui-{__version__}-source.zip"
    if source.is_file():
        with zipfile.ZipFile(source) as archive:
            assert archive.testzip() is None
            assert any(name.endswith("vendor/shadps4plus/src/core/file_format/pkg.cpp") for name in archive.namelist())
            assert not any("/.work/" in name or "/.venv/" in name for name in archive.namelist())
            for name in archive.namelist():
                relative = Path(*Path(name).parts[1:])
                assert archive.read(name) == (ROOT / relative).read_bytes(), f"Stale source archive: {relative}"
    print("DISTRIBUTION_INPUTS_VERIFIED")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("check", choices=("tests", "backend", "package", "installer", "distribution"))
    args = parser.parse_args()
    checks = {"tests": run_tests, "backend": lambda: run_tests(True), "package": verify_package,
              "installer": verify_windows_installer, "distribution": verify_distribution}
    checks[args.check]()


if __name__ == "__main__":
    main()
