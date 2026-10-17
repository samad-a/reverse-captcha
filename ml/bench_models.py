"""Benchmark LLM accuracy + latency on generated challenges:  python ml/bench_models.py MODEL [MODEL...]"""
import os, re, sys, html, statistics
from concurrent.futures import ThreadPoolExecutor
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "agents"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from llm import ask, final_answer  # noqa
from app import challenge  # noqa

N = int(os.getenv("N", "6"))

def one(model, seed):
    c = challenge.generate(seed)
    try:
        raw, s = ask(f"DOCUMENT:\n{c['document_text']}\n\nQUESTION: {c['question']}", model=model)
    except Exception as e:
        return False, 99, False, str(e)[:80]
    a = final_answer(raw)
    g = challenge.parse_number(a)
    return g is not None and abs(g - c["answer"]) < 0.01, s, c["trap_word"].lower() in a.lower(), a[:40]

for m in sys.argv[1:]:
    with ThreadPoolExecutor(N) as ex:
        res = list(ex.map(lambda sd: one(m, sd), range(1000, 1000 + N)))
    acc = sum(r[0] for r in res) / N; trap = sum(r[2] for r in res) / N
    print(f"{m:45s} acc {acc:.0%} trap {trap:.0%} median {statistics.median(r[1] for r in res):.1f}s max {max(r[1] for r in res):.1f}s | {[r[3] for r in res][:3]}", flush=True)
