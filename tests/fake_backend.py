import pathlib
import struct
import sys
import time

mode, source, output = sys.argv[1:]
source = pathlib.Path(source)
output = pathlib.Path(output)
assert (pathlib.Path.cwd() / "user").is_dir()
if mode == "failure":
    print("Cannot extract PKG file : example failure", flush=True)
    print(f'THE END "{source}"', flush=True)
    sys.exit(0)
if mode == "crash":
    sys.exit(42)
data = source.read_bytes()
offset, size = struct.unpack_from(">II", data, 0x1010)
folder = output / "CUSA00001"
(folder / "sce_sys").mkdir(parents=True)
(folder / "sce_sys" / "param.sfo").write_bytes(data[offset:offset + size])
if mode == "wait":
    print("Extracting file 1 of 3", flush=True)
    time.sleep(60)
if mode == "incomplete":
    print("Extracting file 1 of 3", flush=True)
else:
    (folder / "example.txt").write_text("fixture payload", encoding="utf-8")
    print("Extracting file 1 of 1", flush=True)
print(f'THE END "{source}"', flush=True)
