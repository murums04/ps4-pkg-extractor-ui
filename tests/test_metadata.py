import importlib
import struct

import pytest

from tests.fixtures import write_license_pkg, write_pkg


def implementation():
    try:
        return importlib.import_module("pkg_extractor_ui.metadata")
    except ModuleNotFoundError:
        pytest.fail("The package metadata reader is not implemented")


@pytest.mark.parametrize(("category", "flags", "kind", "relative"), [
    ("gd", 0, "Game", "CUSA00001"),
    ("gp", 0x100000, "Update", "CUSA00001-patch"),
    ("ac", 0, "DLC", "CUSA00001/EXAMPLECONTENT01"),
])
def test_package_types(tmp_path, category, flags, kind, relative):
    metadata = implementation()
    info = metadata.read_package(write_pkg(tmp_path, category=category, flags=flags))
    assert info.title_id == "CUSA00001"
    assert info.title == "Example package"
    assert info.kind == kind
    assert info.output_relative.as_posix() == relative


@pytest.mark.parametrize(("offset", "format", "value"), [
    (0, ">I", 0),
    (0x10, ">I", 0xFFFFFFFF),
    (0x18, ">I", 0xFFFFFF00),
    (0x430, ">Q", 0xFFFFFFFF),
    (0x1010, ">I", 0xFFFFFF00),
    (0x1014, ">I", 0xFFFFFF00),
])
def test_rejects_invalid_header_and_ranges(tmp_path, offset, format, value):
    metadata = implementation()
    path = write_pkg(tmp_path)
    contents = bytearray(path.read_bytes())
    struct.pack_into(format, contents, offset, value)
    path.write_bytes(contents)
    with pytest.raises(metadata.PackageError):
        metadata.read_package(path)


def test_rejects_short_input(tmp_path):
    metadata = implementation()
    path = tmp_path / "short.pkg"
    path.write_bytes(b"\x7fCNT")
    with pytest.raises(metadata.PackageError):
        metadata.read_package(path)


def test_rejects_unsafe_title_id(tmp_path):
    metadata = implementation()
    path = write_pkg(tmp_path)
    contents = bytearray(path.read_bytes())
    contents[0x47:0x50] = b"../escape"
    path.write_bytes(contents)
    with pytest.raises(metadata.PackageError):
        metadata.read_package(path)


def test_handles_spaces_and_unicode_without_modifying_input(tmp_path):
    metadata = implementation()
    path = write_pkg(tmp_path, "Grüsse & test [1].pkg")
    before = path.read_bytes()
    info = metadata.read_package(path)
    assert info.source == path.resolve()
    assert path.read_bytes() == before


def test_rejects_corrupt_sfo_offsets(tmp_path):
    metadata = implementation()
    path = write_pkg(tmp_path)
    contents = bytearray(path.read_bytes())
    struct.pack_into("<I", contents, 0x1020 + 8, 0xFFFFFF00)
    path.write_bytes(contents)
    with pytest.raises(metadata.PackageError):
        metadata.read_package(path)


def test_reads_license_only_dlc_with_zero_declared_size(tmp_path):
    metadata = implementation()
    info = metadata.read_package(write_license_pkg(tmp_path))
    assert info.kind == "DLC"
    assert info.pfs_size == 0
    assert info.output_relative.as_posix() == "CUSA00001/EXAMPLECONTENT01"


@pytest.mark.parametrize(("offset", "format", "value"), [
    (0x74, ">I", 0x1B),
    (0x78, ">I", 0x100000),
    (0x30, ">Q", 0x1000),
    (0x38, ">Q", 1),
    (0x410, ">Q", 0x1000),
    (0x418, ">Q", 1),
    (0x43C, ">I", 0x10000),
    (0x430, ">Q", 1),
    (0x1014, ">I", 0xFFFFFF00),
])
def test_license_only_dlc_keeps_size_and_range_checks(tmp_path, offset, format, value):
    metadata = implementation()
    path = write_license_pkg(tmp_path)
    contents = bytearray(path.read_bytes())
    struct.pack_into(format, contents, offset, value)
    path.write_bytes(contents)
    with pytest.raises(metadata.PackageError):
        metadata.read_package(path)


def test_zero_declared_size_requires_dlc_metadata(tmp_path):
    metadata = implementation()
    with pytest.raises(metadata.PackageError):
        metadata.read_package(write_license_pkg(tmp_path, category="gd"))
