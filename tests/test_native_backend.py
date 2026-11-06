from pathlib import Path
import sys

import pytest

from pkg_extractor_ui.backend import ExtractionError, extract_package
from tests.fixtures import write_encrypted_np_pkg, write_license_pkg, write_payload_pkg, write_pkg

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


@pytest.mark.parametrize(("compressed", "size"), [(False, 70001), (True, 70001), (True, 0)])
def test_actual_engine_payload_matches_plaintext(tmp_path, compressed, size):
    source, plaintext = write_payload_pkg(tmp_path, compressed=compressed, size=size)
    before = source.read_bytes()
    result = extract_package(source, tmp_path / "export")
    assert (result / "payload.bin").read_bytes() == plaintext
    assert source.read_bytes() == before


@pytest.mark.parametrize("corruption", ["checksum", "truncated", "short", "metadata"])
def test_corrupt_payload_is_rejected_and_removed(tmp_path, corruption):
    source, _ = write_payload_pkg(tmp_path, corruption=corruption)
    before = source.read_bytes()
    messages = []
    with pytest.raises(ExtractionError, match="Failed to decompress PFS"):
        extract_package(source, tmp_path / "export", log=messages.append)
    assert not any(line.startswith("THE END ") for line in messages)
    assert list((tmp_path / "export").iterdir()) == []
    assert source.read_bytes() == before


def test_payload_output_open_failure_is_rejected(tmp_path, monkeypatch):
    from pkg_extractor_ui import backend

    source, _ = write_payload_pkg(tmp_path)
    original_run = backend.run_extractor

    def obstruct_output(command, source, staging, *args, **kwargs):
        (staging / "CUSA00001/payload.bin").mkdir(parents=True)
        return original_run(command, source, staging, *args, **kwargs)

    monkeypatch.setattr(backend, "run_extractor", obstruct_output)
    with pytest.raises(ExtractionError, match="Failed to open PFS output file"):
        extract_package(source, tmp_path / "export")
    assert list((tmp_path / "export").iterdir()) == []


@pytest.mark.skipif(sys.platform == "win32", reason="Uses POSIX file-size limits")
@pytest.mark.parametrize(("size", "limit", "message"), [
    (70001, 40000, "Failed to write complete PFS output file"),
    (3001, 3000, "Failed to flush PFS output file"),
])
def test_payload_write_failure_is_rejected(tmp_path, size, limit, message):
    source, _ = write_payload_pkg(tmp_path, size=size)
    command = [sys.executable, "-c", (
        "import os, resource, signal, sys; "
        "signal.signal(signal.SIGXFSZ, signal.SIG_IGN); "
        f"resource.setrlimit(resource.RLIMIT_FSIZE, ({limit}, {limit})); "
        "os.execv(sys.argv[1], sys.argv[1:])"
    ), str(ENGINE)]
    with pytest.raises(ExtractionError, match=message):
        extract_package(source, tmp_path / "export", command=command)
    assert list((tmp_path / "export").iterdir()) == []


@pytest.mark.parametrize("failure", ["corrupt", "output"])
def test_native_payload_failure_exits_without_completion(tmp_path, failure):
    import subprocess

    source, _ = write_payload_pkg(tmp_path, corruption="checksum" if failure == "corrupt" else None)
    output = tmp_path / "export"
    if failure == "output":
        (output / "CUSA00001/payload.bin").mkdir(parents=True)
    (tmp_path / "user").mkdir()
    result = subprocess.run([str(ENGINE), str(source), str(output)], cwd=tmp_path,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 1
    assert "Cannot extract PKG file :" in result.stdout
    assert "THE END " not in result.stdout


@pytest.mark.parametrize(("category", "flags", "relative"), [
    ("gd", 0, ""), ("gp", 0x100000, ""), ("ac", 0, "EXAMPLECONTENT01"),
])
def test_nested_unicode_payload_and_directory_controls(tmp_path, category, flags, relative):
    source, plaintext = write_payload_pkg(tmp_path, nested=True, filename="Grüsse_日本😀.bin",
                                          category=category, flags=flags)
    result = extract_package(source, tmp_path / "export")
    assert (result / relative / "Unterordner_日本/Grüsse_日本😀.bin").read_bytes() == plaintext
    assert result.name == ("CUSA00001-patch" if flags else "CUSA00001")


@pytest.mark.parametrize("name", [
    "", ".", "..", "../blocked.bin", "folder/blocked.bin", "folder\\blocked.bin",
    "payload:stream", "bad\0name", "name.", "name ", "CON", "NUL.txt", "COM¹.dat",
])
def test_unsafe_payload_name_is_rejected_before_path_use(tmp_path, name):
    source, _ = write_payload_pkg(tmp_path, filename=name)
    with pytest.raises(ExtractionError, match="Invalid PFS"):
        extract_package(source, tmp_path / "export")
    assert list((tmp_path / "export").iterdir()) == []
    assert not (tmp_path / "blocked.bin").exists()


def test_absolute_payload_name_is_rejected_inside_owned_scratch(tmp_path):
    owned_target = tmp_path / "owned-absolute.bin"
    source, _ = write_payload_pkg(tmp_path, filename=str(owned_target))
    with pytest.raises(ExtractionError, match="Invalid PFS"):
        extract_package(source, tmp_path / "export")
    assert not owned_target.exists()
    assert list((tmp_path / "export").iterdir()) == []


@pytest.mark.parametrize("malformed", [
    "negative_length", "oversized_length", "zero_record", "oversized_record",
    "inode", "type", "current_inode", "parent_name",
])
def test_malformed_directory_record_is_rejected(tmp_path, malformed):
    source, _ = write_payload_pkg(tmp_path, malformed=malformed)
    with pytest.raises(ExtractionError, match="Invalid PFS|Incomplete PFS"):
        extract_package(source, tmp_path / "export")
    assert list((tmp_path / "export").iterdir()) == []


def test_native_invalid_directory_exits_without_completion(tmp_path):
    import subprocess

    source, _ = write_payload_pkg(tmp_path, malformed="negative_length")
    (tmp_path / "user").mkdir()
    result = subprocess.run([str(ENGINE), str(source), str(tmp_path / "export")], cwd=tmp_path,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 1
    assert "Invalid PFS directory record" in result.stdout
    assert "THE END " not in result.stdout


@pytest.mark.parametrize("invalid", ["title", "dlc"])
def test_native_rejects_unsafe_root_components(tmp_path, invalid):
    import subprocess

    source = write_pkg(tmp_path, category="ac" if invalid == "dlc" else "gd")
    contents = bytearray(source.read_bytes())
    if invalid == "title":
        contents[0x47:0x50] = b"BAD/TITLE"
    else:
        original = b"UP0001-CUSA00001_00-EXAMPLECONTENT01"
        replacement = b"UP0001-CUSA00001_00-" + b"bad/entitlement".ljust(16, b"x")
        contents = contents.replace(original, replacement)
    source.write_bytes(contents)
    (tmp_path / "user").mkdir()
    result = subprocess.run([str(ENGINE), str(source), str(tmp_path / "export")], cwd=tmp_path,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 1
    assert "Cannot extract PKG file : Invalid" in result.stdout
    assert "THE END " not in result.stdout
    assert not (tmp_path / "export").exists()


@pytest.mark.skipif(sys.platform == "win32", reason="Requires unprivileged POSIX symlinks")
def test_native_rejects_output_symlink_inside_owned_scratch(tmp_path):
    import subprocess

    source, _ = write_payload_pkg(tmp_path)
    owned_target = tmp_path / "owned-target"
    owned_target.mkdir()
    output = tmp_path / "export"
    (output / "CUSA00001").mkdir(parents=True)
    (output / "CUSA00001/sce_sys").symlink_to(owned_target, target_is_directory=True)
    (tmp_path / "user").mkdir()
    result = subprocess.run([str(ENGINE), str(source), str(output)], cwd=tmp_path,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 1
    assert "PKG output path escapes extraction root" in result.stdout
    assert "THE END " not in result.stdout
    assert list(owned_target.iterdir()) == []


@pytest.mark.skipif(sys.platform == "win32", reason="Requires unprivileged POSIX symlinks")
@pytest.mark.parametrize(("category", "alias"), [
    ("gd", "CUSA00001"), ("ac", "CUSA00001"),
    ("ac", "CUSA00001/EXAMPLECONTENT01"),
])
def test_native_rejects_package_derived_root_alias(tmp_path, category, alias):
    import subprocess

    source = write_pkg(tmp_path, category=category)
    owned_target = tmp_path / "owned-target"
    owned_target.mkdir()
    output = tmp_path / "export"
    link = output / alias
    link.parent.mkdir(parents=True)
    link.symlink_to(owned_target, target_is_directory=True)
    (tmp_path / "user").mkdir()
    result = subprocess.run([str(ENGINE), str(source), str(output)], cwd=tmp_path,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 1
    assert "Unsafe package output folder" in result.stdout
    assert "THE END " not in result.stdout
    assert list(owned_target.iterdir()) == []


@pytest.mark.skipif(sys.platform == "win32", reason="Requires unprivileged POSIX symlinks")
def test_native_allows_user_selected_output_base_alias(tmp_path):
    import subprocess

    source, plaintext = write_payload_pkg(tmp_path)
    owned_target = tmp_path / "owned-target"
    owned_target.mkdir()
    output = tmp_path / "selected-output"
    output.symlink_to(owned_target, target_is_directory=True)
    (tmp_path / "user").mkdir()
    result = subprocess.run([str(ENGINE), str(source), str(output)], cwd=tmp_path,
                            capture_output=True, text=True, timeout=15)
    assert result.returncode == 0
    assert "THE END " in result.stdout
    assert (owned_target / "CUSA00001/payload.bin").read_bytes() == plaintext
