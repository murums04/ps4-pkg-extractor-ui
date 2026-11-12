import importlib
import os
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from tests.fixtures import write_pkg
from tests.test_backend import command


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


def window(app, mode="success"):
    try:
        module = importlib.import_module("pkg_extractor_ui.window")
    except ModuleNotFoundError:
        pytest.fail("The PKG window is not implemented")
    return module.MainWindow(command=command(mode))


def settle(app, screen):
    deadline = time.monotonic() + 10
    while screen.worker is not None and time.monotonic() < deadline:
        app.processEvents()
        QTest.qWait(10)
    assert screen.worker is None


def test_queue_filters_duplicates_and_preserves_valid_input(tmp_path, app):
    screen = window(app)
    source = write_pkg(tmp_path)
    screen.add_files([source, source, tmp_path])
    assert len(screen.sources) == 1
    assert screen.table.rowCount() == 1
    assert screen.table.item(0, 1).text() == "Game"
    assert screen.extract_button.isEnabled()
    screen.close()


def test_failed_input_does_not_stop_next_job(tmp_path, app):
    screen = window(app)
    invalid = tmp_path / "broken.pkg"
    invalid.write_bytes(b"broken")
    source = write_pkg(tmp_path)
    screen.add_files([invalid, source])
    screen.output_edit.setText(str(tmp_path / "output"))
    screen.start_extraction()
    settle(app, screen)
    assert screen.results == {0: "Failed", 1: "Extracted"}
    assert screen.extract_button.isEnabled()
    assert "1 failed" in screen.status_label.text()
    screen.close()


@pytest.mark.parametrize("output_name,use_home", [
    ("output", False), (" output", False), ("output", True),
    pytest.param("output ", False, marks=pytest.mark.skipif(
        os.name == "nt", reason="Windows trims trailing spaces in directory names")),
    pytest.param("output ", True, marks=pytest.mark.skipif(
        os.name == "nt", reason="Windows trims trailing spaces in directory names")),
])
def test_output_path_preserves_selected_folder(tmp_path, app, monkeypatch, output_name, use_home):
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QFileDialog

    screen = window(app)
    destination = tmp_path / output_name
    destination.mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *args: str(destination))
    opened = []
    monkeypatch.setattr(QDesktopServices, "openUrl", lambda url: opened.append(url.toLocalFile()) or True)
    screen.add_files([write_pkg(tmp_path)])
    screen.choose_output()
    if use_home:
        screen.output_edit.setText(f"~/{output_name}")
    assert screen.open_button.isEnabled()
    screen.start_extraction()
    settle(app, screen)
    assert screen.results == {0: "Extracted"}
    assert (destination / "CUSA00001").is_dir()
    if output_name != output_name.strip():
        assert not (tmp_path / output_name.strip()).exists()
    screen.open_output()
    assert [Path(path) for path in opened] == [destination.resolve()]
    screen.close()


def test_unresolvable_home_disables_extraction(tmp_path, app, monkeypatch):
    screen = window(app)
    screen.add_files([write_pkg(tmp_path)])

    def missing_home(path):
        raise RuntimeError("Could not determine home directory")

    monkeypatch.setattr(Path, "expanduser", missing_home)
    screen.output_edit.setText("~/output")
    assert not screen.extract_button.isEnabled()
    assert not screen.open_button.isEnabled()
    screen.close()


def test_relative_output_is_rejected(tmp_path, app):
    screen = window(app)
    screen.add_files([write_pkg(tmp_path)])
    screen.output_edit.setText("output")
    assert not screen.extract_button.isEnabled()
    assert "full folder path" in screen.output_hint.text()
    screen.close()


def test_adding_files_extracts_only_new_ones(tmp_path, app):
    screen = window(app)
    output = tmp_path / "output"
    screen.add_files([write_pkg(tmp_path)])
    screen.output_edit.setText(str(output))
    screen.start_extraction()
    settle(app, screen)
    added = tmp_path / "added.pkg"
    added.write_bytes(screen.sources[0].read_bytes())
    screen.add_files([added])
    screen.start_extraction()
    settle(app, screen)
    assert sorted(path.name for path in output.iterdir()) == ["CUSA00001", "CUSA00001 (2)"]
    assert screen.results == {1: "Extracted"}
    assert screen.status_label.text() == "1 extracted"
    assert screen.extract_button.text() == "Extract again"
    screen.close()


def test_button_label_follows_unfinished_packages(tmp_path, app):
    screen = window(app)
    source = write_pkg(tmp_path)
    invalid = tmp_path / "broken.pkg"
    invalid.write_bytes(b"broken")
    screen.add_files([source, invalid])
    screen.output_edit.setText(str(tmp_path / "output"))
    assert screen.extract_button.text() == "Extract PKG"
    screen.start_extraction()
    settle(app, screen)
    assert screen.extract_button.text() == "Extract remaining"
    screen.table.selectRow(1)
    screen.remove_selected()
    assert screen.extract_button.text() == "Extract again"
    screen.table.selectRow(0)
    screen.remove_selected()
    screen.add_files([source])
    assert screen.extract_button.text() == "Extract PKG"
    screen.close()


def test_dropped_folder_adds_packages(tmp_path, app):
    screen = window(app)
    source = write_pkg(tmp_path)
    (tmp_path / "notes.txt").write_text("skip")
    screen.add_files([tmp_path])
    assert screen.sources == [source.resolve()]
    screen.close()


def test_close_cancels_work_and_waits_for_cleanup(tmp_path, app):
    screen = window(app, "wait")
    screen.show()
    screen.add_files([write_pkg(tmp_path)])
    screen.output_edit.setText(str(tmp_path / "output"))
    screen.start_extraction()
    deadline = time.monotonic() + 5
    while not list((tmp_path / "output").glob(".pkg-*")) and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.01)
    assert list((tmp_path / "output").glob(".pkg-*"))
    screen.close()
    settle(app, screen)
    assert not screen.isVisible()
    assert list((tmp_path / "output").iterdir()) == []


def test_retry_and_clear_reset_current_results(tmp_path, app):
    screen = window(app)
    screen.add_files([write_pkg(tmp_path)])
    screen.output_edit.setText(str(tmp_path / "output"))
    screen.start_extraction()
    settle(app, screen)
    screen.start_extraction()
    settle(app, screen)
    assert len(list((tmp_path / "output").iterdir())) == 2
    screen.clear_files()
    assert not screen.results
    assert screen.table.rowCount() == 0
    assert not screen.extract_button.isEnabled()
    screen.close()
