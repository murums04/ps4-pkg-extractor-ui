import hashlib
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RELEASE = "PKG_EXTRACTOR_1_1"


def main():
    target = ROOT / "backend"
    target.mkdir(exist_ok=True)
    windows = sys.platform == "win32"
    if sys.platform not in ("win32", "darwin", "linux"):
        raise RuntimeError("Unsupported extractor build platform.")
    if windows and platform.machine().lower() not in ("amd64", "x86_64"):
        raise RuntimeError("The Windows extractor requires x64.")
    source = ROOT / "vendor/shadps4plus"
    source_manifest = json.loads((source / "SOURCE.json").read_text(encoding="utf-8"))
    for name, hashes in source_manifest["files"].items():
        if hashlib.sha256((source / name).read_bytes()).hexdigest() != hashes["sha256"]:
            raise RuntimeError(f"Pinned extractor source changed: {name}")
    build = ROOT / ".work" / "native"
    configure = ["cmake", "-S", str(ROOT / "packaging/native"),
                 "-B", str(build), "-DCMAKE_BUILD_TYPE=Release"]
    if windows:
        configure += ["-G", "Ninja"]
    subprocess.run(configure, check=True)
    subprocess.run(["cmake", "--build", str(build), "--parallel", "3"], check=True)
    name = "pkg_extractor.exe" if windows else "pkg_extractor"
    executable = target / name
    shutil.copy2(build / name, executable)
    patch = ROOT / "packaging/native/np-entry-padding.patch"
    record = {
        "release": RELEASE,
        "source": "vendor/shadps4plus",
        "commit": source_manifest["commit"],
        "patch": patch.relative_to(ROOT).as_posix(),
        "patch_sha256": hashlib.sha256(patch.read_bytes()).hexdigest(),
        "built_for": f"{sys.platform}-{platform.machine()}",
    }
    if sys.platform == "win32":
        from windows_manifest import enable_utf8
        manifest = ROOT / "packaging" / "backend-windows.manifest"
        record["original_executable_sha256"] = enable_utf8(executable, manifest)
        record["manifest"] = "UTF-8 process code page and long-path awareness"
        record["manifest_sha256"] = hashlib.sha256(manifest.read_bytes()).hexdigest()
    with executable.open("rb") as stream:
        record["executable_sha256"] = hashlib.file_digest(stream, "sha256").hexdigest()
    (target / "provenance.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print("EXTRACTOR_PREPARED")


if __name__ == "__main__":
    main()
