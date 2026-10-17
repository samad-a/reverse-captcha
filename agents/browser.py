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


HOLD_OPEN_MARK = "[agent] finished: browser window left open"


def hold(page, args):
    """Keep the window up at the end: for --hold seconds, or with --keep-open until the person closes it."""
    if args.headless:
        return
    if getattr(args, "keep_open", False):
        print(HOLD_OPEN_MARK, flush=True)
        try:
            page.wait_for_event("close", timeout=0)
        except Error:
            pass
        print("[agent] window closed", flush=True)
    else:
        page.wait_for_timeout(args.hold * 1000)
