"""Launch a browser for the agents: Playwright's bundled Chromium if installed, else the system's Edge or Chrome.
Set AGENT_BROWSER=msedge|chrome to force one (handy on slow wifi where `playwright install` can't finish)."""
import ctypes
import os
import sys

from playwright.sync_api import Error

# Room the browser's own title bar, tabs and address bar take around the page (in CSS pixels).
CHROME_W, CHROME_H = 16, 110


def fit_viewport(headless, width=1280, height=860):
    """The page size the agents want, shrunk if needed so the whole window fits above the taskbar.

    Scaled displays (e.g. 125% on a 1080p laptop) have far fewer CSS pixels than the panel resolution suggests.
    """
    if headless or sys.platform != "win32":
        return {"width": width, "height": height}
    class RECT(ctypes.Structure):
        _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long), ("right", ctypes.c_long), ("bottom", ctypes.c_long)]
    r = RECT()
    if not ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(r), 0):  # SPI_GETWORKAREA
        return {"width": width, "height": height}
    return {"width": max(800, min(width, r.right - r.left - CHROME_W)),
            "height": max(500, min(height, r.bottom - r.top - CHROME_H))}


def launch(p, headless):
    forced = os.getenv("AGENT_BROWSER")
    extra = {} if headless else {"args": ["--window-position=0,0"]}
    if forced:
        return p.chromium.launch(headless=headless, channel=forced, **extra)
    try:
        return p.chromium.launch(headless=headless, **extra)
    except Error as e:
        if "Executable doesn't exist" not in str(e):
            raise
    for channel in ("msedge", "chrome"):
        try:
            b = p.chromium.launch(headless=headless, channel=channel, **extra)
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
