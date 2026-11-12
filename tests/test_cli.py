import json
import sys
from pathlib import Path

import pytest

from pkg_extractor_ui import __main__ as cli, backend
from tests.fixtures import write_pkg


@pytest.fixture
def invoke(monkeypatch):
    command = [sys.executable, str(Path(__file__).with_name("fake_backend.py")), "success"]
    monkeypatch.setattr(backend, "bundled_command", lambda: command)

    def run(source, output, report=None):
        arguments = ["pkg_extractor_ui", "--extract", str(source), "--output-dir", str(output)]
        if report is not None:
            arguments += ["--report", str(report)]
        monkeypatch.setattr(sys, "argv", arguments)
        return cli.main()

    return run


@pytest.mark.parametrize("with_report", [False, True])
def test_cli_extracts_and_reports_json(tmp_path, invoke, capsys, with_report):
    source = write_pkg(tmp_path)
    original = source.read_bytes()
    output = tmp_path / "out"
    report = tmp_path / "report.json" if with_report else None
    assert invoke(source, output, report) == 0
    captured = capsys.readouterr()
    result = output / "CUSA00001"
    assert (result / "example.txt").read_text() == "fixture payload"
    assert source.read_bytes() == original
    assert json.loads(report.read_text() if report else captured.out) == [
        {"source": str(source), "status": "extracted", "output": str(result)}
    ]
    assert captured.err == ""
    if report:
        assert captured.out == ""


@pytest.mark.parametrize("kind", ["existing", "symlink", "missing-parent", "file-parent"])
def test_invalid_report_prevents_extraction(tmp_path, invoke, capsys, kind):
    source = write_pkg(tmp_path)
    output = tmp_path / "out"
    report = tmp_path / "report.json"
    if kind == "existing":
        report.write_bytes(b"keep me")
    elif kind == "symlink":
        try:
            report.symlink_to(tmp_path / "missing.json")
        except OSError as error:
            pytest.skip(f"Symlinks unavailable: {error}")
    else:
        parent = tmp_path / "parent"
        if kind == "file-parent":
            parent.write_bytes(b"keep me")
        report = parent / "report.json"
    before = set(tmp_path.iterdir())
    with pytest.raises(SystemExit) as error:
        invoke(source, output, report)
    assert error.value.code == 1
    assert not output.exists()
    assert set(tmp_path.iterdir()) == before
    assert "report access failed" in capsys.readouterr().err
    if kind == "existing":
        assert report.read_bytes() == b"keep me"
    elif kind == "symlink":
        assert report.is_symlink() and not report.exists()


def test_report_path_is_reserved_before_publication(tmp_path, invoke):
    source = write_pkg(tmp_path)
    output = tmp_path / "out"
    output.mkdir()
    report = output / "CUSA00001"
    assert invoke(source, output, report) == 0
    result = output / "CUSA00001 (2)"
    assert (result / "example.txt").is_file()
    assert json.loads(report.read_text())[0]["output"] == str(result)


def test_report_write_failure_is_a_clean_cli_error(tmp_path, invoke, monkeypatch, capsys):
    source = write_pkg(tmp_path)
    output = tmp_path / "out"

    def fail(*args, **kwargs):
        raise OSError("report disk full")

    monkeypatch.setattr(cli.json, "dump", fail)
    with pytest.raises(SystemExit) as error:
        invoke(source, output, tmp_path / "report.json")
    assert error.value.code == 1
    assert "report access failed: report disk full" in capsys.readouterr().err
    assert (output / "CUSA00001" / "example.txt").is_file()
