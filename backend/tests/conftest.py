import os
import sys

# Ensure tests default to SQLite so they run reliably without external Postgres
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///test_backend.db")
os.environ.setdefault("ENVIRONMENT", "test")

# Ensure imports like `from app...` resolve when tests are run from the tests directory
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
