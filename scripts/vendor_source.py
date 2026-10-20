import hashlib
import json
import posixpath
import re
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMIT = "771a8d58aff540448c7cbace7c40a66a5daf010d"
REPOSITORY = "AzaharPlus/shadPS4Plus"
SOURCES = [
    "extractor/main.cpp", "src/core/loader.cpp", "src/core/file_format/pkg.cpp",
    "src/core/file_format/psf.cpp", "src/core/file_format/pkg_type.cpp",
    "src/core/crypto/crypto.cpp", "src/common/io_file.cpp", "src/common/assert.cpp",
    "src/common/error.cpp", "src/common/path_util.cpp", "src/common/string_util.cpp",
    "LICENSE", "LICENSES/GPL-2.0-or-later.txt",
]


def fetch(url):
    request = urllib.request.Request(url, headers={"User-Agent": "murums-pkg-ui-build"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main():
    tree = json.loads(fetch(f"https://api.github.com/repos/{REPOSITORY}/git/trees/{COMMIT}?recursive=1"))
    if tree.get("truncated"):
        raise RuntimeError("The source tree is incomplete.")
    blobs = {entry["path"]: entry["sha"] for entry in tree["tree"] if entry["type"] == "blob"}
    destination = ROOT / "vendor" / "shadps4plus"
    pending = list(SOURCES)
    manifest = {}
    while pending:
        name = pending.pop(0)
        if name in manifest:
            continue
        data = fetch(f"https://raw.githubusercontent.com/{REPOSITORY}/{COMMIT}/{name}")
        digest = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if digest != blobs[name]:
            raise RuntimeError(f"Source identity mismatch: {name}")
        local = destination / name
        local.parent.mkdir(parents=True, exist_ok=True)
        local.write_bytes(data)
        manifest[name] = {"git_blob": digest, "sha256": hashlib.sha256(data).hexdigest()}
        text = data.decode("utf-8", errors="replace")
        for include in re.findall(r'^\s*#include\s*["<]([^">]+)[">]', text, re.M):
            for candidate in (posixpath.normpath(posixpath.join(posixpath.dirname(name), include)),
                              "src/" + include, "externals/" + include):
                if candidate in blobs:
                    pending.append(candidate)
                    break
    (destination / "SOURCE.json").write_text(json.dumps({
        "repository": f"https://github.com/{REPOSITORY}", "commit": COMMIT,
        "release": "PKG_EXTRACTOR_1_1", "files": dict(sorted(manifest.items())),
    }, indent=2) + "\n", encoding="utf-8")
    print(f"VENDORED_SOURCE_VERIFIED: {len(manifest)} files")


if __name__ == "__main__":
    main()
