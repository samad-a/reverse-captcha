"""One command: python run.py  (add --reload while tuning)"""
import sys

import uvicorn

from app import config

if __name__ == "__main__":
    print(f"\n  Gate:      http://localhost:{config.PORT}/\n  Dashboard: http://localhost:{config.PORT}/dashboard\n")
    uvicorn.run("app.main:app", host=config.HOST, port=config.PORT, reload="--reload" in sys.argv)
