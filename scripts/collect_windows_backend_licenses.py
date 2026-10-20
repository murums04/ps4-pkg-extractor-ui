import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    compiler = shutil.which("g++")
    if not compiler:
        raise RuntimeError("Put the MSYS2 UCRT64 bin directory on PATH.")
    prefix = Path(compiler).resolve().parent.parent
    if prefix.name != "ucrt64":
        raise RuntimeError("The Windows backend uses the MSYS2 UCRT64 toolchain.")
    database = {}
    for description in (prefix.parent / "var/lib/pacman/local").glob("*/desc"):
        sections = description.read_text(encoding="utf-8").split("\n\n")
        values = {}
        for section in sections:
            lines = section.strip().splitlines()
            if lines and lines[0].startswith("%"):
                values[lines[0].strip("%")] = lines[1:]
        if "NAME" in values:
            database[values["NAME"][0]] = values
    destination = ROOT / "licenses/Windows-runtime"
    destination.mkdir(parents=True, exist_ok=True)
    records = {}
    for name in ("gcc", "libgcc", "libstdc++", "crt", "headers", "winpthreads", "libwinpthread", "crypto++", "zlib"):
        package = f"mingw-w64-ucrt-x86_64-{name}"
        metadata = database[package]
        notices = prefix / "share/licenses" / name
        if not notices.is_dir() or not any(notices.iterdir()):
            raise RuntimeError(f"Missing Windows runtime notices: {package}")
        shutil.copytree(notices, destination / name, dirs_exist_ok=True)
        records[package] = {
            "version": metadata["VERSION"][0],
            "source_package": metadata["BASE"][0],
            "source": metadata["URL"][0],
            "license": metadata["LICENSE"],
        }
    (destination / "packages.json").write_text(
        json.dumps(records, indent=2) + "\n", encoding="utf-8", newline="\n")
    print("WINDOWS_RUNTIME_NOTICES_COLLECTED")


if __name__ == "__main__":
    main()
