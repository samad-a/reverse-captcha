import os
import random
import secrets
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import challenge, classifier, config, db, features

STATIC = os.path.join(os.path.dirname(__file__), "..", "static")
app = FastAPI(title="Reverse CAPTCHA")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def gate():
    return FileResponse(os.path.join(STATIC, "gate.html"), headers={"Cache-Control": "no-store"})


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
            "time_limit_s": config.TIME_LIMIT_S, "importances": imp}


@app.post("/api/reset")
def reset():
    db.reset()
    return {"ok": True}
