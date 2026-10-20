import json
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    destination = ROOT / "licenses" / "macOS-runtime"
    destination.mkdir(parents=True, exist_ok=True)
    for formula in ("cryptopp", "zlib"):
        metadata = subprocess.check_output(["brew", "info", "--json=v2", formula], text=True)
        (destination / f"{formula}.json").write_text(metadata, encoding="utf-8")
        record = json.loads(metadata)["formulae"][0]
        prefix = Path(subprocess.check_output(["brew", "--prefix", formula], text=True).strip())
        licenses = [path for path in prefix.rglob("*") if path.is_file()
                    and path.name.lower() in ("license", "license.txt", "copying", "copyright")]
        if not licenses or not record.get("installed"):
            raise RuntimeError(f"Missing installed formula or license: {formula}")
        for index, source in enumerate(licenses):
            shutil.copy2(source, destination / f"{formula}-{index}-{source.name}")
    print("MACOS_RUNTIME_NOTICES_COLLECTED")


if __name__ == "__main__":
    main()
