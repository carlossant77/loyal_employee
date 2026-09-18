import os
from pathlib import Path

# Tests use the same libSQL client with a disposable file URL; production requires Turso env vars.
os.environ.setdefault("TURSO_DATABASE_URL", f"file:{Path('/tmp/exo-agent-test.sqlite3')}")
os.environ.setdefault("TURSO_AUTH_TOKEN", "test-only-token")
