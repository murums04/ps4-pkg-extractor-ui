import struct
import hashlib
import re
from pathlib import Path


def make_sfo(category="gd", title="Example package"):
    values = {
        "CATEGORY": category,
        "CONTENT_ID": "UP0001-CUSA00001_00-EXAMPLECONTENT01",
        "TITLE": title,
        "TITLE_ID": "CUSA00001",
    }
    keys = bytearray()
    data = bytearray()
    entries = bytearray()
    for key, value in values.items():
        encoded = value.encode("utf-8") + b"\0"
        entries += struct.pack("<HHIII", len(keys), 0x0204, len(encoded), len(encoded), len(data))
        keys += key.encode("ascii") + b"\0"
        data += encoded
    key_start = 20 + len(entries)
    return struct.pack("<4s4I", b"\0PSF", 0x101, key_start, key_start + len(keys), len(values)) + entries + keys + data


def write_pkg(directory: Path, name="example.pkg", category="gd", flags=0, extra_data=b""):
    sfo = make_sfo(category)
    header = bytearray(0x1000)
    header[:4] = b"\x7fCNT"
    count = 2 if extra_data else 1
    struct.pack_into(">I", header, 0x10, count)
    struct.pack_into(">I", header, 0x18, 0x1000)
    content_id = b"UP0001-CUSA00001_00-EXAMPLECONTENT01"
    header[0x40:0x40 + len(content_id)] = content_id
    struct.pack_into(">I", header, 0x78, flags)
    sfo_offset = 0x1000 + count * 32 + len(extra_data)
    pfs_offset = sfo_offset + len(sfo)
    struct.pack_into(">Q", header, 0x410, pfs_offset)
    struct.pack_into(">Q", header, 0x430, pfs_offset + 0x380)
    entry = b""
    if extra_data:
        entry += struct.pack(">6I8x", 0x777777, 0, 0, 0, 0x1040, len(extra_data))
    entry += struct.pack(">6I8x", 0x1000, 0, 0, 0, sfo_offset, len(sfo))
    path = directory / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + entry + extra_data + sfo + bytes(0x380))
    return path


def write_license_pkg(directory: Path, name="license.pkg", category="ac"):
    path = write_pkg(directory, name, category=category)
    contents = bytearray(path.read_bytes())
    struct.pack_into(">I", contents, 0x74, 0x1C)
    struct.pack_into(">Q", contents, 0x410, 0)
    struct.pack_into(">Q", contents, 0x430, 0)
    path.write_bytes(contents)
    return path


def write_encrypted_np_pkg(directory: Path, plaintext: bytes, entry_id=0x403,
                           truncate_padding=False):
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    keys = Path(__file__).resolve().parents[1] / "vendor/shadps4plus/src/core/crypto/keys.h"
    keyset = keys.read_text(encoding="utf-8").split("class PkgDerivedKey3Keyset {", 1)[1]
    modulus = re.search(r"Modulus\[\]\s*=\s*\{([^}]+)\}", keyset)[1]
    modulus = int.from_bytes(bytes(int(value, 16) for value in re.findall(r"0x[0-9a-fA-F]+", modulus)), "big")
    public_key = rsa.RSAPublicNumbers(65537, modulus).public_key()
    derived_key = bytes(range(32))
    entry_keys = bytearray(2048)
    entry_keys[256 + 3 * 256:256 + 4 * 256] = public_key.encrypt(derived_key, padding.PKCS1v15())

    sfo = make_sfo()
    header = bytearray(0x1000)
    header[:4] = b"\x7fCNT"
    struct.pack_into(">I", header, 0x10, 3)
    struct.pack_into(">I", header, 0x18, 0x1000)
    content_id = b"UP0001-CUSA00001_00-EXAMPLECONTENT01"
    header[0x40:0x40 + len(content_id)] = content_id
    keys_offset = 0x1060
    sfo_offset = keys_offset + len(entry_keys)
    np_offset = sfo_offset + len(sfo) + 0x380
    entries = struct.pack(">6I8x", 0x10, 0, 0, 0, keys_offset, len(entry_keys))
    entries += struct.pack(">6I8x", 0x1000, 0, 0, 0, sfo_offset, len(sfo))
    np_entry = struct.pack(">6I8x", entry_id, 0, 0x80000000, 0x30000000, np_offset, len(plaintext))
    iv_key = hashlib.sha256(np_entry + derived_key).digest()
    encryptor = Cipher(algorithms.AES(iv_key[16:]), modes.CBC(iv_key[:16])).encryptor()
    padded = plaintext + bytes((-len(plaintext)) % 16)
    ciphertext = encryptor.update(padded) + encryptor.finalize()
    if truncate_padding:
        ciphertext = ciphertext[:len(plaintext)]
    struct.pack_into(">Q", header, 0x430, np_offset + len(ciphertext))
    path = directory / "encrypted-metadata.pkg"
    path.write_bytes(header + entries + np_entry + entry_keys + sfo + bytes(0x380) + ciphertext)
    return path
