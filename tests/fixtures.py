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


def write_payload_pkg(directory: Path, *, compressed=True, corruption=None, size=70001,
                      filename="payload.bin", nested=False, malformed=None, category="gd", flags=0):
    import hmac
    import zlib
    from cryptography.hazmat.primitives.asymmetric import padding, rsa
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

    keys = (Path(__file__).resolve().parents[1] / "vendor/shadps4plus/src/core/crypto/keys.h").read_text()

    def encrypt_key(name, value):
        keyset = keys.split(f"class {name} {{", 1)[1]
        modulus = re.search(r"Modulus\[\]\s*=\s*\{([^}]+)\}", keyset)[1]
        modulus = int.from_bytes(bytes(int(v, 16) for v in re.findall(r"0x[0-9a-fA-F]+", modulus)), "big")
        return rsa.RSAPublicNumbers(65537, modulus).public_key().encrypt(value, padding.PKCS1v15())

    def encrypt_cbc(data, key):
        cipher = Cipher(algorithms.AES(key[16:]), modes.CBC(key[:16])).encryptor()
        return cipher.update(data) + cipher.finalize()

    plaintext = bytes((i * 37 + i // 113) % 256 for i in range(size))
    payload_blocks = [plaintext[i:i + 0x10000].ljust(0x10000, b"\0")
                      for i in range(0, size, 0x10000)]
    metadata = [bytearray(0x10000) for _ in range(5 if nested else 4)]
    file_inode = 3 if nested else 2
    struct.pack_into("<I", metadata[0], 0x30, file_inode + 1)
    for index in range(file_inode + 1):
        struct.pack_into("<H", metadata[1], index * 0xA8, 0x8000 if index == file_inode else 0x4000)
    struct.pack_into("<q", metadata[1], file_inode * 0xA8 + 8, size)
    struct.pack_into("<II", metadata[1], file_inode * 0xA8 + 96, len(payload_blocks), len(metadata))

    def dirent(block, offset, inode, kind, name, length=None):
        encoded = name.encode()
        length = length or ((16 + len(encoded) + 7) & ~7)
        struct.pack_into("<4i", block, offset, inode, kind, len(encoded), length)
        block[offset + 16:offset + 16 + len(encoded)] = encoded

    dirent(metadata[2], 0, 1, 3, "flat_path_table", 0x30)
    for index in range(3, len(metadata)):
        dirent(metadata[index], 0, index - 2, 4, ".", 0x18)
        dirent(metadata[index], 0x18, 1, 5, "..", 0x18)
    if nested:
        dirent(metadata[3], 0x30, 2, 3, "Unterordner_日本")
    dirent(metadata[-1], 0x30, file_inode, 2, filename)
    if malformed in {"negative_length", "oversized_length", "zero_record", "oversized_record", "inode", "type"}:
        offset, value = {
            "negative_length": (8, -1), "oversized_length": (8, 513),
            "zero_record": (12, 0), "oversized_record": (12, 0x10000),
            "inode": (0, 999), "type": (4, 6),
        }[malformed]
        struct.pack_into("<i", metadata[-1], 0x30 + offset, value)
    elif malformed == "current_inode":
        struct.pack_into("<i", metadata[-1], 0, file_inode)
    elif malformed == "parent_name":
        dirent(metadata[-1], 0x18, 1, 5, "parent", 0x18)
    blocks = [zlib.compress(block) for block in metadata]
    for index, block in enumerate(payload_blocks):
        encoded = zlib.compress(block) if compressed else block
        if index == 0:
            if corruption == "checksum":
                encoded = encoded[:-1] + bytes([encoded[-1] ^ 1])
            elif corruption == "truncated":
                encoded = encoded[:-2]
            elif corruption == "short":
                encoded = zlib.compress(block[:-1])
        blocks.append(encoded)
    if corruption == "metadata":
        blocks[0] = b"invalid zlib data"
    offsets = [0x100]
    for block in blocks:
        offsets.append(offsets[-1] + len(block))
    pfsc = bytearray(offsets[-1])
    struct.pack_into("<4i2qQq", pfsc, 0, 0x43534650, 0, 0, 0x10000, 0x10000,
                     0x40, 0x100, len(blocks) * 0x10000)
    struct.pack_into(f"<{len(offsets)}Q", pfsc, 0x40, *offsets)
    for offset, block in zip(offsets, blocks):
        pfsc[offset:offset + len(block)] = block
    image = bytearray(0x60000)
    image[0x20000:0x20000 + len(pfsc)] = pfsc
    derived_key = bytes(range(32))
    image_key = bytes(range(32, 64))
    seed = bytes(range(16))
    data_tweak_key = hmac.digest(image_key, struct.pack("<I", 1) + seed, "sha256")
    xts_key = data_tweak_key[16:] + data_tweak_key[:16]
    encrypted_image = bytearray()
    for offset in range(0, len(image), 0x1000):
        cipher = Cipher(algorithms.AES(xts_key), modes.XTS(struct.pack("<Q", offset // 0x1000) + bytes(8))).encryptor()
        encrypted_image += cipher.update(image[offset:offset + 0x1000]) + cipher.finalize()
    encrypted_image[0x370:0x380] = seed
    entry_keys = bytearray(2048)
    entry_keys[1024:1280] = encrypt_key("PkgDerivedKey3Keyset", derived_key)
    sfo = make_sfo(category)
    data_offset = 0x1060
    sfo_offset = data_offset + len(entry_keys) + 256
    pfs_offset = (sfo_offset + len(sfo) + 0xFFF) & ~0xFFF
    entries = struct.pack(">6I8x", 0x10, 0, 0, 0, data_offset, len(entry_keys))
    image_entry = struct.pack(">6I8x", 0x20, 0, 0, 0, data_offset + len(entry_keys), 256)
    entries += image_entry + struct.pack(">6I8x", 0x1000, 0, 0, 0, sfo_offset, len(sfo))
    encrypted_key = encrypt_cbc(encrypt_key("FakeKeyset", image_key), hashlib.sha256(image_entry + derived_key).digest())
    header = bytearray(0x1000)
    header[:4] = b"\x7fCNT"
    struct.pack_into(">II", header, 0x10, 3, 0)
    struct.pack_into(">I", header, 0x18, 0x1000)
    content_id = b"UP0001-CUSA00001_00-EXAMPLECONTENT01"
    header[0x40:0x40 + len(content_id)] = content_id
    struct.pack_into(">I", header, 0x78, flags)
    struct.pack_into(">QQ", header, 0x410, pfs_offset, len(image))
    struct.pack_into(">Q", header, 0x430, pfs_offset + len(image))
    struct.pack_into(">I", header, 0x43C, len(image) // 2)
    contents = header + entries + entry_keys + encrypted_key + sfo
    contents += bytes(pfs_offset - len(contents)) + encrypted_image
    path = directory / "payload.pkg"
    path.write_bytes(contents)
    return path, plaintext
