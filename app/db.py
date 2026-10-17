import json
import sqlite3
import threading
import time

from . import config

_lock = threading.Lock()
_conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
_conn.row_factory = sqlite3.Row
_conn.executescript("""
CREATE TABLE IF NOT EXISTS attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL, label TEXT, likely TEXT, machine_score INTEGER, robot_score INTEGER, passed INTEGER,
  elapsed REAL, correct INTEGER, trap INTEGER, given REAL, expected REAL,
  features TEXT, verdict TEXT, name TEXT, true_label TEXT, token TEXT, archived INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS routes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL, lane TEXT, reason TEXT, query TEXT, robot_score INTEGER, features TEXT, archived INTEGER DEFAULT 0
);
""")


def add_route(lane, reason, query, robot_score=0, f=None):
    with _lock:
        _conn.execute("INSERT INTO routes (ts,lane,reason,query,robot_score,features) VALUES (?,?,?,?,?,?)",
                      (time.time(), lane, reason, json.dumps(query), robot_score, json.dumps(f or {})))
        _conn.commit()


def lanes():
    counts = {r["lane"]: r["c"] for r in _conn.execute(
        "SELECT lane, COUNT(*) c FROM routes WHERE archived=0 GROUP BY lane").fetchall()}
    rows = _conn.execute("SELECT id, ts, lane, reason, query, robot_score FROM routes WHERE archived=0 "
                         "ORDER BY id DESC LIMIT 8").fetchall()
    return {"human": counts.get("human", 0), "agent": counts.get("agent", 0),
            "recent": [{**dict(r), "query": json.loads(r["query"])} for r in rows]}


def add_attempt(v, f, correct, trap, given, expected, true_label=None, token=None):
    with _lock:
        cur = _conn.execute(
            "INSERT INTO attempts (ts,label,likely,machine_score,robot_score,passed,elapsed,correct,trap,given,expected,"
            "features,verdict,true_label,token) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (time.time(), v["label"], v["likely"], v["machine_score"], v["robot_score"], int(v["passed"]), v["elapsed"],
             int(correct), int(trap), given, expected, json.dumps(f), json.dumps(v), true_label, token))
        _conn.commit()
        return cur.lastrowid


def set_name(attempt_id, name):
    with _lock:
        _conn.execute("UPDATE attempts SET name=? WHERE id=? AND passed=0", (name[:24], attempt_id))
        _conn.commit()


def token_valid(token):
    row = _conn.execute("SELECT id FROM attempts WHERE token=? AND passed=1", (token,)).fetchone()
    return row is not None


def _row(r):
    d = dict(r)
    d["verdict"] = json.loads(d["verdict"])
    d.pop("features", None)
    return d


def recent(n=12):
    rows = _conn.execute("SELECT * FROM attempts WHERE archived=0 ORDER BY id DESC LIMIT ?", (n,)).fetchall()
    return [_row(r) for r in rows]


def hall_of_humans(n=10):
    """People who failed, best first: correct-but-slow by time, then closest wrong answers."""
    rows = _conn.execute(
        "SELECT * FROM attempts WHERE archived=0 AND passed=0 AND name IS NOT NULL AND name != '' "
        "ORDER BY correct DESC, CASE WHEN given IS NULL THEN 1e12 ELSE abs(given-expected) END ASC, elapsed ASC LIMIT ?",
        (n,)).fetchall()
    return [_row(r) for r in rows]


def stats():
    rows = _conn.execute("SELECT label, COUNT(*) c FROM attempts WHERE archived=0 GROUP BY label").fetchall()
    return {r["label"]: r["c"] for r in rows}


def reset():
    """Soft reset: hides attempts from the dashboard but keeps them as training data."""
    with _lock:
        _conn.execute("UPDATE attempts SET archived=1")
        _conn.execute("UPDATE routes SET archived=1")
        _conn.commit()


def training_rows():
    return [dict(r) for r in _conn.execute("SELECT * FROM attempts").fetchall()]
