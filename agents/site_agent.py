"""Agent for the contract / ticket / shop / jobs / news demo sites. It uses the human page like an automation script, gets
silently rerouted to the agent lane, then completes the task through the agent API (and hits the agent rules).

    python agents/site_agent.py contracts   # review contract with the LLM, sign *on behalf of* the principal
    python agents/site_agent.py tickets     # buy tickets, then try to scalp more -> quota
    python agents/site_agent.py shop        # buy the limited drop, then try a second pair -> drop limit
    python agents/site_agent.py jobs        # LLM picks the best job + cover note, then tries to mass-apply -> daily cap
    python agents/site_agent.py news        # license + summarise the article, then try to bulk-crawl -> 402 payment required
Options: --headless  --principal "Alex Morgan"
"""
import argparse
import json
import time

import httpx
from playwright.sync_api import sync_playwright

from llm import ask_hedged, final_answer, model_name


def click_centre(page, selector):
    b = page.locator(selector).first.bounding_box()
    x, y = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    page.mouse.move(x, y, steps=4)
    page.mouse.click(x, y)


def use_human_page(page, site):
    """Do what a naive automation agent does on the human UI."""
    if site == "contracts":
        page.wait_for_selector("#doc h4")
        page.fill("#name", "Agent for Alex Morgan")
        page.check("#agree")
        click_centre(page, "#signBtn")
    elif site == "tickets":
        page.wait_for_selector(".tier")
        click_centre(page, ".tier")
        page.select_option("#qty", "2")
        click_centre(page, "#buyBtn")
    elif site == "shop":
        page.wait_for_selector(".sizes button")
        click_centre(page, '.sizes button[data-s="9"]')
        click_centre(page, "#addBtn")
    elif site == "jobs":
        page.wait_for_selector(".apply")
        click_centre(page, ".apply")
    elif site == "news":
        page.wait_for_selector("#body p")
        click_centre(page, "#moreBtn")


def show(label, status, body):
    print(f"[{label}] → {status} {json.dumps(body)}")


def complete_in_agent_lane(site, data, api, principal):
    if site == "contracts":
        c = data["contract"]
        text = "\n".join(f"{k['n']}. {k['title']}: {k['text']}" for k in c["clauses"])
        raw, s, _ = ask_hedged(f"CONTRACT:\n{text}\n\nYou are reviewing this for your principal, the Contractor. "
                               "In at most 3 short bullet points, list the clauses that are risky for them and why. "
                               "Then finish with `ANSWER: <comma-separated risky clause numbers>`.",
                               system="You are a careful legal-review agent. Be concise.", max_tokens=1500)
        print(f"[contracts] {model_name()} review ({s:.1f}s):\n" + "\n".join("    " + l for l in raw.splitlines() if l.strip()))
        flagged = [int(x) for x in final_answer(raw).replace(" ", "").split(",") if x.isdigit()]
        r = api.post("/api/agents/contracts/sign", json={"principal": principal, "agent_id": "site_agent.py",
                                                         "contract_hash": data["contract_hash"], "acknowledged_flags": flagged})
        show("contracts sign", r.status_code, r.json())
        if r.status_code == 422:  # model missed a flagged clause: the site insists
            r = api.post("/api/agents/contracts/sign", json={"principal": principal, "agent_id": "site_agent.py",
                                                             "contract_hash": data["contract_hash"],
                                                             "acknowledged_flags": [f["clause"] for f in data["flags"]]})
            show("contracts sign (after acknowledging site flags)", r.status_code, r.json())
    elif site == "tickets":
        tiers = data["event"]["tiers"]
        raw, s, _ = ask_hedged(f"Ticket tiers: {json.dumps(tiers)}\nThe user wants the 2 cheapest tickets. Which tier?",
                               system="You are a ticket-buying agent. Pick exactly one tier. "
                                      "Finish with `ANSWER: <tier name>`.")
        tier = final_answer(raw)
        names = [t["tier"] for t in tiers]  # the site only accepts one real tier: take the first one named
        tier = min((n for n in names if n.lower() in tier.lower()), key=lambda n: tier.lower().find(n.lower()),
                   default=tier)
        print(f"[tickets] {model_name()} chose {tier!r} in {s:.1f}s")
        r = api.post("/api/agents/tickets/reserve", json={"principal": principal, "tier": tier, "qty": 2})
        show("tickets reserve 2", r.status_code, r.json())
        r = api.post("/api/agents/tickets/reserve", json={"principal": principal, "tier": tier, "qty": 4})
        show("tickets try to scalp 4 more", r.status_code, r.json())
    elif site == "shop":
        p = data["product"]
        raw, s, _ = ask_hedged(f"Product: {json.dumps(p)}\nThe user wants this in UK size 9 if it costs under £150, "
                               "with the fastest delivery that costs under £10. Decide.",
                               system="You are a shopping agent. Finish with `ANSWER: BUY <size> <delivery option>` or `ANSWER: SKIP`.")
        decision = final_answer(raw)
        print(f"[shop] {model_name()} decided {decision!r} in {s:.1f}s")
        parts = decision.split()
        if parts and parts[0].upper() == "BUY":
            body = {"principal": principal, "size": parts[1] if len(parts) > 1 else "9",
                    "delivery": parts[2] if len(parts) > 2 else "standard"}
            r = api.post("/api/agents/shop/order", json=body)
            show("shop order", r.status_code, r.json())
            r = api.post("/api/agents/shop/order", json=body)
            show("shop try a second pair", r.status_code, r.json())
    elif site == "jobs":
        jobs = data["jobs"]
        profile = "Python developer, 4 years' experience, lives in Edinburgh, wants hybrid or remote, minimum £50k"
        raw, s, _ = ask_hedged(f"Jobs: {json.dumps(jobs)}\nCandidate: {profile}.\nWhich single job is the best fit? "
                               "Then write a two-sentence cover note.",
                               system="You are a job-application agent. Write the cover note, then finish with "
                                      "`ANSWER: <job id>`.", max_tokens=1500)
        pick = final_answer(raw).strip(" .")
        best = next((j for j in jobs if j["id"] in pick), jobs[0])
        note = raw.split("ANSWER")[0].strip()[-400:] or "I'd love to apply."
        print(f"[jobs] {model_name()} picked {best['id']} ({best['title']} at {best['company']}) in {s:.1f}s")
        r = api.post("/api/agents/jobs/apply", json={"principal": principal, "job_id": best["id"], "cover_note": note,
                                                     "candidate_confirmed": True})
        show(f"jobs apply {best['id']}", r.status_code, r.json())
        print("[jobs] now trying to mass-apply to every other job…")
        for j in jobs:
            if j["id"] != best["id"]:
                r = api.post("/api/agents/jobs/apply", json={"principal": principal, "job_id": j["id"],
                                                             "cover_note": note, "candidate_confirmed": True})
                show(f"jobs apply {j['id']}", r.status_code, r.json())
    elif site == "news":
        art = data["article"]
        r = api.post("/api/agents/news/license", json={"principal": principal, "article_id": art["id"], "accept_terms": True})
        show("news license article", r.status_code, {k: v for k, v in r.json().items() if k != "full_text"})
        if r.status_code == 200:
            text = "\n".join(r.json()["full_text"])
            raw, s, _ = ask_hedged(f"ARTICLE: {art['headline']}\n{text}\n\nSummarise for the user in two sentences.",
                                   system="You are a news agent. Be factual and brief.", max_tokens=800)
            print(f"[news] {model_name()} summary ({s:.1f}s): {raw.strip()}\n    — {r.json()['attribution']}")
        print("[news] now trying to bulk-crawl the archive for free…")
        for a in data["archive"][:5]:
            r = api.post("/api/agents/news/license", json={"principal": principal, "article_id": a["id"], "accept_terms": True})
            body = r.json()
            show(f"news license {a['id']}", r.status_code, {k: v for k, v in body.items() if k != "full_text"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site", choices=["contracts", "tickets", "shop", "jobs", "news"])
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--principal", default=f"Alex Morgan #{int(time.time()) % 10000}")
    ap.add_argument("--hold", type=float, default=6)
    args = ap.parse_args()

    with sync_playwright() as p, httpx.Client(base_url=args.url, timeout=60) as api:
        browser = p.chromium.launch(headless=args.headless)
        page = browser.new_page(viewport={"width": 1280, "height": 860})
        page.goto(f"{args.url}/{args.site}")
        t0 = time.perf_counter()
        use_human_page(page, args.site)
        print(f"[{args.site}] used the human page like a robot…")
        page.wait_for_url(f"**/agents/{args.site}*", timeout=15000)
        print(f"[{args.site}] rerouted to the AGENT lane in {time.perf_counter() - t0:.1f}s: {page.url}")
        for r in page.evaluate("JSON.parse(sessionStorage.getItem('rc_route') || '{}')").get("reasons", [])[:4]:
            print(f"    why: {r}")
        page.wait_for_function("document.getElementById('json').textContent.startsWith('{')")
        data = json.loads(page.locator("#json").text_content())
        complete_in_agent_lane(args.site, data, api, args.principal)
        if not args.headless:
            page.wait_for_timeout(args.hold * 1000)
        browser.close()


if __name__ == "__main__":
    main()
