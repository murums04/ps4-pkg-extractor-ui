import json
import os
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from pkg_extractor_ui import __version__
from pkg_extractor_ui.about import AboutDialog
from pkg_extractor_ui.updates import Release, UpdateChecker, parse_release, portable_asset_name

REPOSITORY = "https://github.com/murums04/ps4-pkg-extractor-ui"
LATEST_RELEASE = "https://api.github.com/repos/murums04/ps4-pkg-extractor-ui/releases/latest"


def release_data(version=__version__, system="win32", machine="AMD64"):
    tag = f"v{version}"
    asset = portable_asset_name(version, system, machine)
    return {
        "tag_name": tag, "draft": False, "prerelease": False,
        "html_url": f"{REPOSITORY}/releases/tag/{tag}",
        "assets": [{"name": asset, "state": "uploaded",
                    "browser_download_url": f"{REPOSITORY}/releases/download/{tag}/{asset}"}],
    }


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def server():
    response = {"status": 200, "body": json.dumps(release_data()).encode(), "requests": []}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            response["requests"].append({
                "path": self.path, "user_agent": self.headers.get("User-Agent"),
                "content_length": self.headers.get("Content-Length"),
            })
            self.send_response(response["status"])
            self.end_headers()
            self.wfile.write(response["body"])

        def log_message(self, *args):
            pass

    http = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=http.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{http.server_port}/latest", response
    finally:
        http.shutdown()
        http.server_close()
        thread.join(timeout=2)


def finish_check(checker):
    deadline = time.monotonic() + 4
    while (checker.startup_timer.isActive() or checker.busy) and time.monotonic() < deadline:
        QTest.qWait(10)
    assert not checker.startup_timer.isActive() and not checker.busy


def test_startup_checks_own_release_once_and_manual_check_can_retry(app, server, monkeypatch):
    endpoint, response = server
    updates = UpdateChecker()
    requested_urls = []
    send_request = updates.manager.get

    def route_to_fixture(request):
        requested_urls.append(request.url().toString())
        request.setUrl(QUrl(endpoint))
        return send_request(request)

    monkeypatch.setattr(updates.manager, "get", route_to_fixture)
    updates.start_automatic_check()
    assert updates.startup_timer.isActive()
    finish_check(updates)
    assert updates.state == "current"
    assert requested_urls == [LATEST_RELEASE]
    assert response["requests"] == [{
        "path": "/latest", "user_agent": f"ps4-pkg-extractor-ui/{__version__}",
        "content_length": None,
    }]
    QTest.qWait(100)
    assert len(response["requests"]) == 1
    updates.check()
    finish_check(updates)
    assert updates.state == "current"
    assert requested_urls == [LATEST_RELEASE, LATEST_RELEASE]
    updates.deleteLater()


@pytest.mark.parametrize("status,state", [(200, "current"), (404, "unpublished"),
                                         (403, "error"), (429, "error"), (500, "error")])
def test_update_http_status_is_reported(app, server, status, state):
    endpoint, response = server
    response["status"] = status
    updates = UpdateChecker(endpoint=endpoint)
    updates.check()
    finish_check(updates)
    assert updates.state == state
    updates.deleteLater()


def test_invalid_update_response_can_be_retried(app, server):
    endpoint, response = server
    response["body"] = b"not json"
    updates = UpdateChecker(endpoint=endpoint)
    updates.check()
    finish_check(updates)
    assert updates.state == "error"
    response["body"] = json.dumps(release_data()).encode()
    updates.check()
    finish_check(updates)
    assert updates.state == "current"
    updates.deleteLater()


@pytest.mark.parametrize(("system", "machine", "suffix"), [
    ("win32", "AMD64", "windows-x64-portable.zip"),
    ("darwin", "arm64", "macos-arm64-portable.zip"),
    ("darwin", "x86_64", "macos-x64-portable.zip"),
    ("linux", "x86_64", "linux-x64-portable.tar.gz"),
])
def test_update_download_names_match_pkg_packages(system, machine, suffix):
    assert portable_asset_name("0.1.1", system, machine) == f"ps4-pkg-extractor-ui-0.1.1-{suffix}"
    release = parse_release(release_data("0.1.1", system, machine), "0.1.0", system, machine)
    assert release.download_url == f"{REPOSITORY}/releases/download/v0.1.1/ps4-pkg-extractor-ui-0.1.1-{suffix}"


def test_update_links_from_another_repository_are_rejected():
    data = release_data("0.1.1")
    data["html_url"] = "https://github.com/other/project/releases/tag/v0.1.1"
    with pytest.raises(ValueError, match="Unexpected release location"):
        parse_release(data, "0.1.0")


def test_about_refreshes_update_actions_and_opens_selected_url(app, monkeypatch):
    updates = UpdateChecker()
    about = AboutDialog(updates)
    opened = []
    monkeypatch.setattr(about, "open_url", opened.append)
    about.show()
    assert about.download_button.isHidden()
    assert about.release_button.isHidden()
    updates.release = Release("0.1.1", "https://example.com/release", "https://example.com/pkg.zip")
    updates.set_status("available", "Update available: 0.1.1")
    assert not about.download_button.isHidden()
    assert not about.release_button.isHidden()
    about.open_download()
    about.open_release()
    assert opened == [updates.release.download_url, updates.release.release_url]
    about.close()
