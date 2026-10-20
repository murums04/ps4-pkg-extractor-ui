import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(*arguments, environment=None):
    subprocess.run([sys.executable, *arguments], cwd=ROOT, env=environment, check=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iscc", type=Path)
    args = parser.parse_args()
    run("scripts/fetch_backend.py")
    if sys.platform == "win32":
        run("scripts/collect_windows_backend_licenses.py")
    run("-m", "pytest", "-q")
    run("scripts/prepare_assets.py")
    environment = os.environ.copy()
    environment["PYINSTALLER_CONFIG_DIR"] = str(ROOT / ".work" / "pyinstaller-cache")
    environment["TEMP"] = environment["TMP"] = str(ROOT / ".work" / "tmp")
    Path(environment["TEMP"]).mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        environment["PATH"] = os.pathsep.join([str(Path(sys.executable).parent),
                                              environment["SYSTEMROOT"] + "/System32",
                                              environment["SYSTEMROOT"]])
    run("-m", "PyInstaller", "--noconfirm", "--clean",
        "--distpath", "packages/local", "--workpath", ".work/pyinstaller",
        "packaging/app.spec", environment=environment)
    if sys.platform == "linux":
        run("scripts/collect_linux_licenses.py", "--toc", ".work/pyinstaller/app/COLLECT-00.toc",
            "--destination", "licenses/Linux-runtime")
    if sys.platform == "darwin":
        run("scripts/collect_macos_licenses.py")
    arguments = ["scripts/package_release.py"]
    if args.iscc:
        arguments.extend(["--iscc", str(args.iscc.resolve())])
    run(*arguments)
    run("scripts/verify.py", "package")
    print("BUILD_VERIFIED")


if __name__ == "__main__":
    main()
