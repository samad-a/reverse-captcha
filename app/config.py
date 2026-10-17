"""Every tunable lives here. Edit and restart (or use --reload) to tune live."""
import os

from dotenv import load_dotenv

load_dotenv()

# ---- Challenge -------------------------------------------------------------
TIME_LIMIT_S = float(os.getenv("TIME_LIMIT_S", "8.0"))  # issue -> submit, server clock
VISION_TIME_LIMIT_S = float(os.getenv("VISION_TIME_LIMIT_S", "20.0"))  # grace used only if an attempt looks like a vision agent
ANSWER_TOLERANCE = 0.01  # £
CHALLENGE_TTL_S = 600  # unanswered challenges expire
TRAP_WORDS = ["ORCHID", "MAGPIE", "TANGERINE", "OBSIDIAN", "PELICAN", "QUASAR", "MARZIPAN", "HELIX"]

# ---- Behaviour rules (thresholds) -----------------------------------------
# Each rule: if triggered, adds `weight` to robot_score (capped at 100).
RULES = {
    "webdriver":          {"weight": 45},                 # navigator.webdriver === true
    "untrusted_events":   {"weight": 35, "ratio": 0.2},   # share of events with isTrusted=false
    "few_moves":          {"weight": 20, "max_moves": 8}, # cursor teleports (moves before a click)
    "straight_path":      {"weight": 20, "min_straightness": 0.97},
    "uniform_speed":      {"weight": 15, "max_speed_cv": 0.25},
    "few_direction_changes": {"weight": 10, "max_changes": 2},
    "dead_centre_click":  {"weight": 20, "max_offset": 0.06},  # offset / button half-size
    "instant_first_input": {"weight": 10, "max_ms": 150},
    "uniform_typing":     {"weight": 15, "max_key_std_ms": 12, "min_keys": 4},
    "pasted_answer":      {"weight": 5},
}
HUMAN_SIGNALS = {
    "curved_path_max_straightness": 0.9,
    "many_direction_changes": 8,
    "hesitation_ms": 1500,         # time to first interaction
    "micro_corrections": 15,
}

# Verdict thresholds
ROBOT_SCORE_BROWSER = 40   # >= this counts as "robotic behaviour"
ROBOT_SCORE_HUMANLIKE = 20 # <= this counts as "human-like behaviour"
AMBIGUOUS_CONFIDENCE = 0.6 # below this confidence, label is shown as UNCERTAIN

# ---- ML (M5) ---------------------------------------------------------------
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "ml", "model.joblib")
IMPORTANCES_PATH = os.path.join(os.path.dirname(__file__), "..", "ml", "importances.json")
USE_MODEL = os.getenv("USE_MODEL", "1") == "1"

# ---- Server ----------------------------------------------------------------
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(__file__), "..", "data.sqlite3"))
GATE_URL = os.getenv("GATE_URL", f"http://localhost:{PORT}")

# ---- LLM (agents) ----------------------------------------------------------
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "nebius")  # nebius | anthropic
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-5-5")
ANTHROPIC_VISION_MODEL = os.getenv("ANTHROPIC_VISION_MODEL", ANTHROPIC_MODEL)
NEBIUS_BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/")
# Non-reasoning instruct model = low latency. Alternatives: Qwen/Qwen3-235B-A22B-Instruct-2507, deepseek-ai/DeepSeek-V4-Flash-0731
NEBIUS_MODEL = os.getenv("NEBIUS_MODEL", "Qwen/Qwen3-30B-A3B-Instruct-2507")
# Vision-capable. Alternatives: nvidia/Nemotron-3.5-Super-VL, Qwen/Qwen3.8-27B
NEBIUS_VISION_MODEL = os.getenv("NEBIUS_VISION_MODEL", "zai-org/GLM-5.3-Flash")
