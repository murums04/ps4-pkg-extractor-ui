import re
import struct
from dataclasses import dataclass
from pathlib import Path


class PackageError(ValueError):
    pass


@dataclass(frozen=True)
class PackageInfo:
    source: Path
    title_id: str
    title: str
    kind: str
    content_id: str
    output_relative: Path
    file_size: int
    pfs_size: int
    sfo: bytes


def checked_range(offset: int, length: int, limit: int, description: str):
    if offset < 0 or length < 0 or offset > limit or length > limit - offset:
        raise PackageError(f"{description} extends beyond the package.")


def read_sfo(data: bytes) -> dict[str, str]:
    if len(data) < 20 or data[:4] != b"\0PSF":
        raise PackageError("The package has no readable param.sfo.")
    version, keys, values, count = struct.unpack_from("<4I", data, 4)
    if version not in (0x100, 0x101) or count > 4096:
        raise PackageError("Unsupported param.sfo layout.")
    checked_range(20, count * 16, len(data), "SFO entry table")
    if not 20 + count * 16 <= keys <= values <= len(data):
        raise PackageError("Invalid param.sfo table offsets.")
    result = {}
    for index in range(count):
        key_offset, kind, length, capacity, value_offset = struct.unpack_from(
            "<HHIII", data, 20 + index * 16)
        key_start = keys + key_offset
        if not keys <= key_start < values:
            raise PackageError("Invalid param.sfo key offset.")
        key_end = data.find(b"\0", key_start, values)
        if key_end < 0 or length > capacity:
            raise PackageError("Invalid param.sfo entry.")
        checked_range(values + value_offset, capacity, len(data), "SFO value")
        try:
            key = data[key_start:key_end].decode("utf-8")
            if key in result:
                raise PackageError("Duplicate param.sfo key.")
            if kind == 0x0204:
                value = data[values + value_offset:values + value_offset + length]
                if not value.endswith(b"\0"):
                    raise PackageError("Unterminated param.sfo string.")
                result[key] = value[:-1].decode("utf-8")
        except UnicodeDecodeError as error:
            raise PackageError("Invalid text in param.sfo.") from error
    return result


def read_package(path: Path) -> PackageInfo:
    try:
        source = Path(path).resolve(strict=True)
        if not source.is_file():
            raise PackageError("Choose a PKG file.")
        file_size = source.stat().st_size
        with source.open("rb") as stream:
            header = stream.read(0x1000)
            if len(header) != 0x1000 or header[:4] != b"\x7fCNT":
                raise PackageError("This is not a PS4 PKG file.")
            declared_size = struct.unpack_from(">Q", header, 0x430)[0]
            count = struct.unpack_from(">I", header, 0x10)[0]
            table_offset = struct.unpack_from(">I", header, 0x18)[0]
            if not 0 < count <= 100_000 or table_offset < 0x1000:
                raise PackageError("Invalid PKG entry table.")
            checked_range(table_offset, count * 32, file_size, "PKG entry table")
            content_offset, content_size = struct.unpack_from(">QQ", header, 0x30)
            checked_range(content_offset, content_size, file_size, "PKG content")
            pfs_offset, pfs_size = struct.unpack_from(">QQ", header, 0x410)
            checked_range(pfs_offset, pfs_size, file_size, "PFS image")
            checked_range(pfs_offset, 0x380, file_size, "PFS seed")
            content_type = struct.unpack_from(">I", header, 0x74)[0]
            pfs_cache_size = struct.unpack_from(">I", header, 0x43C)[0]
            license_only = content_type == 0x1C and not any(
                (content_offset, content_size, pfs_offset, pfs_size, pfs_cache_size))
            # License-only DLC may leave the total size field unset.
            if declared_size != file_size and not (declared_size == 0 and license_only):
                raise PackageError("The PKG size does not match its header. The file may be incomplete.")
            content_id = header[0x40:0x64].rstrip(b"\0").decode("ascii", errors="strict")
            match = re.fullmatch(r"[A-Z]{2}\d{4}-([A-Z]{4}\d{5})_\d{2}-([A-Za-z0-9_]{1,16})", content_id)
            if not match:
                raise PackageError("Invalid package content ID.")
            title_id = match[1]
            stream.seek(table_offset)
            table = stream.read(count * 32)
            sfo_entry = None
            for index in range(count):
                entry_id, _, _, _, offset, size = struct.unpack_from(">6I", table, index * 32)
                checked_range(offset, size, file_size, "PKG entry")
                if entry_id == 0x1000:
                    if sfo_entry is not None or size > 4 * 1024 * 1024:
                        raise PackageError("Invalid param.sfo entry.")
                    sfo_entry = (offset, size)
            if sfo_entry is None:
                raise PackageError("The package contains no param.sfo.")
            stream.seek(sfo_entry[0])
            sfo = stream.read(sfo_entry[1])
        fields = read_sfo(sfo)
        if fields.get("TITLE_ID", title_id) != title_id:
            raise PackageError("The package and param.sfo title IDs disagree.")
        category = fields.get("CATEGORY")
        if not category:
            raise PackageError("The package has no content category.")
        flags = struct.unpack_from(">I", header, 0x78)[0]
        if flags & 0x61300000:
            kind = "Update"
            relative = Path(title_id + "-patch")
        elif category == "ac":
            kind = "DLC"
            if fields.get("CONTENT_ID") != content_id:
                raise PackageError("The DLC content IDs disagree.")
            relative = Path(title_id) / match[2]
        else:
            kind = "Game"
            relative = Path(title_id)
        if declared_size == 0 and kind != "DLC":
            raise PackageError("A package with no declared size must be a license-only DLC.")
        return PackageInfo(source, title_id, fields.get("TITLE", title_id), kind,
                           content_id, relative, file_size, pfs_size, sfo)
    except (OSError, UnicodeError, struct.error) as error:
        raise PackageError(f"Could not read the PKG: {error}") from error
