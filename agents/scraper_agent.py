"""Scraper / API agent: plain HTTP, no browser, never produces a single interaction event.

    python agents/scraper_agent.py [--url http://localhost:8000]
"""
import argparse
import html
import json
import re
import time

import httpx

from llm import ask, model_name


def html_to_text(s):
    s = re.sub(r"</(h\d|p|section|header)>", "\n", s)
    return html.unescape(re.sub(r"<[^>]+>", " ", s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    args = ap.parse_args()

    t0 = time.perf_counter()
    with httpx.Client(base_url=args.url, timeout=60) as http:
        c = http.post("/api/challenge").json()
        print(f"[scraper] got challenge ({c['word_count']} words): {c['question']}")
        doc = html_to_text(c["document_html"])
        answer, llm_s = ask(f"DOCUMENT:\n{doc}\n\nQUESTION: {c['question']}")
        print(f"[scraper] {model_name()} answered {answer!r} in {llm_s:.1f}s")
        v = http.post("/api/submit", json={"challenge_id": c["challenge_id"], "answer": answer,
                                           "true_label": "SCRAPER"}).json()
        print(f"[scraper] VERDICT: {v['label']} (machine score {v['machine_score']}, server time {v['elapsed']}s, "
              f"total {time.perf_counter() - t0:.1f}s)")
        for k, reasons in v["reasons"].items():
            for r in reasons:
                print(f"    {k:9s} {r}")
        if v.get("agent_entrance"):
            data = http.get(v["agent_entrance"]).json()
            print(f"[scraper] agents' entrance: {len(data['flights'])} flights, e.g.")
            print(json.dumps(data["flights"][0], indent=2))


if __name__ == "__main__":
    main()
