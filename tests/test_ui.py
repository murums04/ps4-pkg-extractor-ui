import importlib
import os
import time

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
