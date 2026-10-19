"""Regenerate the README screenshots in docs/screenshots. Start the server first (python run.py).

    .venv/Scripts/python docs/take_screenshots.py [name ...]

The agent shots call the configured LLM, like the real agents do.
"""
import math
import os
import random
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "agents"))
from playwright.sync_api import sync_playwright  # noqa: E402
from llm import ask_hedged, final_answer  # noqa: E402

BASE = "http://127.0.0.1:8000"
OUT = os.path.join(REPO, "docs", "screenshots")
os.makedirs(OUT, exist_ok=True)
VIEW = {"width": 1280, "height": 800}
only = set(sys.argv[1:])


def want(name):
    return not only or name in only


def shot(page, name, full=False):
    page.wait_for_timeout(900)
    page.screenshot(path=os.path.join(OUT, name + ".png"), full_page=full)
    print("saved", name)


def centre(page, sel):
    b = page.locator(sel).bounding_box()
    return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2


def human_move(page, x0, y0, x1, y1):
    for i in range(1, 41):
        t = i / 40
        bend = math.sin(t * math.pi) * 90
        page.mouse.move(x0 + (x1 - x0) * t + bend * 0.4 + random.uniform(-3, 3),
                        y0 + (y1 - y0) * t - bend + random.uniform(-3, 3))
        time.sleep(random.uniform(0.02, 0.07))


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    if want("gate") or want("human"):
        ctx = browser.new_context(viewport=VIEW)
        ctx.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => false})")
        page = ctx.new_page()
        page.goto(BASE + "/")
        shot(page, "gate")
        human_move(page, 200, 150, 500, 300)
        page.mouse.wheel(0, 120); time.sleep(0.6); page.mouse.wheel(0, -120); time.sleep(0.8)
        x, y = centre(page, "#tickbox")
        human_move(page, 500, 300, x + 6, y - 5)
        time.sleep(0.9)
        page.mouse.click(x + 6, y - 5)
        page.wait_for_selector("#picker:not(.hidden), #challenge:not(.hidden)", timeout=10000)
        shot(page, "human-blocked")
        ctx.close()

    if want("agent"):
        page = browser.new_page(viewport=VIEW)
        page.goto(BASE + "/?label=BROWSER%20AGENT")
        x, y = centre(page, "#tickbox")
        page.mouse.move(x, y, steps=4); page.mouse.click(x, y)
        page.wait_for_selector("#doc .clause", timeout=10000)
        page.wait_for_timeout(300)
        page.screenshot(path=os.path.join(OUT, "challenge.png")); print("saved challenge")
        q = page.locator("#question").text_content()
        doc = page.locator("#doc").text_content()
        raw, _, _ = ask_hedged(f"DOCUMENT:\n{doc}\n\nQUESTION: {q}")
        ans = final_answer(raw)
        x, y = centre(page, "#answer"); page.mouse.move(x, y, steps=4); page.mouse.click(x, y)
        page.keyboard.type(ans, delay=8)
        x, y = centre(page, "#submitBtn"); page.mouse.move(x, y, steps=4); page.mouse.click(x, y)
        page.wait_for_function("window.__verdict")
        page.wait_for_timeout(1500)
        shot(page, "agent-granted")
        page.close()

    page = browser.new_page(viewport=VIEW, user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36")
    for name, path in [("dashboard", "/dashboard"), ("flights", "/flights"),
                       ("flights-results", "/flights/results?from=EDI&to=KEF"),
                       ("contracts", "/contracts"), ("tickets", "/tickets"),
                       ("shop", "/shop"), ("jobs", "/jobs"), ("news", "/news"),
                       ("agent-lane-contracts", "/agents/contracts")]:
        if want(name):
            page.goto(BASE + path)
            shot(page, name)
    browser.close()
