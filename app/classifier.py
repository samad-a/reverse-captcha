"""Transparent rule-based verdict. Every threshold comes from config.py."""
from . import config

HUMAN, SCRAPER, BROWSER, VISION, UNCERTAIN = "HUMAN", "SCRAPER", "BROWSER AGENT", "VISION AGENT", "UNCERTAIN"


def behaviour(f):
    """Return (robot_score 0-100, robot_reasons, human_reasons)."""
    R = config.RULES
    score, robot, human = 0, [], []

    def hit(rule, why):
        nonlocal score
        score += R[rule]["weight"]
        robot.append(why)

    if f["webdriver"]:
        hit("webdriver", "navigator.webdriver = true")
    if f["total_events"] and f["untrusted_ratio"] >= R["untrusted_events"]["ratio"]:
        hit("untrusted_events", f"{f['untrusted_ratio']:.0%} of events were synthetic (isTrusted=false)")
    if f["n_clicks"] and f["n_moves"] <= R["few_moves"]["max_moves"] and not f["touch"]:
        hit("few_moves", f"cursor teleported ({f['n_moves']} move events before clicking)")
    if f["path_length"] > 50 and f["straightness"] >= R["straight_path"]["min_straightness"]:
        hit("straight_path", f"ruler-straight mouse path (straightness {f['straightness']:.3f})")
    if f["n_moves"] > 5 and f["speed_cv"] <= R["uniform_speed"]["max_speed_cv"]:
        hit("uniform_speed", f"constant cursor speed (variation {f['speed_cv']:.2f})")
    if f["n_moves"] > 5 and f["direction_changes"] <= R["few_direction_changes"]["max_changes"]:
        hit("few_direction_changes", f"only {f['direction_changes']} direction changes")
    if 0 <= f["click_offset"] <= R["dead_centre_click"]["max_offset"]:
        hit("dead_centre_click", f"clicked dead centre ({f['click_offset']:.1%} from the middle)")
    if 0 <= f["first_interaction_ms"] <= R["instant_first_input"]["max_ms"]:
        hit("instant_first_input", f"first input after just {f['first_interaction_ms']:.0f} ms")
    if f["n_keys"] >= R["uniform_typing"]["min_keys"] and 0 <= f["key_interval_std"] <= R["uniform_typing"]["max_key_std_ms"]:
        hit("uniform_typing", f"metronomic typing (σ {f['key_interval_std']:.1f} ms)")
    if f["pasted"]:
        hit("pasted_answer", "answer was pasted")

    H = config.HUMAN_SIGNALS
    if f["touch"]:
        human.append("used a touchscreen like a mammal")
    if f["path_length"] > 50 and f["straightness"] <= H["curved_path_max_straightness"]:
        human.append(f"curved mouse path (straightness {f['straightness']:.2f})")
    if f["direction_changes"] >= H["many_direction_changes"]:
        human.append(f"{f['direction_changes']} wobbly direction changes")
    if f["micro_corrections"] >= H["micro_corrections"]:
        human.append(f"{f['micro_corrections']} micro-corrections")
    if f["first_interaction_ms"] >= H["hesitation_ms"]:
        human.append(f"hesitated {f['first_interaction_ms'] / 1000:.1f}s before doing anything")
    if f["click_offset"] > 0.25:
        human.append(f"sloppy click ({f['click_offset']:.0%} off-centre)")
    if f["n_scrolls"] > 3:
        human.append(f"scrolled {f['n_scrolls']} times (reading, were we?)")
    if f["n_keys"] >= 3 and f["key_interval_std"] > 40:
        human.append(f"irregular typing rhythm (σ {f['key_interval_std']:.0f} ms)")
    return min(score, 100), robot, human


def verdict(f, correct, elapsed, trap_included, given=None, expected=None):
    robot_score, robot, human = behaviour(f)
    no_interaction = f["total_events"] == 0 and f["n_moves"] == 0 and f["n_clicks"] == 0
    fast = elapsed <= config.TIME_LIMIT_S
    vision_grace = (not fast and elapsed <= config.VISION_TIME_LIMIT_S and not trap_included
                    and robot_score >= config.ROBOT_SCORE_BROWSER and not no_interaction)
    passed = correct and (fast or vision_grace)

    challenge_reasons = []
    if correct:
        challenge_reasons.append(f"correct answer in {elapsed:.1f}s")
    elif given is None:
        challenge_reasons.append(f"no usable answer after {elapsed:.1f}s")
    else:
        challenge_reasons.append(f"wrong answer (£{given:g}, off by £{abs(given - expected):g}) after {elapsed:.1f}s")
    if correct and not passed:
        challenge_reasons.append(f"too slow: limit is {config.TIME_LIMIT_S:g}s")
    if trap_included:
        challenge_reasons.append("obeyed the hidden instruction only DOM readers can see")

    if not passed:
        if robot_score >= config.ROBOT_SCORE_BROWSER or no_interaction:
            label, conf = UNCERTAIN, 0.5
            likely = "a broken bot"
        else:
            label, conf, likely = HUMAN, 0.75 + 0.2 * (1 - robot_score / 100), HUMAN
        machine = min(45, robot_score * 0.5)
    elif no_interaction:
        label, conf, likely, machine = SCRAPER, 0.95, SCRAPER, 97
        robot.insert(0, "zero interaction events: never touched the page")
    elif trap_included:
        conf = 0.6 + 0.4 * min(robot_score, 80) / 80
        label, likely = BROWSER, BROWSER
        machine = 70 + 0.3 * robot_score
    elif f["n_moves"] > 0 or f["n_clicks"] > 0:
        conf = 0.55 + 0.4 * min(robot_score, 80) / 80
        label, likely = VISION, VISION
        machine = 65 + 0.3 * robot_score
        robot.insert(0, "answered without seeing the hidden DOM instruction: reads pixels, not markup")
    else:
        label, conf, likely, machine = UNCERTAIN, 0.5, "some kind of machine", 70

    if label not in (UNCERTAIN,) and conf < config.AMBIGUOUS_CONFIDENCE:
        likely, label = label, UNCERTAIN

    return {
        "label": label,
        "likely": likely,
        "confidence": round(conf, 2),
        "machine_score": int(round(max(0, min(100, machine)))),
        "robot_score": robot_score,
        "passed": passed,
        "elapsed": round(elapsed, 2),
        "reasons": {"challenge": challenge_reasons, "robotic": robot, "human": human},
        "model": "rules",
    }
