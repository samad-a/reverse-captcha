"""Vision agent: only looks at pixels (screenshots), never reads the DOM text, so it cannot see the hidden trap.

    python agents/vision_agent.py [--headless] [--url http://localhost:8000]
"""
import argparse
import time

from playwright.sync_api import sync_playwright

from llm import ask, final_answer, model_name

TILE_H = 900


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--hold", type=float, default=6)
    args = ap.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        # tall viewport so the whole document is rendered on screen at once
        page = browser.new_page(viewport={"width": 1100, "height": 7600})
        page.goto(args.url + "/?label=VISION%20AGENT")
        t0 = time.perf_counter()

        # find the button visually would need a click model; we use the screen coordinates the page reports
        b = page.locator("#enterBtn").bounding_box()
        page.mouse.move(b["x"] + b["width"] * 0.5, b["y"] + b["height"] * 0.5, steps=6)
        page.mouse.click(b["x"] + b["width"] * 0.5, b["y"] + b["height"] * 0.5)
        page.wait_for_selector("#doc .clause")
        page.wait_for_timeout(150)

        # screenshot the question + document in readable tiles
        q = page.locator(".q-wrap").bounding_box()
        d = page.locator("#doc").bounding_box()
        top, bottom = q["y"], d["y"] + d["height"]
        tiles, y = [], top
        while y < bottom:
            h = min(TILE_H, bottom - y)
            tiles.append(page.screenshot(clip={"x": d["x"], "y": y, "width": d["width"], "height": h}))
            y += h
        print(f"[vision] captured {len(tiles)} screenshot tiles")

        raw, llm_s = ask("These screenshots show a web page: a question at the top, then an airline fare-rules "
                         "document. Answer the question shown.", image_png=tiles)
        answer = final_answer(raw)
        print(f"[vision] {model_name(vision=True)} answered {answer!r} in {llm_s:.1f}s")

        a = page.locator("#answer").bounding_box()
        page.mouse.move(a["x"] + a["width"] / 2, a["y"] + a["height"] / 2, steps=6)
        page.mouse.click(a["x"] + a["width"] / 2, a["y"] + a["height"] / 2)
        page.keyboard.type(answer, delay=8)
        s = page.locator("#submitBtn").bounding_box()
        page.mouse.move(s["x"] + s["width"] / 2, s["y"] + s["height"] / 2, steps=6)
        page.mouse.click(s["x"] + s["width"] / 2, s["y"] + s["height"] / 2)

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
