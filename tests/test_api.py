from __future__ import annotations
import sys, pathlib; sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from unittest import mock
from urllib import error

import pytest

from usage_report.api import SimAPI, SimAPIError


class DummyResponse:
    def __init__(self, status: int, data: bytes):
        self.status = status
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_fetch_user_success():
    api = SimAPI()
    dummy = DummyResponse(200, b'{"kennung": "testuser"}')
    with mock.patch.object(api, "_get_auth", return_value=("u", "p")):
        with mock.patch("urllib.request.urlopen", return_value=dummy):
            data = api.fetch_user("testuser")
    assert data == {"kennung": "testuser"}


def test_fetch_user_failure():
    api = SimAPI()
    dummy = DummyResponse(404, b'Not found')
    with mock.patch.object(api, "_get_auth", return_value=("u", "p")):
        with mock.patch("urllib.request.urlopen", return_value=dummy):
            with pytest.raises(SimAPIError):
                api.fetch_user("baduser")


def test_fetch_user_http_error():
    api = SimAPI()
    http_err = error.HTTPError(
        api.BASE_URL + "baduser",
        403,
        "Forbidden",
        hdrs=None,
        fp=None,
    )
    with mock.patch.object(api, "_get_auth", return_value=("u", "p")):
        with mock.patch("urllib.request.urlopen", side_effect=http_err):
            with pytest.raises(SimAPIError):
                api.fetch_user("baduser")


def test_fetch_user_request_headers(monkeypatch):
    api = SimAPI()
    captured = {}

    def fake_urlopen(req):
        captured["url"] = req.full_url
        captured["auth"] = req.headers.get("Authorization")
        captured["accept"] = req.headers.get("Accept")
        return DummyResponse(200, b"{}")

    monkeypatch.setattr(api, "_get_auth", lambda: ("u", "p"))
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    api.fetch_user("testuser")

    assert captured["url"].endswith("testuser")
    assert captured["auth"].startswith("Basic ")
    assert captured["accept"] == "application/json"
