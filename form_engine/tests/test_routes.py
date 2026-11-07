import sys
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from form_engine import routes

PDF = b"%PDF-1.4 fake"


class UnknownFormError(ValueError):
    pass


@pytest.fixture
def client(monkeypatch):
    calls = []

    def fake_fill(session, form_id, signature_b64=None):
        calls.append((session, form_id, signature_b64))
        if form_id == "nope":
            raise UnknownFormError("x")
        if form_id == "badsig":
            raise ValueError("x")
        if form_id == "boom":
            raise RuntimeError("Jane Secret 123-45-6789")
        return PDF

    mod = types.ModuleType("form_engine.fill")
    mod.fill_form = fake_fill
    mod.UnknownFormError = UnknownFormError
    monkeypatch.setitem(sys.modules, "form_engine.fill", mod)
    app = FastAPI()
    app.include_router(routes.router)
    c = TestClient(app)
    c.calls = calls
    return c


def test_success(client):
    r = client.post("/form/fill", json={"session": {"a": 1}, "form_id": "sdge_care"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert "sdge_care_filled.pdf" in r.headers["content-disposition"]
    assert r.content == PDF


def test_mock(client, monkeypatch, tmp_path):
    f = tmp_path / "m.json"
    f.write_text('{"language": "es"}')
    monkeypatch.setattr(routes, "MOCK_SESSION", f)
    r = client.post(
        "/form/fill?mock=true",
        json={"session": {"x": 1}, "form_id": "sdge_care", "signature_png": "sig"},
    )
    assert r.status_code == 200
    assert client.calls[-1] == ({"language": "es"}, "sdge_care", "sig")


def test_mock_unavailable(client, monkeypatch, tmp_path):
    monkeypatch.setattr(routes, "MOCK_SESSION", tmp_path / "missing.json")
    r = client.post(
        "/form/fill?mock=true", json={"session": {}, "form_id": "sdge_care"}
    )
    assert r.json()["error"]["code"] == "mock_unavailable"


def test_unknown_form(client):
    r = client.post("/form/fill", json={"session": {}, "form_id": "nope"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "unknown_form"


def test_value_error(client):
    r = client.post("/form/fill", json={"session": {}, "form_id": "badsig"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "bad_input"


def test_unexpected(client):
    r = client.post(
        "/form/fill", json={"session": {"n": "Jane Secret"}, "form_id": "boom"}
    )
    assert r.status_code == 500
    assert r.json()["error"]["code"] == "fill_failed"
    assert "Jane" not in r.text and "6789" not in r.text


def test_missing_form_id(client):
    assert client.post("/form/fill", json={"session": {}}).status_code == 422


def test_mock_without_session(client, monkeypatch, tmp_path):
    f = tmp_path / "m.json"
    f.write_text('{"language": "es"}')
    monkeypatch.setattr(routes, "MOCK_SESSION", f)
    r = client.post("/form/fill?mock=true", json={"form_id": "sdge_care"})
    assert r.status_code == 200


def test_unmocked_real_route():
    import io
    import json
    from pathlib import Path

    from pypdf import PdfReader

    sess = json.loads(
        (Path(routes.__file__).parent / "fixtures" / "mock_session.json").read_text()
    )
    app = FastAPI()
    app.include_router(routes.router)
    r = TestClient(app).post(
        "/form/fill", json={"session": sess, "form_id": "sdge_care"}
    )
    assert r.status_code == 200
    pages = PdfReader(io.BytesIO(r.content)).pages
    assert len(pages) == 1
    assert "Maria Lopez" in pages[0].extract_text()
