import os
from dataclasses import dataclass
from pathlib import Path

os.environ.setdefault("TURSO_DATABASE_URL", "file:/tmp/exo-validation-flow.sqlite3")
os.environ.setdefault("TURSO_AUTH_TOKEN", "test-token")

from app.domain import PendingStatus
from app.persistence import TursoStore
from app.services import ValidationOrchestrator


def test_validation_state_transitions_are_explicit():
    assert PendingStatus.NOT_FIXED.transition_to(PendingStatus.IN_VALIDATION) == PendingStatus.IN_VALIDATION
    assert PendingStatus.IN_VALIDATION.transition_to(PendingStatus.WAITING_MERGE) == PendingStatus.WAITING_MERGE
    assert PendingStatus.IN_VALIDATION.transition_to(PendingStatus.NOT_FIXED) == PendingStatus.NOT_FIXED


def test_skipped_cannot_enter_validation():
    import pytest
    with pytest.raises(ValueError):
        PendingStatus.SKIPPED.transition_to(PendingStatus.IN_VALIDATION)


class FakeLeader:
    def propose_fix(self, finding):
        return {"accepted": True, "branch": "ignored", "patch": {"src/a.py": "fixed"}, "report": "fixed assertion"}

class FakeReviewer:
    def review(self, report, verification):
        return {"accepted": True, "reason": "tests and report agree"}

class FakeGitHub:
    def __init__(self, ci_green=True, completed=True): self.ci_green = ci_green; self.completed = completed; self.deleted = []; self.prs = []
    def create_branch(self, owner, repo, branch, sha): return {"ref": branch}
    def create_commit(self, owner, repo, branch, message, files): return {"sha": "new-sha"}
    def branch_ci_result(self, repository, branch): return {"completed": self.completed, "success": self.ci_green, "sonar": []}
    def open_pull_request(self, owner, repo, head, base, title, body): self.prs.append(head); return {"html_url": "https://github/pr/1"}
    def delete_branch(self, owner, repo, branch): self.deleted.append(branch)


def make_store(tmp_path):
    return TursoStore(tmp_path / "flow.sqlite3", auth_token="test-token")


def seed(store):
    store.create_job("job-1", "owner/repo", "main", "completed", "now")
    store.add_finding("finding-1", "job-1", "ci:abc", "ci", None, "src/a.py", "não_corrigida", None)


def test_green_ci_reviewer_approval_opens_pr_and_waits_merge(tmp_path):
    store = make_store(tmp_path); seed(store); github = FakeGitHub(True)
    result = ValidationOrchestrator(store, FakeLeader(), FakeReviewer(), github, timeout_seconds=120).process("finding-1")
    assert result["status"] == "aguardando_merge"
    assert result["pr_url"] == "https://github/pr/1"
    assert github.prs and not github.deleted


def test_red_ci_rejects_and_deletes_branch(tmp_path):
    store = make_store(tmp_path); seed(store); github = FakeGitHub(False)
    result = ValidationOrchestrator(store, FakeLeader(), FakeReviewer(), github, timeout_seconds=120).process("finding-1")
    assert result["status"] == "não_corrigida"
    assert result["reason"] == "ci_failed"
    assert github.deleted


def test_timeout_rejects_and_records_distinct_reason(tmp_path):
    store = make_store(tmp_path); seed(store); github = FakeGitHub(True, completed=False)
    result = ValidationOrchestrator(store, FakeLeader(), FakeReviewer(), github, timeout_seconds=0).process("finding-1")
    assert result == {"status": "não_corrigida", "reason": "timeout"}
    assert github.deleted
