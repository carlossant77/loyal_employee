from __future__ import annotations
import asyncio
import json
import os
from pathlib import Path
from typing import Any
from libsql_client import create_client
from .domain import ScopePolicy

SCHEMA = (
    "CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, repository TEXT NOT NULL, ref TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL)",
    "CREATE TABLE IF NOT EXISTS findings(id TEXT PRIMARY KEY, job_id TEXT NOT NULL, correlation TEXT NOT NULL, origin TEXT NOT NULL, category TEXT, path TEXT NOT NULL, status TEXT NOT NULL, pr_url TEXT, branch_name TEXT, validation_started_at TEXT, validation_reason TEXT, FOREIGN KEY(job_id) REFERENCES jobs(id))",
    "CREATE TABLE IF NOT EXISTS scope(id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)",
)

class TursoStore:
    def __init__(self, path: str | Path | None = None, auth_token: str | None = None):
        if path is not None:
            url = str(path)
            if not url.startswith(("file:", "http://", "https://", "libsql://")): url = f"file:{url}"
        else:
            url = os.getenv("TURSO_DATABASE_URL"); auth_token = auth_token or os.getenv("TURSO_AUTH_TOKEN")
            if not url or not auth_token: raise RuntimeError("TURSO_DATABASE_URL e TURSO_AUTH_TOKEN são obrigatórios")
        self.url, self.auth_token = url, auth_token
        self._client = create_client(url, auth_token=auth_token)
        self._initialize()

    @classmethod
    def from_environment(cls): return cls()
    def _run(self, operation): return asyncio.run(operation)
    async def _execute_async(self, statement, args=None): return await self._client.execute(statement, args or [])
    def _execute(self, statement, args=None): return self._run(self._execute_async(statement, args))
    def _initialize(self):
        self._execute("CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY, repository TEXT NOT NULL, ref TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL)")
        self._execute("CREATE TABLE IF NOT EXISTS findings(id TEXT PRIMARY KEY, job_id TEXT NOT NULL, correlation TEXT NOT NULL, origin TEXT NOT NULL, category TEXT, path TEXT NOT NULL, status TEXT NOT NULL, pr_url TEXT, branch_name TEXT, validation_started_at TEXT, validation_reason TEXT, FOREIGN KEY(job_id) REFERENCES jobs(id))")
        self._execute("CREATE TABLE IF NOT EXISTS scope(id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)")
        for column in ("branch_name TEXT", "validation_started_at TEXT", "validation_reason TEXT"):
            try: self._execute(f"ALTER TABLE findings ADD COLUMN {column}")
            except Exception: pass
        if not self._execute("SELECT 1 FROM scope WHERE id=1").rows: self._execute("INSERT INTO scope VALUES(1, ?)", [json.dumps(ScopePolicy.default().to_dict())])
    @staticmethod
    def _rows(result): return [dict(zip(result.columns, row)) for row in result.rows]
    def create_job(self, job_id, repository, ref, status, created_at): self._execute("INSERT INTO jobs VALUES(?,?,?,?,?)", [job_id, repository, ref, status, created_at])
    def add_finding(self, finding_id, job_id, correlation, origin, category, path, status, pr_url): self._execute("INSERT INTO findings(id,job_id,correlation,origin,category,path,status,pr_url) VALUES(?,?,?,?,?,?,?,?)", [finding_id, job_id, correlation, origin, category, path, status, pr_url])
    def list_jobs(self): return self._rows(self._execute("SELECT id, repository, ref, status, created_at FROM jobs ORDER BY created_at DESC LIMIT 100"))
    def list_findings(self, status=None):
        query = "SELECT id, job_id, correlation, origin, category, path, status, pr_url, branch_name, validation_reason FROM findings"
        result = self._execute(query + (" WHERE status=?" if status else "") + " ORDER BY rowid DESC LIMIT 500", [status] if status else [])
        return self._rows(result)
    def get_finding(self, finding_id):
        rows = self._rows(self._execute("SELECT * FROM findings WHERE id=?", [finding_id])); return rows[0] if rows else None
    def get_job(self, job_id):
        rows = self._rows(self._execute("SELECT * FROM jobs WHERE id=?", [job_id])); return rows[0] if rows else None
    def update_validation(self, finding_id, status, branch_name=None, validation_started_at=None, validation_reason=None, pr_url=None):
        self._execute("UPDATE findings SET status=?, branch_name=COALESCE(?,branch_name), validation_started_at=COALESCE(?,validation_started_at), validation_reason=?, pr_url=COALESCE(?,pr_url) WHERE id=?", [status, branch_name, validation_started_at, validation_reason, pr_url, finding_id])
    def get_scope(self): return json.loads(self._execute("SELECT payload FROM scope WHERE id=1").rows[0][0])
    def set_scope(self, payload): self._execute("UPDATE scope SET payload=? WHERE id=1", [json.dumps(ScopePolicy.from_dict(payload).to_dict())])
    def waiting_correlations(self): return {row[0] for row in self._execute("SELECT correlation FROM findings WHERE status=?", ["aguardando_merge"]).rows}
    def close(self): self._run(self._client.close())

SqliteStore = TursoStore
