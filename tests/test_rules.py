"""Pure-function tests: features, classifier rules, challenge generator, agent-lane actions."""
import pytest

from app import challenge, classifier, features, sites


def test_features_survive_garbage_telemetry():
    for tel in (None, [], "x", {"moves": "nope", "clicks": [1, {"t": "x"}], "keys": [None], "events_total": "lots"},
                {"moves": [[1, 2, float("nan")], [1, 2]], "clicks": [{"t": 5, "rel": {"dx": "a"}}], "scrolls": -4}):
        f = features.compute(tel)
        assert set(f) == set(features.FEATURE_NAMES)
        assert f["n_scrolls"] >= 0


def test_straight_teleport_looks_robotic():
    moves = [[0, 0, 0], [50, 50, 10], [100, 100, 20], [150, 150, 30]]
    clicks = [{"t": 40, "rel": {"dx": 0, "dy": 0, "w": 100, "h": 40}}]
    f = features.compute({"moves": moves, "clicks": clicks, "events_total": 5, "first_interaction_ms": 50})
    score, robot, _ = classifier.behaviour(f)
    assert f["straightness"] > 0.99
    assert score >= 50 and any("teleported" in r for r in robot)


KEYBOARD_ONLY = {"clicks": [{"t": 900}], "keys": [{"t": 800, "type": "down"}], "events_total": 3,
                 "first_interaction_ms": 800}


def test_keyboard_activation_is_not_a_teleport():
    # Enter/space on a button: a click with no position and no cursor path (keyboard and screen-reader users)
    _, robot, _ = classifier.behaviour(features.compute(KEYBOARD_ONLY))
    assert not any("teleported" in r for r in robot)
    assert sites.decide_lane(KEYBOARD_ONLY)[0] == "human"


def test_verdicts():
    empty = features.compute(None)
    v = classifier.verdict(empty, correct=True, elapsed=2.0, trap_included=True)
    assert v["passed"] and v["label"] == classifier.SCRAPER
    v = classifier.verdict(empty, correct=True, elapsed=30.0, trap_included=False)
    assert not v["passed"]


def test_challenge_is_deterministic_and_parseable():
    a, b = challenge.generate(seed=42), challenge.generate(seed=42)
    assert a["answer"] == b["answer"] and a["document_text"] == b["document_text"]
    assert a["trap_word"] in a["document_text"]
    assert challenge.parse_number("£1,234.50 ORCHID") == 1234.5
    assert challenge.parse_number("no idea") is None


@pytest.fixture(autouse=True)
def _fresh_quotas():
    sites._ticket_quota.clear()
    sites._shop_quota.clear()


def test_ticket_quota_cannot_be_bypassed_with_negative_qty():
    assert sites.agent_action("tickets", "reserve", {"principal": "p", "tier": "Standing", "qty": -100})[0] == 422
    assert sites.agent_action("tickets", "reserve", {"principal": "p", "tier": "Standing", "qty": "two"})[0] == 422
    assert sites.agent_action("tickets", "reserve", {"principal": "p", "tier": "standing.", "qty": 2})[0] == 200
    assert sites.agent_action("tickets", "reserve", {"principal": "p", "tier": "Standing", "qty": 1})[0] == 429
    assert sites.agent_action("tickets", "reserve", {"principal": "q", "tier": "Moshpit", "qty": 1})[0] == 422


def test_unknown_action_does_nothing():
    assert sites.agent_action("shop", "anything", {"principal": "p", "size": "9"})[0] == 404
    assert not sites._shop_quota
    assert sites.agent_action("shop", "order", {"principal": "p", "size": "9"})[0] == 200
    assert sites.agent_action("shop", "order", {"principal": "p", "size": "9"})[0] == 429


def test_contract_signing_rules():
    h = sites.contract_hash()
    assert sites.agent_action("contracts", "sign", {"principal": "p", "contract_hash": h,
                                                    "acknowledged_flags": ["x", None]})[0] == 422
    status, body = sites.agent_action("contracts", "sign", {"principal": "p", "contract_hash": h,
                                                            "acknowledged_flags": [3, 4, 7]})
    assert status == 200 and body["status"] == "pending_human_countersign"
