"""Vision agent: only looks at pixels (screenshots), never reads the DOM text, so it cannot see the hidden trap.

    python agents/vision_agent.py [--headless] [--url http://localhost:8000]
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
from playwright.sync_api import sync_playwright  # noqa: E402

from llm import ask_hedged, final_answer, model_name  # noqa: E402
from app import config  # noqa: E402

TILE_H = 1000
PROMPT = ("These screenshots show one web page from top to bottom: a question, then an airline fare-rules "
          "document. Answer the question shown.")


def capture_tiles(page, fmt="jpeg"):
    """Screenshot the question + document in readable vertical tiles."""
    q = page.locator(".q-wrap").bounding_box()
    d = page.locator("#doc").bounding_box()
    top, bottom = q["y"], d["y"] + d["height"]
    tiles, y = [], top
    while y < bottom:
        h = min(TILE_H, bottom - y)
        opts = {"type": "jpeg", "quality": 70} if fmt == "jpeg" else {}
        tiles.append(page.screenshot(clip={"x": d["x"], "y": y, "width": d["width"], "height": h}, **opts))
        y += h
    return tiles


def click_centre(page, selector):
    b = page.locator(selector).bounding_box()
    x, y = b["x"] + b["width"] / 2, b["y"] + b["height"] / 2
    page.mouse.move(x, y, steps=6)
    page.mouse.click(x, y)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--hold", type=float, default=6)
    args = ap.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        # tall viewport so the whole document is rendered on screen at once
        page = browser.new_page(viewport={"width": 1100, "height": 7600})
        page.goto(args.url + "/?label=VISION%20AGENT")
        page.add_style_tag(content=".doc{max-height:none!important}")
        t0 = time.perf_counter()

        click_centre(page, "#tickbox")
        page.wait_for_selector("#doc .clause, #picker:not(.hidden)")
        if page.locator("#picker:not(.hidden)").count():  # judged human by the checkbox: take the dare
            click_centre(page, "#tryChallenge")
        page.wait_for_selector("#doc .clause")
        page.wait_for_timeout(100)
        tiles = capture_tiles(page)
        print(f"[vision] captured {len(tiles)} screenshot tiles ({sum(map(len, tiles)) // 1024} KB)")

        raw, llm_s, n = ask_hedged(PROMPT, hedge_after=config.VISION_HEDGE_AFTER_S, image_png=tiles)
        answer = final_answer(raw)
        print(f"[vision] {model_name(vision=True)} answered {answer!r} in {llm_s:.1f}s"
              + (" (hedged: 2nd request won the race)" if n > 1 else ""))

        click_centre(page, "#answer")
        page.keyboard.type(answer, delay=8)
        click_centre(page, "#submitBtn")

        page.wait_for_function("window.__verdict")
        v = page.evaluate("window.__verdict")
        print(f"[vision] VERDICT: {v['label']} (machine score {v['machine_score']}, server time {v['elapsed']}s, "
              f"total {time.perf_counter() - t0:.1f}s)")
        for k, reasons in v["reasons"].items():
            for r in reasons:
                print(f"    {k:9s} {r}")
        if not args.headless:
            page.set_viewport_size({"width": 1100, "height": 860})
            page.wait_for_timeout(args.hold * 1000)
        browser.close()


if __name__ == "__main__":
    main()
