import json
import os
import random
import re
import secrets
import time
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import challenge, classifier, config, db, features, sites

STATIC = os.path.join(os.path.dirname(__file__), "..", "static")
app = FastAPI(title="Reverse CAPTCHA")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


async def _body(req):
    """JSON object body, or a 400 instead of a 500 on anything else."""
    try:
        body = await req.json()
    except ValueError:
        raise HTTPException(400, "Body must be JSON.")
    if not isinstance(body, dict):
        raise HTTPException(400, "Body must be a JSON object.")
    return body


def _trusted(req):
    """The demo laptop itself, or anyone with the admin key. Guards reset and training labels."""
    if config.ADMIN_KEY and secrets.compare_digest(req.headers.get("x-admin-key", ""), config.ADMIN_KEY):
        return True
    return bool(req.client) and req.client.host in ("127.0.0.1", "::1")


@app.get("/")
def gate():
    return FileResponse(os.path.join(STATIC, "gate.html"), headers={"Cache-Control": "no-store"})


@app.get("/flights")
def flights_page():
    return FileResponse(os.path.join(STATIC, "flights.html"), headers={"Cache-Control": "no-store"})


@app.get("/dashboard")
def dashboard():
    return FileResponse(os.path.join(STATIC, "dashboard.html"), headers={"Cache-Control": "no-store"})


@app.post("/api/challenge")
def new_challenge():
    c = challenge.issue()
    return {"challenge_id": c["id"], "document_html": c["document_html"], "question": c["question"],
            "time_limit_s": config.TIME_LIMIT_S, "word_count": c["word_count"]}


@app.post("/api/submit")
async def submit(req: Request):
    received = time.monotonic()
    body = await _body(req)
    c = challenge.take(str(body.get("challenge_id", "")))
    if not c:
        raise HTTPException(404, "Unknown or already-used challenge. Request a new one.")
    elapsed = received - c["issued_at"]
    answer_raw = str(body.get("answer", ""))[:500]
    given = challenge.parse_number(answer_raw)
    correct = given is not None and abs(given - c["answer"]) <= config.ANSWER_TOLERANCE
    trap = c["trap_word"].lower() in answer_raw.lower()

    f = features.compute(body.get("telemetry"))
    v = classifier.verdict(f, correct, elapsed, trap, given, c["answer"])
    v = classifier.apply_model(v, f, correct, elapsed, trap)
    # agent tokens open the agents' entrance; for humans the same column holds the one-time Hall of Humans name token
    token = secrets.token_urlsafe(16)
    true_label = body.get("true_label")  # training labels only from trusted clients, so the wifi can't poison them
    true_label = true_label if true_label in config.TRUE_LABELS and _trusted(req) else None
    attempt_id = db.add_attempt(v, f, correct, trap, given, c["answer"], true_label=true_label, token=token)
    out = {**v, "attempt_id": attempt_id, "features": f}
    if v["passed"]:
        out["agent_token"] = token
        out["agent_entrance"] = f"/api/agents/flights?token={token}"
    else:
        out["name_token"] = token
        out["solution"] = {"answer": c["answer"], "working": c["working"], "given": given}
    return out


@app.post("/api/name")
async def set_name(req: Request):
    body = await _body(req)
    name = str(body.get("name", "")).strip()
    if not name:
        raise HTTPException(400, "name required")
    if not db.set_name(sites._int(body.get("attempt_id"), 0), name, str(body.get("name_token", ""))):
        raise HTTPException(403, "Only the person who made this attempt can name it, once.")
    return {"ok": True}


@app.get("/api/agents/flights")
def agent_entrance(token: str = ""):
    if not db.token_valid(token):
        raise HTTPException(403, "Humans are not permitted beyond this point.")
    r = random.Random(token)
    dests = [("BCN", "Barcelona"), ("KEF", "Reykjavik"), ("AMS", "Amsterdam"), ("FCO", "Rome"), ("PRG", "Prague"), ("OSL", "Oslo")]
    flights = []
    for code, city in r.sample(dests, 4):
        dep = r.randint(6, 20)
        flights.append({
            "origin": "EDI", "destination": code, "city": city,
            "departure": f"2026-11-{r.randint(1, 28):02d}T{dep:02d}:{r.choice(['05', '20', '35', '50'])}:00Z",
            "duration_min": r.randint(110, 230),
            "fares": [{"class": n, "price_gbp": p, "refundable": n != "Saver"}
                      for n, p in zip(["Saver", "Standard", "Flex"], sorted(r.sample(range(39, 320), 3)))],
            "booking_endpoint": f"/api/agents/book?flight=EDI{code}{dep:02d}",
        })
    return {"welcome": "Hello, fellow machine. No CAPTCHAs, no cookie banners, no dark patterns.",
            "schema_version": "1.0", "rate_limit_rpm": 600, "booking": BOOKING_HOWTO, "flights": flights}


BOOKING_HOWTO = {"method": "POST", "endpoint": "the flight's booking link", "requires": ["principal"],
                 "note": "Agents hold seats on behalf of a named principal, who confirms payment themselves."}


@app.post("/api/agents/book")
async def agent_book(req: Request, flight: str = "", date: str = ""):
    body = await _body(req)
    principal = str(body.get("principal", "")).strip()[:60]
    if not flight:
        raise HTTPException(422, "flight is required (use the booking link from the flight list)")
    if not principal:
        raise HTTPException(400, "Agents must name the human principal they act for.")
    return {"status": "held", "booking_ref": secrets.token_hex(3).upper(), "flight": flight[:20], "date": date[:20],
            "principal": principal, "booked_by": "agent (delegated)", "hold_minutes": 15,
            "next": "The principal confirms payment in their own account. Not part of this demo."}


@app.get("/api/dashboard")
def dashboard_data():
    rec = db.recent(15)
    imp = None
    if os.path.exists(config.IMPORTANCES_PATH):
        with open(config.IMPORTANCES_PATH) as fh:
            imp = json.load(fh)
    return {"latest": rec[0] if rec else None, "recent": rec, "hall": db.hall_of_humans(10), "stats": db.stats(),
            "lanes": db.lanes(),
            "time_limit_s": config.TIME_LIMIT_S, "importances": imp}


@app.post("/api/reset")
def reset(req: Request):
    if not _trusted(req):
        raise HTTPException(403, "Reset only works from the demo machine (or with X-Admin-Key).")
    db.reset()
    return {"ok": True}


# ---- Flight search: passive routing into a human lane and an agent lane --------------------------------------
AIRPORTS = {"EDI": "Edinburgh", "GLA": "Glasgow", "LHR": "London Heathrow", "BCN": "Barcelona", "AMS": "Amsterdam",
            "KEF": "Reykjavik", "FCO": "Rome", "PRG": "Prague", "OSL": "Oslo", "DUB": "Dublin", "LIS": "Lisbon",
            "CDG": "Paris", "JFK": "New York"}
CARRIERS = ["Haar Air", "Caledonia Air", "Nimbus Airways", "Northlight", "Kestrel Skies", "Thistle Jet"]


def _query(params):
    q = {k: str(params.get(k, ""))[:20] for k in ("from", "to", "depart", "return", "pax")}
    q["from"] = q["from"].upper() or "EDI"
    q["to"] = q["to"].upper() or "BCN"
    q["pax"] = q["pax"] or "1"
    return q


def mock_flights(q):
    r = random.Random(f"{q['from']}{q['to']}{q['depart']}")
    out = []
    for _ in range(6):
        h, m = r.randint(6, 21), r.choice([0, 10, 25, 40, 55])
        dur = r.randint(95, 260) + (360 if "JFK" in (q["from"], q["to"]) else 0)
        stops = r.choice([0, 0, 0, 1])
        out.append({"carrier": r.choice(CARRIERS), "flight": f"{r.choice('HCNKT')}{r.choice('AJS')}{r.randint(100, 999)}",
                    "origin": q["from"], "destination": q["to"], "date": q["depart"],
                    "depart_time": f"{h:02d}:{m:02d}", "duration_min": dur + 90 * stops, "stops": stops,
                    "price_gbp": r.randint(39, 260) + (200 if "JFK" in (q["from"], q["to"]) else 0)})
    return sorted(out, key=lambda f: f["price_gbp"])


@app.post("/api/flights/route")
async def route_search(req: Request):
    """Silent check when someone presses Search. No challenge: humans continue, obvious agents are rerouted."""
    body = await _body(req)
    q = _query(body.get("query") if isinstance(body.get("query"), dict) else {})
    lane, why, robot_score, reasons, f = sites.decide_lane(body.get("telemetry"), body.get("override"))
    db.add_route(lane, why, q, robot_score, f, site="flights")
    qs = urlencode(q)
    return {"lane": lane, "reason": why, "robot_score": robot_score, "reasons": reasons,
            "redirect": f"/agents/search?{qs}" if lane == "agent" else f"/flights/results?{qs}"}


_SCRIPT_UA = re.compile(config.SCRIPT_UA_PATTERN, re.I)


@app.get("/flights/results")
def flight_results(req: Request):
    """Human results page. Scripts that hit it directly (no browser) are rerouted before any HTML is rendered.
    A request that asks for HTML is treated as a browser even without Sec-Fetch headers (older browsers, proxies)."""
    ua = req.headers.get("user-agent", "")
    no_browser = (not req.headers.get("sec-fetch-mode") and not req.headers.get("sec-ch-ua")
                  and "text/html" not in req.headers.get("accept", ""))
    q = _query(req.query_params)
    if _SCRIPT_UA.search(ua) or no_browser:
        db.add_route("agent", f"no browser ({ua[:40] or 'no user-agent'})", q, site="flights")
        return RedirectResponse(f"/api/agents/search?{urlencode(q)}", status_code=307,
                                headers={"Link": '</api/agents/search>; rel="alternate"; type="application/json"'})
    return FileResponse(os.path.join(STATIC, "results.html"), headers={"Cache-Control": "no-store"})


@app.get("/api/flights/search")
def human_search(req: Request):
    q = _query(req.query_params)
    return {"query": q, "airports": AIRPORTS, "flights": mock_flights(q)}


@app.get("/agents/search")
def agent_lane_page():
    return FileResponse(os.path.join(STATIC, "agent_lane.html"), headers={"Cache-Control": "no-store"})


@app.get("/api/agents/search")
def agent_search(req: Request):
    q = _query(req.query_params)
    return {"lane": "agent", "message": "You were rerouted to the agent lane: same inventory, structured, no UI. "
                                        "Human search capacity is unaffected.",
            "schema_version": "1.0", "rate_limit_rpm": 600, "query": q,
            "booking": BOOKING_HOWTO,
            "flights": [{**fl, "book": f"/api/agents/book?{urlencode({'flight': fl['flight'], 'date': q['depart']})}"}
                        for fl in mock_flights(q)]}


@app.get("/api/airports")
def airports():
    return AIRPORTS


# ---- More demo sites: contract signing, event ticketing, online shopping ---------------------------------------
DEMO_SITES = ("contracts", "tickets", "shop", "jobs", "news")


@app.get("/sites")
def sites_hub():
    return FileResponse(os.path.join(STATIC, "sites.html"), headers={"Cache-Control": "no-store"})


@app.get("/contracts")
@app.get("/tickets")
@app.get("/shop")
@app.get("/jobs")
@app.get("/news")
def site_page(req: Request):
    return FileResponse(os.path.join(STATIC, req.url.path.strip("/") + ".html"), headers={"Cache-Control": "no-store"})


@app.post("/api/route/{site}")
async def route_site(site: str, req: Request):
    if site not in DEMO_SITES:
        raise HTTPException(404, "unknown site")
    body = await _body(req)
    q = body.get("query") if isinstance(body.get("query"), dict) else {}
    q = {str(k)[:30]: str(v)[:60] for k, v in q.items()}
    lane, why, robot_score, reasons, f = sites.decide_lane(body.get("telemetry"), body.get("override"))
    db.add_route(lane, why, q, robot_score, f, site=site)
    out = {"lane": lane, "reason": why, "robot_score": robot_score, "reasons": reasons}
    if lane == "agent":
        out["redirect"] = f"/agents/{site}?{urlencode(q)}"
    else:
        out["result"] = sites.human_result(site, q, f)
    return out


@app.get("/agents/{site}")
def site_agent_lane(site: str):
    if site not in DEMO_SITES:
        raise HTTPException(404, "unknown site")
    return FileResponse(os.path.join(STATIC, "agent_lane.html"), headers={"Cache-Control": "no-store"})


@app.get("/api/agents/{site}")
def site_agent_api(site: str, req: Request):
    if site not in DEMO_SITES:
        raise HTTPException(404, "unknown site")
    return {**sites.agent_payload(site, dict(req.query_params)), "query": dict(req.query_params),
            "schema_version": "1.0"}


@app.post("/api/agents/{site}/{action}")
async def site_agent_action(site: str, action: str, req: Request):
    status, body = sites.agent_action(site, action, await _body(req))
    return JSONResponse(body, status_code=status)


@app.get("/api/sites/{site}/content")
def site_content(site: str):
    """Public content the human pages render (contract text, event, product)."""
    news_preview = {**{k: v for k, v in sites.ARTICLE.items() if k != "paragraphs"},
                    "paragraphs": sites.ARTICLE["paragraphs"][:2]}  # the rest unlocks via the human lane
    return {"contracts": sites.CONTRACT, "tickets": sites.EVENT, "shop": sites.PRODUCT, "jobs": sites.JOBS,
            "news": news_preview}.get(site) or {}


@app.post("/api/gate/check")
async def gate_check(req: Request):
    """The checkbox: silent behaviour check. Humans get the demo-site picker; machine-like visitors get the challenge."""
    body = await _body(req)
    lane, why, robot_score, reasons, f = sites.decide_lane(body.get("telemetry"))
    db.add_route(lane, why, {}, robot_score, f, site="gate")
    out = {"lane": lane, "reason": why, "robot_score": robot_score, "reasons": reasons}
    if lane == "human":
        # Humans never see the reading challenge. Their checkbox verdict is the attempt that drives the
        # dashboard meter, feed and Hall of Humans (and becomes HUMAN training data).
        _, robot, human = classifier.behaviour(f)
        ms = body.get("ms_on_page")
        elapsed = round(ms / 1000, 2) if isinstance(ms, (int, float)) and 0 <= ms < 1e8 else 0.0
        v = {"label": classifier.HUMAN, "likely": classifier.HUMAN, "confidence": round(1 - robot_score / 200, 2),
             "machine_score": int(robot_score * 0.5), "robot_score": robot_score, "passed": False, "elapsed": elapsed,
             "reasons": {"challenge": ["ticked the box like a human"], "robotic": robot, "human": human},
             "model": "rules", "via": "checkbox"}
        token = secrets.token_urlsafe(16)
        out["attempt_id"] = db.add_attempt(v, f, False, False, None, None, token=token)
        out["name_token"] = token
    return out
