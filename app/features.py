"""Telemetry (from gate.js) -> flat feature dict. Pure functions, no I/O."""
import math
import statistics as st

FEATURE_NAMES = [
    "n_moves", "path_length", "straightness", "speed_mean", "speed_cv", "direction_changes", "micro_corrections",
    "overshoot", "click_offset", "n_clicks", "first_interaction_ms", "n_keys", "key_interval_std", "pasted",
    "n_scrolls", "untrusted_ratio", "webdriver", "touch", "total_events",
]


def _segments_before_clicks(moves, clicks):
    """Split the move stream into the approach paths leading to each click."""
    segs, i = [], 0
    for c in clicks:
        seg = []
        while i < len(moves) and moves[i][2] <= c["t"]:
            seg.append(moves[i])
            i += 1
        segs.append(seg)
    if i < len(moves):
        segs.append(moves[i:])
    return [s for s in segs if s]


def compute(tel):
    tel = tel or {}
    moves = [m for m in tel.get("moves", []) if isinstance(m, (list, tuple)) and len(m) >= 3]
    clicks = [c for c in tel.get("clicks", []) if isinstance(c, dict) and "t" in c]
    keys = tel.get("keys", [])

    path = 0.0
    speeds, angles = [], []
    for a, b in zip(moves, moves[1:]):
        dx, dy, dt = b[0] - a[0], b[1] - a[1], max(b[2] - a[2], 1)
        d = math.hypot(dx, dy)
        path += d
        if d > 0:
            speeds.append(d / dt)
            angles.append(math.atan2(dy, dx))

    # straightness: per approach segment, chord / path, weighted by path length
    num = den = 0.0
    overshoot = 0
    for seg in _segments_before_clicks(moves, clicks):
        sp = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(seg, seg[1:]))
        if sp > 20:
            chord = math.hypot(seg[-1][0] - seg[0][0], seg[-1][1] - seg[0][1])
            num += chord
            den += sp
    straightness = num / den if den else 1.0

    direction_changes = micro = 0
    for a, b in zip(angles, angles[1:]):
        diff = abs((b - a + math.pi) % (2 * math.pi) - math.pi)
        if diff > math.radians(45):
            direction_changes += 1
        elif diff > math.radians(8):
            micro += 1
        if diff > math.radians(150):
            overshoot += 1

    offsets = []
    for c in clicks:
        rel = c.get("rel")
        if rel and rel.get("w") and rel.get("h"):
            offsets.append(math.hypot(rel["dx"] / (rel["w"] / 2), rel["dy"] / (rel["h"] / 2)) / math.sqrt(2))
    click_offset = st.mean(offsets) if offsets else -1.0

    downs = [k["t"] for k in keys if k.get("type") == "down"]
    intervals = [b - a for a, b in zip(downs, downs[1:]) if b - a < 2000]
    key_std = st.pstdev(intervals) if len(intervals) >= 2 else -1.0

    speed_mean = st.mean(speeds) if speeds else 0.0
    speed_cv = (st.pstdev(speeds) / speed_mean) if len(speeds) >= 2 and speed_mean > 0 else 0.0

    total = int(tel.get("events_total", 0) or 0)
    untrusted = int(tel.get("untrusted_total", 0) or 0)
    fi = tel.get("first_interaction_ms")

    return {
        "n_moves": len(moves),
        "path_length": round(path, 1),
        "straightness": round(straightness, 4),
        "speed_mean": round(speed_mean, 4),
        "speed_cv": round(speed_cv, 4),
        "direction_changes": direction_changes,
        "micro_corrections": micro,
        "overshoot": overshoot,
        "click_offset": round(click_offset, 4),
        "n_clicks": len(clicks),
        "first_interaction_ms": float(fi) if fi is not None else -1.0,
        "n_keys": len(downs),
        "key_interval_std": round(key_std, 2),
        "pasted": int(tel.get("pastes", 0) or 0),
        "n_scrolls": int(tel.get("scrolls", 0) or 0),
        "untrusted_ratio": round(untrusted / total, 3) if total else 0.0,
        "webdriver": 1 if tel.get("webdriver") else 0,
        "touch": 1 if tel.get("touch") else 0,
        "total_events": total,
    }
