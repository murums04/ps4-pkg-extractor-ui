import importlib
import sys
import threading
from pathlib import Path

import pytest

from tests.fixtures import write_pkg


def implementation():
    try:
        return importlib.import_module("pkg_extractor_ui.backend")
    except ModuleNotFoundError:
        pytest.fail("The extractor process runner is not implemented")


def command(mode):
    return [sys.executable, str(Path(__file__).with_name("fake_backend.py")), mode]


def test_extracts_in_separate_folder_and_preserves_existing_result(tmp_path):
    backend = implementation()
    source = write_pkg(tmp_path, "a & b.pkg")
    original = source.read_bytes()
    first = backend.extract_package(source, tmp_path / "out", command("success"))
    second = backend.extract_package(source, tmp_path / "out", command("success"))
    assert first != second
    assert first.name == "CUSA00001" and second.name == "CUSA00001 (2)"
    assert (first / "example.txt").read_text() == "fixture payload"
    assert (second / "example.txt").is_file()
    assert source.read_bytes() == original
    assert not list((tmp_path / "out").glob(".pkg-*"))


@pytest.mark.parametrize("mode", ["failure", "crash", "incomplete"])
def test_failed_process_never_publishes_output(tmp_path, mode):
    backend = implementation()
    source = write_pkg(tmp_path)
    with pytest.raises(backend.ExtractionError):
        backend.extract_package(source, tmp_path / "out", command(mode))
    assert list((tmp_path / "out").iterdir()) == []


def test_cancel_stops_child_and_removes_partial_output(tmp_path):
    backend = implementation()
    source = write_pkg(tmp_path)
    cancel = threading.Event()
    def on_progress(current, total):
        cancel.set()
    with pytest.raises(backend.ExtractionCancelled):
        backend.extract_package(source, tmp_path / "out", command("wait"), cancel, on_progress)
    assert list((tmp_path / "out").iterdir()) == []


def test_missing_executable_has_useful_error(tmp_path):
    backend = implementation()
    with pytest.raises(backend.ExtractionError, match="start|found|extractor"):
        backend.extract_package(write_pkg(tmp_path), tmp_path / "out", [str(tmp_path / "absent")])


@pytest.mark.parametrize("name", ["cannot open.pkg", "failed to copy.pkg", "Extracting file 1 of 3.pkg"])
def test_filename_text_is_not_a_backend_record(tmp_path, name):
    backend = implementation()
    output = backend.extract_package(write_pkg(tmp_path, name), tmp_path / "out", command("success"))
    assert (output / "example.txt").is_file()
