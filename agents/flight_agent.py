"""Flight-search agent: uses the human search page like an automation script would, gets silently rerouted
to the agent lane (no challenge), then lets the LLM pick a flight from the structured results.

    python agents/flight_agent.py [--headless] [--from EDI --to KEF] [--task "cheapest direct flight"]
"""
import argparse
import json
import time

from playwright.sync_api import sync_playwright

from browser import launch
from llm import ask_hedged, final_answer, model_name


def click_centre(page, selector):
    b = page.locator(selector).bounding_box()
    x, y = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    page.mouse.move(x, y, steps=4)
    page.mouse.click(x, y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--from", dest="origin", default="EDI")
    ap.add_argument("--to", dest="dest", default="KEF")
    ap.add_argument("--task", default="the cheapest direct flight")
    ap.add_argument("--hold", type=float, default=6)
    args = ap.parse_args()

    with sync_playwright() as p:
        browser = launch(p, args.headless)
        page = browser.new_page(viewport={"width": 1280, "height": 860})
        page.goto(args.url + "/flights")
        page.wait_for_selector("#from option", state="attached")
        t0 = time.perf_counter()
        page.select_option("#from", args.origin)
        page.select_option("#to", args.dest)
        click_centre(page, "#searchBtn")
        print(f"[flight] searched {args.origin} → {args.dest} on the human site…")

        page.wait_for_url("**/search?*", timeout=15000)
        lane = "agent" if "/agents/" in page.url else "human"
        print(f"[flight] landed in the {lane.upper()} lane: {page.url} ({time.perf_counter() - t0:.1f}s)")
        route = page.evaluate("JSON.parse(sessionStorage.getItem('rc_route') || '{}')")
        for r in route.get("reasons", [])[:4]:
            print(f"    why: {r}")
        if lane != "agent":
            print("[flight] not rerouted. The site thought I was human.")
        else:
            page.wait_for_function("document.getElementById('json').textContent.startsWith('{')")
            data = json.loads(page.locator("#json").text_content())
            compact = [{k: f[k] for k in ("flight", "carrier", "depart_time", "stops", "duration_min", "price_gbp")}
                       for f in data["flights"]]
            raw, s, _ = ask_hedged(f"Flights (JSON): {json.dumps(compact)}\n\nThe user wants {args.task}. "
                                   "Which flight number should be booked?",
                                   system="You are a travel-booking agent. Finish with `ANSWER: <flight number>`.")
            pick = final_answer(raw)
            chosen = next((f for f in compact if f["flight"] in pick), None)
            print(f"[flight] {model_name()} picked {pick} in {s:.1f}s: {json.dumps(chosen)}")
        if not args.headless:
            page.wait_for_timeout(args.hold * 1000)
        browser.close()


if __name__ == "__main__":
    main()
