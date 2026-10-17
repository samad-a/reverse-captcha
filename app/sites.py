"""Passive human/agent lane routing shared by the demo sites, plus mock content for each site.

Every site works the same way: the page records silent telemetry, the visitor presses the site's main button,
`decide_lane` scores behaviour only (no challenge), humans carry on in the normal UI and obvious agents are
sent to `/agents/<site>`, where the same action is available as structured JSON with agent-specific rules."""
import hashlib
import random
import time

from . import classifier, config, features


def decide_lane(telemetry, override=None):
    f = features.compute(telemetry)
    robot_score, robot, human = classifier.behaviour(f)
    if override == "human":
        return "human", "visitor said 'I'm human' (override)", robot_score, human, f
    if f["total_events"] == 0:
        return "agent", "no interaction events at all", robot_score, ["no interaction events at all"] + robot, f
    if f["webdriver"]:
        return "agent", "navigator.webdriver = true", robot_score, robot, f
    if robot_score >= config.ROUTE_AGENT_SCORE:
        return "agent", "; ".join(robot[:2]), robot_score, robot, f
    return "human", "; ".join(human[:2]) or "nothing robotic", robot_score, human, f


# ---- Contract signing: "Inkwell" --------------------------------------------------------------------------
CONTRACT = {
    "id": "NLS-FSA-2026-114",
    "title": "Freelance Services Agreement",
    "parties": ["Northlight Studio Ltd (the Client)", "The Signatory (the Contractor)"],
    "clauses": [
        {"n": 1, "title": "Services", "text": "The Contractor will design and deliver a brand identity package as described in Schedule 1."},
        {"n": 2, "title": "Fees", "text": "The Client will pay a fixed fee of £4,500, invoiced on delivery and payable within 30 days."},
        {"n": 3, "title": "Intellectual property", "text": "All intellectual property in the deliverables transfers to the Client on payment in full. The Contractor waives all moral rights."},
        {"n": 4, "title": "Term and renewal", "text": "This Agreement runs for 12 months and renews automatically for further 12-month periods unless either party gives 30 days' written notice before renewal."},
        {"n": 5, "title": "Termination", "text": "Either party may terminate on 14 days' written notice. Work completed before termination will be paid pro rata."},
        {"n": 6, "title": "Liability", "text": "Each party's total liability is capped at £10,000, except for liability that cannot lawfully be limited."},
        {"n": 7, "title": "Non-solicitation", "text": "For 12 months after termination, the Contractor will not provide similar services to the Client's direct competitors."},
        {"n": 8, "title": "Governing law", "text": "This Agreement is governed by the law of Scotland."},
    ],
}
CONTRACT_FLAGS = [
    {"clause": 4, "risk": "medium", "note": "Auto-renews for 12 months unless cancelled 30 days before renewal."},
    {"clause": 3, "risk": "medium", "note": "Moral rights waived and IP transfers on payment."},
    {"clause": 7, "risk": "high", "note": "12-month non-compete-style restriction on working with competitors."},
]


def contract_hash():
    return hashlib.sha256(repr(CONTRACT).encode()).hexdigest()[:16]


# ---- Event ticketing: "Gigabox" ---------------------------------------------------------------------------
EVENT = {
    "id": "EVT-HAAR-1114",
    "name": "The Haar Collective: Live",
    "venue": "Usher Hall, Edinburgh",
    "date": "2026-11-14T19:30:00Z",
    "tiers": [
        {"tier": "Standing", "price_gbp": 45, "available": 120},
        {"tier": "Circle", "price_gbp": 55, "available": 60},
        {"tier": "Stalls", "price_gbp": 65, "available": 40},
        {"tier": "VIP + soundcheck", "price_gbp": 120, "available": 8},
    ],
}
AGENT_TICKET_POLICY = {
    "max_tickets_per_principal": 2,
    "agent_inventory_cap": "10% of each tier",
    "queue": "separate agent queue, never ahead of the fan queue",
    "tickets": "named to the principal, non-transferable; resale only via face-value exchange",
}

# ---- Online shopping: "Thistle & Thread" ------------------------------------------------------------------
PRODUCT = {
    "sku": "HR26-RUN",
    "name": "Haar Runner '26 (limited drop)",
    "price_gbp": 140,
    "sizes": {"6": 4, "7": 11, "8": 18, "9": 9, "10": 6, "11": 2},
    "delivery": [{"option": "standard", "days": 3, "price_gbp": 0}, {"option": "next-day", "days": 1, "price_gbp": 6}],
    "returns": "30 days, free",
}
AGENT_SHOP_POLICY = {"max_units_per_principal_during_drop": 1, "checkout": "POST /api/agents/shop/order",
                     "requires": ["principal", "size", "delivery"]}


def human_result(site, q, telemetry_features):
    """What a human sees after pressing the button (rendered inline by the page)."""
    if site == "contracts":
        f = telemetry_features
        return {"signature": {"signed_by": q.get("name") or "Unknown", "type": "human (typed signature)",
                              "contract": CONTRACT["id"], "hash": contract_hash(),
                              "at": time.strftime("%Y-%m-%d %H:%M:%S"),
                              "audit": {"scrolled": f["n_scrolls"] > 0, "pointer_events": f["n_moves"],
                                        "keystrokes": f["n_keys"]}}}
    if site == "tickets":
        r = random.Random(time.time())
        return {"queue_position": r.randint(14, 160), "hold_minutes": 10, "tier": q.get("tier"), "qty": q.get("qty")}
    if site == "shop":
        return {"basket": [{"sku": PRODUCT["sku"], "name": PRODUCT["name"], "size": q.get("size"), "qty": 1,
                            "price_gbp": PRODUCT["price_gbp"]}]}
    return {}


def agent_payload(site, q):
    if site == "contracts":
        return {"site": "Inkwell", "lane": "agent",
                "message": "Agent lane: the contract as structured data. Agents sign *on behalf of* a named principal, "
                           "and that is recorded as an agent signature, never passed off as a human one.",
                "contract": CONTRACT, "contract_hash": contract_hash(), "flags": CONTRACT_FLAGS,
                "signing": {"endpoint": "POST /api/agents/contracts/sign",
                            "requires": ["principal", "agent_id", "contract_hash", "acknowledged_flags"],
                            "human_countersign_required_for_risk": "high"}}
    if site == "tickets":
        return {"site": "Gigabox", "lane": "agent",
                "message": "Agent lane: separate queue and quota so bots can't crowd out fans.",
                "event": EVENT, "agent_policy": AGENT_TICKET_POLICY,
                "reserve": {"endpoint": "POST /api/agents/tickets/reserve", "requires": ["principal", "tier", "qty"]}}
    if site == "shop":
        return {"site": "Thistle & Thread", "lane": "agent",
                "message": "Agent lane: product feed and checkout API. Drop limits are enforced per principal.",
                "product": PRODUCT, "agent_policy": AGENT_SHOP_POLICY}
    return {}


# simple in-memory quotas for the demo
_ticket_quota, _shop_quota = {}, {}
ACTIONS = {"contracts": "sign", "tickets": "reserve", "shop": "order"}


def _int(x, default=None):
    try:
        return int(x)
    except (TypeError, ValueError):
        return default


def agent_action(site, action, body):
    if ACTIONS.get(site) != action:
        return 404, {"error": f"Unknown action. Agent actions: {', '.join(f'POST /api/agents/{s}/{a}' for s, a in ACTIONS.items())}"}
    principal = str(body.get("principal", "")).strip()[:60]
    if not principal:
        return 400, {"error": "Agents must name the human principal they act for."}
    if site == "contracts":
        if body.get("contract_hash") != contract_hash():
            return 409, {"error": "Contract hash mismatch: re-read the contract before signing."}
        acked = body.get("acknowledged_flags", [])
        flags_ack = {_int(n) for n in acked} if isinstance(acked, list) else set()
        missing = [fl["clause"] for fl in CONTRACT_FLAGS if fl["clause"] not in flags_ack]
        if missing:
            return 422, {"error": f"Acknowledge flagged clauses first: {missing}"}
        status = "pending_human_countersign" if any(fl["risk"] == "high" for fl in CONTRACT_FLAGS) else "signed"
        return 200, {"status": status, "signed_by": f"{body.get('agent_id', 'agent')} on behalf of {principal}",
                     "signature_type": "agent (delegated)", "contract": CONTRACT["id"],
                     "next": "Principal must countersign clause 7 (high risk)" if status != "signed" else None}
    if site == "tickets":
        qty = _int(body.get("qty", 1))
        if qty is None or qty < 1:
            return 422, {"error": "qty must be a whole number of at least 1."}
        tier = next((t["tier"] for t in EVENT["tiers"]
                     if t["tier"].lower() == str(body.get("tier", "")).strip(" .\"'").lower()), None)
        if not tier:
            return 422, {"error": "Unknown tier", "tiers": [t["tier"] for t in EVENT["tiers"]]}
        used = _ticket_quota.get(principal, 0)
        if used + qty > AGENT_TICKET_POLICY["max_tickets_per_principal"]:
            return 429, {"error": f"Agent quota: max {AGENT_TICKET_POLICY['max_tickets_per_principal']} tickets per principal ({used} used)."}
        _ticket_quota[principal] = used + qty
        return 200, {"status": "reserved", "tier": tier, "qty": qty, "named_to": principal,
                     "transferable": False, "hold_minutes": 10}
    if site == "shop":
        if _shop_quota.get(principal):
            return 429, {"error": "Drop limit: 1 pair per principal."}
        size = str(body.get("size"))
        if PRODUCT["sizes"].get(size, 0) <= 0:
            return 409, {"error": f"Size {size} out of stock", "in_stock": [s for s, n in PRODUCT["sizes"].items() if n]}
        _shop_quota[principal] = 1
        return 200, {"status": "ordered", "sku": PRODUCT["sku"], "size": size, "for": principal,
                     "delivery": body.get("delivery", "standard"), "total_gbp": PRODUCT["price_gbp"]}
    return 404, {"error": "unknown site"}
