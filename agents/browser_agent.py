"""Browser agent: Playwright drives a real Chromium, reads the challenge from the DOM (so it sees the hidden trap).

    python agents/browser_agent.py [--headless] [--url http://localhost:8000]
"""
import argparse
import time

from playwright.sync_api import sync_playwright

from llm import ask_hedged, final_answer, model_name


def centre(page, selector):
    b = page.locator(selector).bounding_box()
    return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:8000")
    ap.add_argument("--headless", action="store_true")
    ap.add_argument("--hold", type=float, default=6, help="seconds to keep the window open at the end")
    args = ap.parse_args()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=args.headless)
        page = browser.new_page(viewport={"width": 1280, "height": 860})
        page.goto(args.url + "/?label=BROWSER%20AGENT")
        t0 = time.perf_counter()

        # robot-style: straight line, dead centre, no hesitation
        x, y = centre(page, "#tickbox")
        page.mouse.move(x, y, steps=4)
        page.mouse.click(x, y)
        page.wait_for_selector("#doc .clause, #picker:not(.hidden)")
        if page.locator("#picker:not(.hidden)").count():
            raise SystemExit("The checkbox judged this agent human, so there is no challenge to solve.")
        question = page.locator("#question").text_content()
        doc = page.locator("#doc").text_content()  # includes visually hidden nodes
        print(f"[browser] read {len(doc.split())} words from the DOM. Q: {question}")

        raw, llm_s, n = ask_hedged(f"DOCUMENT:\n{doc}\n\nQUESTION: {question}")
        answer = final_answer(raw)
        print(f"[browser] {model_name()} answered {answer!r} in {llm_s:.1f}s" + (" (hedged)" if n > 1 else ""))

        x, y = centre(page, "#answer")
        page.mouse.move(x, y, steps=4)
        page.mouse.click(x, y)
        page.keyboard.type(answer, delay=8)
        x, y = centre(page, "#submitBtn")
        page.mouse.move(x, y, steps=4)
        page.mouse.click(x, y)

        page.wait_for_function("window.__verdict")
        v = page.evaluate("window.__verdict")
        print(f"[browser] VERDICT: {v['label']} (machine score {v['machine_score']}, server time {v['elapsed']}s, "
              f"total {time.perf_counter() - t0:.1f}s)")
        for k, reasons in v["reasons"].items():
            for r in reasons:
                print(f"    {k:9s} {r}")
        if not args.headless:
            page.wait_for_timeout(args.hold * 1000)
        browser.close()


if __name__ == "__main__":
    main()
