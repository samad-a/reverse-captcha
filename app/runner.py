"""Launch the demo agents from the web UI: one subprocess at a time, its output buffered for the page to poll.

The same scripts as the command line (agents/*.py), with a visible browser on the demo laptop.
"""
import os
import subprocess
import sys
import threading
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
AGENT_DIR = os.path.join(ROOT, "agents")

# name -> (label, script + args). --url is appended at launch. --keep-open leaves the window up to explore.
AGENTS = {
    "scraper": ("Scraper", ["scraper_agent.py"]),
    "browser": ("Browser agent", ["browser_agent.py", "--keep-open"]),
    "vision": ("Vision agent", ["vision_agent.py", "--keep-open"]),
    "flights": ("Flight agent", ["flight_agent.py", "--keep-open"]),
    "contracts": ("Contract agent", ["site_agent.py", "contracts", "--keep-open"]),
    "tickets": ("Ticket agent", ["site_agent.py", "tickets", "--keep-open"]),
    "shop": ("Shopping agent", ["site_agent.py", "shop", "--keep-open"]),
    "jobs": ("Job agent", ["site_agent.py", "jobs", "--keep-open"]),
    "news": ("News crawler", ["site_agent.py", "news", "--keep-open"]),
}
MAX_LINES = 2000
HOLD_OPEN_MARK = "[agent] finished: browser window left open"  # printed by agents/browser.py hold()

_lock = threading.Lock()
_state = {"proc": None, "name": None, "lines": [], "started": None, "returncode": None, "run": 0, "stopped": False}


class Busy(Exception):
    pass


def _command(name, base_url):
    script, *args = AGENTS[name][1]
    return [sys.executable, os.path.join(AGENT_DIR, script), *args, "--url", base_url]


def _pump(proc, run):
    for line in proc.stdout:
        with _lock:
            if _state["run"] != run:
                return
            if len(_state["lines"]) < MAX_LINES:
                _state["lines"].append(line.rstrip("\n"))
    rc = proc.wait()
    with _lock:
        if _state["run"] == run:
            _state["returncode"] = rc


def running():
    p = _state["proc"]
    return p is not None and _state["returncode"] is None and p.poll() is None


def holding():
    """Finished its work and is only keeping the browser window open for people to look around."""
    return running() and HOLD_OPEN_MARK in _state["lines"]


def start(name, base_url, command=None):
    """Start agent `name`. Raises KeyError for unknown agents and Busy if one is already running."""
    if name not in AGENTS:
        raise KeyError(name)
    if holding():  # a finished agent's open window shouldn't block the next one
        stop()
    with _lock:
        if running():
            raise Busy(_state["name"])
        env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
        proc = subprocess.Popen(command or _command(name, base_url), cwd=ROOT, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, text=True, encoding="utf-8",
                                errors="replace")
        _state.update(proc=proc, name=name, lines=[], started=time.time(), returncode=None, run=_state["run"] + 1,
                      stopped=False)
        run = _state["run"]
    threading.Thread(target=_pump, args=(proc, run), daemon=True).start()
    return run


def status(since=0):
    with _lock:
        lines = _state["lines"]
        since = max(0, min(int(since), len(lines)))
        return {"run": _state["run"], "name": _state["name"], "label": AGENTS.get(_state["name"], ("",))[0],
                "running": running(), "holding": holding(), "stopped": _state["stopped"], "returncode": _state["returncode"], "lines": lines[since:],
                "next": len(lines), "started": _state["started"]}


def stop():
    with _lock:
        p = _state["proc"]
        if p is not None and p.poll() is None:
            _state["stopped"] = True
    if p is not None and p.poll() is None:
        p.terminate()
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
