import os
import random
import re
import secrets
import time
from urllib.parse import urlencode

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import challenge, classifier, config, db, features, sites

STATIC = os.path.join(os.path.dirname(__file__), "..", "static")
app = FastAPI(title="Reverse CAPTCHA")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


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
    body = await req.json()
    c = challenge.take(body.get("challenge_id", ""))
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
    token = secrets.token_urlsafe(16) if v["passed"] else None
    attempt_id = db.add_attempt(v, f, correct, trap, given, c["answer"],
                                true_label=body.get("true_label"), token=token)
    out = {**v, "attempt_id": attempt_id, "features": f}
    if token:
        out["agent_token"] = token
        out["agent_entrance"] = f"/api/agents/flights?token={token}"
    else:
        out["solution"] = {"answer": c["answer"], "working": c["working"], "given": given}
    return out


@app.post("/api/name")
async def set_name(req: Request):
    body = await req.json()
    name = str(body.get("name", "")).strip()
    if not name:
        raise HTTPException(400, "name required")
    db.set_name(int(body.get("attempt_id", 0)), name)
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
            "schema_version": "1.0", "rate_limit_rpm": 600, "flights": flights}


@app.get("/api/dashboard")
def dashboard_data():
    rec = db.recent(15)
    imp = None
    if os.path.exists(config.IMPORTANCES_PATH):
        import json
        with open(config.IMPORTANCES_PATH) as fh:
            imp = json.load(fh)
    return {"latest": rec[0] if rec else None, "recent": rec, "hall": db.hall_of_humans(10), "stats": db.stats(),
            "lanes": db.lanes(),
            "time_limit_s": config.TIME_LIMIT_S, "importances": imp}


@app.post("/api/reset")
def reset():
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
    body = await req.json()
    q = _query(body.get("query", {}))
    lane, why, robot_score, reasons, f = sites.decide_lane(body.get("telemetry"), body.get("override"))
    db.add_route(lane, why, q, robot_score, f, site="flights")
    qs = urlencode(q)
    return {"lane": lane, "reason": why, "robot_score": robot_score, "reasons": reasons,
            "redirect": f"/agents/search?{qs}" if lane == "agent" else f"/flights/results?{qs}"}


_SCRIPT_UA = re.compile(config.SCRIPT_UA_PATTERN, re.I)


@app.get("/flights/results")
def flight_results(req: Request):
    """Human results page. Scripts that hit it directly (no browser) are rerouted before any HTML is rendered."""
    ua = req.headers.get("user-agent", "")
    no_browser = not req.headers.get("sec-fetch-mode") and not req.headers.get("sec-ch-ua")
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
            "flights": [{**fl, "book": f"/api/agents/book?flight={fl['flight']}&date={q['depart']}"} for fl in mock_flights(q)]}


@app.get("/api/airports")
def airports():
    return AIRPORTS


# ---- More demo sites: contract signing, event ticketing, online shopping ---------------------------------------
DEMO_SITES = ("contracts", "tickets", "shop")


@app.get("/sites")
def sites_hub():
    return FileResponse(os.path.join(STATIC, "sites.html"), headers={"Cache-Control": "no-store"})


@app.get("/contracts")
@app.get("/tickets")
@app.get("/shop")
def site_page(req: Request):
    return FileResponse(os.path.join(STATIC, req.url.path.strip("/") + ".html"), headers={"Cache-Control": "no-store"})


@app.post("/api/route/{site}")
async def route_site(site: str, req: Request):
    if site not in DEMO_SITES:
        raise HTTPException(404, "unknown site")
    body = await req.json()
    q = {k: str(v)[:60] for k, v in (body.get("query") or {}).items()}
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
    from fastapi.responses import JSONResponse
    status, body = sites.agent_action(site, await req.json())
    return JSONResponse(body, status_code=status)


@app.get("/api/sites/{site}/content")
def site_content(site: str):
    """Public content the human pages render (contract text, event, product)."""
    return {"contracts": sites.CONTRACT, "tickets": sites.EVENT, "shop": sites.PRODUCT}.get(site) or {}
