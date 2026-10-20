from pathlib import Path
import sys

import pytest

from pkg_extractor_ui.backend import ExtractionError, extract_package
from tests.fixtures import write_encrypted_np_pkg, write_license_pkg, write_pkg

ROOT = Path(__file__).resolve().parents[1]
ENGINE = ROOT / "backend" / ("pkg_extractor.exe" if sys.platform == "win32" else "pkg_extractor")
pytestmark = pytest.mark.skipif(not ENGINE.is_file(), reason="Run scripts/fetch_backend.py first")


@pytest.mark.parametrize(("name", "category", "flags", "relative"), [
    ("ordinary.pkg", "gd", 0, "CUSA00001"),
    ("Grüsse.pkg", "gp", 0x100000, "CUSA00001-patch"),
    ("日本語.pkg", "ac", 0, "CUSA00001/EXAMPLECONTENT01"),
    ("emoji-😀.pkg", "gd", 0, "CUSA00001"),
    ("cannot open.pkg", "gd", 0, "CUSA00001"),
])
def test_actual_engine_metadata_only_package(tmp_path, name, category, flags, relative):
    source = write_pkg(tmp_path, name, category, flags)
    before = source.read_bytes()
    messages = []
    result = extract_package(source, tmp_path / "結果", log=messages.append)
    assert result.name == relative.split("/")[0]
    inside = Path(*Path(relative).parts[1:])
    assert (result / inside / "sce_sys" / "param.sfo").is_file()
    assert sorted(path.name for path in result.iterdir()) == (["EXAMPLECONTENT01"] if category == "ac" else ["sce_sys"])
    assert source.read_bytes() == before
    assert all("\ufffd" not in line for line in messages)


def test_similar_unicode_names_use_selected_input(tmp_path):
    write_pkg(tmp_path, "width-A.pkg", extra_data=b"ASCII_FILE")
    source = write_pkg(tmp_path, "width-Ａ.pkg", extra_data=b"WIDE__FILE")
    result = extract_package(source, tmp_path / "out")
    assert (result / "sce_sys" / str(0x777777)).read_bytes() == b"WIDE__FILE"


def test_each_package_gets_its_own_export_folder(tmp_path):
    first = write_pkg(tmp_path, "Game.pkg", extra_data=b"FIRST_PACKAGE")
    second = write_pkg(tmp_path, "Another game.pkg", extra_data=b"SECOND_PACKAGE")
    export = tmp_path / "export"
    results = [extract_package(source, export) for source in (first, second, first)]
    assert [path.name for path in results] == ["CUSA00001", "CUSA00001 (2)", "CUSA00001 (3)"]
    assert all(path.parent == export for path in results)
    for folder, expected in zip(results, (b"FIRST_PACKAGE", b"SECOND_PACKAGE", b"FIRST_PACKAGE")):
        assert (folder / "sce_sys" / str(0x777777)).read_bytes() == expected
    assert sorted(export.iterdir()) == sorted(results)


def test_actual_engine_license_only_dlc_with_zero_declared_size(tmp_path):
    source = write_license_pkg(tmp_path)
    before = source.read_bytes()
    result = extract_package(source, tmp_path / "export")
    assert result.name == "CUSA00001"
    assert (result / "EXAMPLECONTENT01/sce_sys/param.sfo").is_file()
    assert source.read_bytes() == before


@pytest.mark.parametrize("length", [1, 15, 16, 17, 31, 32, 532])
@pytest.mark.parametrize(("entry_id", "name"), [
    (0x400, "license.dat"),
    (0x401, "license.info"),
    (0x402, "nptitle.dat"),
    (0x403, "npbind.dat"),
])
def test_encrypted_metadata_matches_known_plaintext(tmp_path, length, entry_id, name):
    plaintext = bytes((index * 37 + 11) % 256 for index in range(length))
    source = write_encrypted_np_pkg(tmp_path, plaintext, entry_id)
    before = source.read_bytes()
    outputs = [extract_package(source, tmp_path / "export") for _ in range(2)]
    for output in outputs:
        assert (output / "sce_sys" / name).read_bytes() == plaintext
    assert source.read_bytes() == before


def test_truncated_encrypted_metadata_is_rejected(tmp_path):
    source = write_encrypted_np_pkg(tmp_path, b"known final bytes!", truncate_padding=True)
    before = source.read_bytes()
    with pytest.raises(ExtractionError):
        extract_package(source, tmp_path / "export")
    assert list((tmp_path / "export").iterdir()) == []
    assert source.read_bytes() == before
