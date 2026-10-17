"""Run every agent in demo order, with visible browsers, so the dashboard fills up live.

    python agents/run_demo.py            # all of them
    python agents/run_demo.py gate jobs  # just some (gate, scraper, vision, flights, contracts, tickets, shop, jobs, news)
"""
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
STEPS = [
    ("gate", "Gate: browser agent ticks the box, solves the 6s challenge", ["browser_agent.py", "--hold", "4"]),
    ("scraper", "Gate: scraper never opens a browser", ["scraper_agent.py"]),
    ("vision", "Gate: vision agent reads pixels only, misses the hidden trap", ["vision_agent.py", "--hold", "3"]),
    ("flights", "Flight search: agent rerouted to the agent lane", ["flight_agent.py", "--hold", "3"]),
    ("contracts", "Contracts: agent signs on behalf of its principal", ["site_agent.py", "contracts", "--hold", "3"]),
    ("tickets", "Tickets: agent buys 2, then tries to scalp more", ["site_agent.py", "tickets", "--hold", "3"]),
    ("shop", "Shop: agent buys the drop, then tries a second pair", ["site_agent.py", "shop", "--hold", "3"]),
    ("jobs", "Jobs: agent applies, then tries to mass-apply", ["site_agent.py", "jobs", "--hold", "3"]),
    ("news", "News: crawler licenses an article, then tries to bulk-crawl", ["site_agent.py", "news", "--hold", "3"]),
]


def main():
    wanted = set(sys.argv[1:])
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    for key, title, args in STEPS:
        if wanted and key not in wanted:
            continue
        print(f"\n{'=' * 78}\n  {title}\n{'=' * 78}", flush=True)
        subprocess.run([sys.executable, os.path.join(HERE, args[0]), *args[1:]], env=env)
        time.sleep(1.5)
    print("\nDone. Check the dashboard: http://localhost:8000/dashboard")


if __name__ == "__main__":
    main()
