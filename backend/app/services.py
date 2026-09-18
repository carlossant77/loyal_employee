from __future__ import annotations
from datetime import datetime, timezone
import time
import uuid
from .domain import PendingStatus

class ValidationOrchestrator:
    def __init__(self, store, leader, reviewer, github, timeout_seconds=1200, poll_seconds=5):
        self.store, self.leader, self.reviewer, self.github = store, leader, reviewer, github
        self.timeout_seconds, self.poll_seconds = timeout_seconds, poll_seconds

    def process(self, finding_id: str) -> dict:
        finding = self.store.get_finding(finding_id)
        if not finding: raise ValueError("pendência não encontrada")
        if finding["status"] != PendingStatus.NOT_FIXED.value: raise ValueError("pendência não está em não_corrigida")
        job = self.store.get_job(finding["job_id"])
        owner, repo = job["repository"].split("/", 1)
        branch = f"agent/finding-{finding_id}-{uuid.uuid4().hex[:8]}"
        patch = self.leader.propose_fix(finding)
        if not patch.get("accepted") or not patch.get("patch"):
            return self._reject(finding_id, None, "leader_rejected")
        self.github.create_branch(owner, repo, branch, job["ref"])
        self.github.create_commit(owner, repo, branch, f"fix: {finding_id}", patch["patch"])
        started = datetime.now(timezone.utc).isoformat()
        self.store.update_validation(finding_id, PendingStatus.IN_VALIDATION.value, branch, started, None)
        verification = self._await_ci(job["repository"], branch)
        if not verification.get("completed"):
            return self._reject(finding_id, branch, "timeout")
        if not verification.get("success"):
            return self._reject(finding_id, branch, "ci_failed")
        review = self.reviewer.review(patch, verification)
        if not review.get("accepted"):
            return self._reject(finding_id, branch, "review_rejected")
        pr = self.github.open_pull_request(owner, repo, branch, job["ref"], f"Fix {finding_id}", patch.get("report", "Automated correction"))
        self.store.update_validation(finding_id, PendingStatus.WAITING_MERGE.value, pr_url=pr.get("html_url"), validation_reason=None)
        return {"status": PendingStatus.WAITING_MERGE.value, "pr_url": pr.get("html_url"), "branch": branch}

    def _await_ci(self, repository, branch):
        deadline = time.monotonic() + self.timeout_seconds
        while True:
            result = self.github.branch_ci_result(repository, branch)
            if result.get("completed") or time.monotonic() >= deadline: return result if result.get("completed") else {"completed": False}
            time.sleep(self.poll_seconds)

    def _reject(self, finding_id, branch, reason):
        finding = self.store.get_finding(finding_id); job = self.store.get_job(finding["job_id"]); owner, repo = job["repository"].split("/", 1)
        if branch: self.github.delete_branch(owner, repo, branch)
        self.store.update_validation(finding_id, PendingStatus.NOT_FIXED.value, validation_reason=reason)
        return {"status": PendingStatus.NOT_FIXED.value, "reason": reason}
