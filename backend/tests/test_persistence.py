import json
from app.domain import FindingOrigin, PendingStatus, ScopePolicy
from app.persistence import SqliteStore


def test_job_and_findings_are_persisted_and_filterable(tmp_path):
    store = SqliteStore(tmp_path / "test.sqlite3")
    store.create_job("job-1", "org/repo", "main", "completed", "2026-01-01T00:00:00Z")
    store.add_finding("finding-1", "job-1", "ci:abc", FindingOrigin.CI.value, None, "src/a.py", PendingStatus.NOT_FIXED.value, None)
    store.add_finding("finding-2", "job-1", "sonar:x", FindingOrigin.SONAR.value, "reliability", "src/b.py", PendingStatus.SKIPPED.value, None)
    assert store.list_jobs()[0]["id"] == "job-1"
    assert len(store.list_findings()) == 2
    assert store.list_findings(PendingStatus.SKIPPED.value)[0]["id"] == "finding-2"


def test_scope_policy_is_read_and_written_as_persisted_data(tmp_path):
    store = SqliteStore(tmp_path / "scope.sqlite3")
    original = store.get_scope()
    assert original == ScopePolicy.default().to_dict()
    replacement = {"category":{"allowlist":["bug"],"denylist":[]},"path":{"allowlist":["src/"],"denylist":[]},"origin":{"allowlist":["sonar"],"denylist":[]},"combination":"AND"}
    store.set_scope(replacement)
    assert store.get_scope() == replacement


def test_waiting_correlations_are_queryable(tmp_path):
    store = SqliteStore(tmp_path / "guard.sqlite3")
    store.create_job("job-1", "org/repo", "main", "completed", "now")
    store.add_finding("finding-1", "job-1", "ci:abc", "ci", None, "src/a.py", PendingStatus.WAITING_MERGE.value, "https://github/pr/1")
    assert store.waiting_correlations() == {"ci:abc"}
