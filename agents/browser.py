"""Launch a browser for the agents: Playwright's bundled Chromium if installed, else the system's Edge or Chrome.
Set AGENT_BROWSER=msedge|chrome to force one (handy on slow wifi where `playwright install` can't finish)."""
import os

from playwright.sync_api import Error


def launch(p, headless):
    forced = os.getenv("AGENT_BROWSER")
    if forced:
        return p.chromium.launch(headless=headless, channel=forced)
    try:
        return p.chromium.launch(headless=headless)
    except Error as e:
        if "Executable doesn't exist" not in str(e):
            raise
    for channel in ("msedge", "chrome"):
        try:
            b = p.chromium.launch(headless=headless, channel=channel)
            print(f"[browser] bundled Chromium missing: using system {channel}")
            return b
        except Error:
            pass
    raise SystemExit("No browser found: run `python -m playwright install chromium` or install Edge/Chrome.")
