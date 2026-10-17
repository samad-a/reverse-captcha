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


# ---- Job board: "Glenhire" ---------------------------------------------------------------------------------
JOBS = [
    {"id": "J101", "title": "Python Developer", "company": "Northlight Studio", "location": "Edinburgh", "mode": "hybrid", "salary_gbp": [45000, 55000], "tags": ["python", "fastapi", "postgres"]},
    {"id": "J102", "title": "Data Engineer", "company": "Caledonia Analytics", "location": "Glasgow", "mode": "remote", "salary_gbp": [55000, 65000], "tags": ["python", "spark", "dbt"]},
    {"id": "J103", "title": "Machine Learning Engineer", "company": "Haar Labs", "location": "Edinburgh", "mode": "on-site", "salary_gbp": [60000, 75000], "tags": ["pytorch", "llms", "python"]},
    {"id": "J104", "title": "Frontend Developer", "company": "Thistle & Thread", "location": "UK", "mode": "remote", "salary_gbp": [40000, 50000], "tags": ["typescript", "react"]},
    {"id": "J105", "title": "DevOps Engineer", "company": "Kestrel Cloud", "location": "Aberdeen", "mode": "hybrid", "salary_gbp": [50000, 60000], "tags": ["kubernetes", "terraform"]},
    {"id": "J106", "title": "Graduate Software Engineer", "company": "Firth Bank", "location": "Edinburgh", "mode": "hybrid", "salary_gbp": [32000, 32000], "tags": ["java", "graduate"]},
]
AGENT_JOB_POLICY = {
    "max_applications_per_principal_per_day": 3,
    "disclosure": "Agent applications are shown to employers as 'AI-assisted, on behalf of <principal>'",
    "requires": ["principal", "job_id", "cover_note", "candidate_confirmed"],
    "why": "Stops mass auto-apply bots flooding employers, so human applications still get read.",
}

# ---- News: "The Haar Herald" ---------------------------------------------------------------------------------
ARTICLE = {
    "id": "HH-2026-1114",
    "headline": "Edinburgh trams to run through the night in festival trial",
    "standfirst": "A three-week pilot next August will test 24-hour services between the airport and Newhaven, "
                  "with the council promising a decision on a permanent timetable by spring.",
    "author": "Morag Lindsay, Transport Correspondent",
    "published": "2026-11-14T07:30:00Z",
    "paragraphs": [
        "Trams will run around the clock between Edinburgh Airport and Newhaven for three weeks next August, "
        "in a trial the city council says could become permanent if passenger numbers justify the cost.",
        "Services will run every 20 minutes between midnight and 5am during the pilot, which coincides with the "
        "busiest weeks of the festival season, when hotels and late-night venues report the most demand.",
        "The council estimates the trial will cost around £420,000, including extra staff, security and "
        "maintenance carried out during daytime closures on two Sundays.",
        "Hospitality groups welcomed the plan, saying a lack of late transport forced staff to rely on taxis that "
        "can cost more than a shift's wages. Residents along Leith Walk raised concerns about noise.",
        "A decision on whether to make night services permanent is expected by March, after the council reviews "
        "ridership data, complaints and the impact on maintenance schedules.",
    ],
    "tags": ["transport", "edinburgh", "festival"],
}
ARCHIVE = [{"id": f"HH-2026-{1000 + i}", "headline": h} for i, h in enumerate([
    "Fringe ticket sales hit record high", "Leith Walk cycle lane reopens", "Portobello beach clean draws hundreds",
    "Castle esplanade seating plan approved", "New ferry route to Fife announced", "Waverley roof repairs delayed",
    "Haar warning for Forth crossings", "Meadows tree survey published", "Council backs short-let cap",
    "Hibs and Hearts share stadium upgrade fund"], start=1)]
NEWS_LICENSE = {
    "price_per_article_gbp": 0.01,
    "free_articles_per_principal": 3,
    "attribution_required": "Source: The Haar Herald (link to the article)",
    "ai_training_use": False,
    "why": "Crawlers pay for what they read instead of scraping it for free and skipping the ads that fund reporting.",
}


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
    if site == "jobs":
        job = next((j for j in JOBS if j["id"] == q.get("job")), None)
        return {"application": {"job": job, "status": "started", "by": "candidate (human)",
                                "next": "Upload your CV and answer two questions (not part of this demo)."}}
    if site == "news":
        return {"paragraphs": ARTICLE["paragraphs"][2:]}
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
    if site == "jobs":
        return {"site": "Glenhire", "lane": "agent",
                "message": "Agent lane: job feed and an application API. Agent applications are labelled as "
                           "AI-assisted, and there is a daily cap, so bots can't mass-apply.",
                "jobs": JOBS, "agent_policy": AGENT_JOB_POLICY,
                "apply": {"endpoint": "POST /api/agents/jobs/apply", "requires": AGENT_JOB_POLICY["requires"]}}
    if site == "news":
        return {"site": "The Haar Herald", "lane": "agent",
                "message": "Agent lane: licensed content API. Headlines and summaries are free; full text needs a "
                           "licence with attribution, and AI training use is not allowed.",
                "article": {k: ARTICLE[k] for k in ("id", "headline", "standfirst", "author", "published", "tags")},
                "full_text": "withheld: POST /api/agents/news/license", "license": NEWS_LICENSE,
                "archive": ARCHIVE}
    return {}


# simple in-memory quotas for the demo
_ticket_quota, _shop_quota, _job_quota, _news_quota = {}, {}, {}, {}
ACTIONS = {"contracts": "sign", "tickets": "reserve", "shop": "order", "jobs": "apply", "news": "license"}


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
    if site == "jobs":
        job = next((j for j in JOBS if j["id"] == str(body.get("job_id", "")).strip()), None)
        if not job:
            return 422, {"error": "Unknown job_id", "jobs": [j["id"] for j in JOBS]}
        if body.get("candidate_confirmed") is not True:
            return 422, {"error": "The candidate must confirm this application (candidate_confirmed: true)."}
        if not str(body.get("cover_note", "")).strip():
            return 422, {"error": "A cover note is required."}
        applied = _job_quota.setdefault(principal, [])
        if job["id"] in applied:
            return 409, {"error": f"Already applied to {job['id']}."}
        cap = AGENT_JOB_POLICY["max_applications_per_principal_per_day"]
        if len(applied) >= cap:
            return 429, {"error": f"Daily cap: agents can submit {cap} applications per candidate per day. No mass-applying."}
        applied.append(job["id"])
        return 200, {"status": "submitted", "job": f"{job['title']} at {job['company']}",
                     "shown_to_employer_as": f"AI-assisted application on behalf of {principal}",
                     "applications_left_today": cap - len(applied)}
    if site == "news":
        aid = str(body.get("article_id", "")).strip()
        if aid not in {ARTICLE["id"]} | {a["id"] for a in ARCHIVE}:
            return 422, {"error": "Unknown article_id"}
        if body.get("accept_terms") is not True:
            return 422, {"error": "Accept the licence terms first (accept_terms: true).", "license": NEWS_LICENSE}
        used = _news_quota.setdefault(principal, set())
        if aid not in used and len(used) >= NEWS_LICENSE["free_articles_per_principal"]:
            return 402, {"error": "Payment required: free allowance used. Bulk access needs a paid licence.",
                         "price_per_article_gbp": NEWS_LICENSE["price_per_article_gbp"]}
        used.add(aid)
        return 200, {"status": "licensed", "article_id": aid,
                     "full_text": ARTICLE["paragraphs"] if aid == ARTICLE["id"] else ["(archive article text)"],
                     "attribution": NEWS_LICENSE["attribution_required"], "ai_training_use": False,
                     "free_articles_left": NEWS_LICENSE["free_articles_per_principal"] - len(used)}
    return 404, {"error": "unknown site"}
