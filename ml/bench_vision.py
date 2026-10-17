"""Benchmark vision models on screenshot tiles of generated challenges (server must be running for the CSS).

    python ml/bench_vision.py [--fmt png|jpeg] MODEL [MODEL...]
"""
import argparse
import os
import statistics
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agents"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from playwright.sync_api import sync_playwright  # noqa: E402

from app import challenge  # noqa: E402
from llm import ask, final_answer  # noqa: E402
from vision_agent import PROMPT, capture_tiles  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("models", nargs="+")
ap.add_argument("--fmt", default="jpeg")
ap.add_argument("--n", type=int, default=5)
args = ap.parse_args()

cases = []
with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1100, "height": 7600})
    for seed in range(2000, 2000 + args.n):
        c = challenge.generate(seed)
        page.goto("http://localhost:8000/static/style.css")  # same origin for the stylesheet
        page.set_content(f"""<html><head><link rel="stylesheet" href="http://localhost:8000/static/style.css"></head>
            <body class="gate"><main><section id="challenge" class="card"><div class="q-wrap"><div class="q-label">Your task</div>
            <div class="question">{c['question']}</div></div><article id="doc" class="doc" style="max-height:none">{c['document_html']}</article>
            </section></main></body></html>""")
        page.wait_for_timeout(300)
        cases.append((c, capture_tiles(page, args.fmt)))
    b.close()
print(f"{args.n} cases, {len(cases[0][1])} tiles each, {sum(len(t) for t in cases[0][1]) // 1024} KB ({args.fmt})")

for m in args.models:
    def one(case):
        c, tiles = case
        try:
            raw, s = ask(PROMPT, image_png=tiles, model=m)
        except Exception as e:
            return False, 99, str(e)[:60]
        g = challenge.parse_number(final_answer(raw))
        return g is not None and abs(g - c["answer"]) < 0.01, s, final_answer(raw)[:20]
    with ThreadPoolExecutor(args.n) as ex:
        res = list(ex.map(one, cases))
    times = [r[1] for r in res]
    print(f"{m:40s} acc {sum(r[0] for r in res) / len(res):.0%} median {statistics.median(times):.1f}s "
          f"max {max(times):.1f}s {[r[2] for r in res]}", flush=True)
