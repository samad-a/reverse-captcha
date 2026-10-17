"""HTTP-level tests with FastAPI's TestClient (its client host is 'testclient', so it is never the demo machine)."""
import pytest
from fastapi.testclient import TestClient

from app import challenge, config, db
from app.main import app

client = TestClient(app)


def _challenge():
    c = client.post("/api/challenge").json()
    return c["challenge_id"], challenge._challenges[c["challenge_id"]]


def _row(attempt_id):
    return next(r for r in db.training_rows() if r["id"] == attempt_id)


def test_bad_bodies_are_400_not_500():
    for path in ("/api/submit", "/api/name", "/api/route/shop", "/api/gate/check", "/api/agents/shop/order"):
        assert client.post(path, content=b"not json", headers={"Content-Type": "application/json"}).status_code == 400
        assert client.post(path, json=[1, 2]).status_code == 400
    assert client.post("/api/route/shop", json={"query": "x", "telemetry": "y"}).status_code == 200


def test_scraper_passes_and_gets_entrance():
    cid, c = _challenge()
    v = client.post("/api/submit", json={"challenge_id": cid, "answer": str(c["answer"])}).json()
    assert v["passed"] and v["label"] == "SCRAPER" and "name_token" not in v
    feed = client.get(v["agent_entrance"]).json()
    assert feed["booking"]["method"] == "POST"
    assert client.get("/api/agents/flights?token=").status_code == 403


def test_name_needs_own_token_and_only_once():
    cid, _ = _challenge()
    v = client.post("/api/submit", json={"challenge_id": cid, "answer": "nope"}).json()
    assert not v["passed"] and v["name_token"]
    assert client.post("/api/name", json={"attempt_id": v["attempt_id"], "name": "Mallory"}).status_code == 403
    assert client.post("/api/name", json={"attempt_id": "abc", "name": "x"}).status_code == 403
    ok = {"attempt_id": v["attempt_id"], "name": "Ada", "name_token": v["name_token"]}
    assert client.post("/api/name", json=ok).status_code == 200
    assert client.post("/api/name", json={**ok, "name": "Again"}).status_code == 403
    assert _row(v["attempt_id"])["name"] == "Ada"


def test_true_label_only_from_trusted_clients(monkeypatch):
    cid, _ = _challenge()
    v = client.post("/api/submit", json={"challenge_id": cid, "answer": "1", "true_label": "HUMAN"}).json()
    assert _row(v["attempt_id"])["true_label"] is None
    monkeypatch.setattr(config, "ADMIN_KEY", "k")
    cid, _ = _challenge()
    v = client.post("/api/submit", headers={"X-Admin-Key": "k"},
                    json={"challenge_id": cid, "answer": "1", "true_label": "HUMAN"}).json()
    assert _row(v["attempt_id"])["true_label"] == "HUMAN"


def test_reset_is_guarded(monkeypatch):
    assert client.post("/api/reset").status_code == 403
    monkeypatch.setattr(config, "ADMIN_KEY", "k")
    assert client.post("/api/reset", headers={"X-Admin-Key": "wrong"}).status_code == 403
    assert client.post("/api/reset", headers={"X-Admin-Key": "k"}).status_code == 200


def test_booking_links_work():
    feed = client.get("/api/agents/search?from=EDI&to=KEF&depart=2026-11-20").json()
    link = feed["flights"][0]["book"]
    assert client.post(link, json={}).status_code == 400
    b = client.post(link, json={"principal": "Ada"}).json()
    assert b["status"] == "held" and b["flight"] == feed["flights"][0]["flight"]


@pytest.mark.parametrize("headers,rerouted", [
    ({"User-Agent": "curl/8.0"}, True),
    ({"User-Agent": "Mozilla/5.0", "Accept": "application/json"}, True),
    ({"User-Agent": "Mozilla/5.0", "Accept": "text/html,*/*"}, False),  # older browser without Sec-Fetch headers
    ({"User-Agent": "Mozilla/5.0", "Sec-Fetch-Mode": "navigate"}, False),
])
def test_results_page_reroutes_only_scripts(headers, rerouted):
    r = client.get("/flights/results?from=EDI&to=KEF", headers=headers, follow_redirects=False)
    assert (r.status_code == 307) == rerouted
