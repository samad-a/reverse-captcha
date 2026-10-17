# Reverse CAPTCHA: "Prove you're not human"

A gate that lets AI agents in and keeps humans out, and works out *what kind* of visitor you are.

## Setup (Windows / PowerShell)
```
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m playwright install chromium
copy .env.example .env   # then add your NEBIUS_API_KEY (or ANTHROPIC_API_KEY + LLM_PROVIDER=anthropic)
```

## Run
```
.venv\Scripts\python run.py            # add --reload while tuning config
```
Gate: http://localhost:8000/ · Dashboard: http://localhost:8000/dashboard

All tunables (time limit, rule thresholds, models) are in `app/config.py`, and most can be overridden in `.env`.
