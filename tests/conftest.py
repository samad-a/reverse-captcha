"""Point the app at a throwaway database before anything imports it, and keep the trained model out of tests."""
import os
import sys
import tempfile

os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(prefix="rc-test-"), "test.sqlite3")
os.environ["USE_MODEL"] = "0"
os.environ["ADMIN_KEY"] = ""
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
