from __future__ import annotations
import json
import os
import time
from urllib.parse import urlencode
from dataclasses import dataclass
from urllib.request import Request, urlopen

@dataclass
class GitHubPullRequestProvider:
    """Creates PRs only; no merge endpoint or merge permission is exposed."""
    token: str
    api_base: str = "https://api.github.com"

    @classmethod
    def from_environment(cls) -> "GitHubPullRequestProvider":
        token = os.getenv("GITHUB_TOKEN")
        if not token: raise RuntimeError("GITHUB_TOKEN não configurado")
        return cls(token=token)

    def _request(self, method: str, path: str, payload: dict | None = None):
        body = json.dumps(payload).encode() if payload is not None else None
        request = Request(f"{self.api_base}{path}", data=body, method=method, headers={
            "Authorization": f"Bearer {self.token}", "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28", "Content-Type": "application/json"})
        with urlopen(request, timeout=30) as response:
            payload = response.read()
            return json.loads(payload) if payload else {}

    def create_branch(self, owner: str, repo: str, branch: str, sha: str) -> dict:
        if sha in {"HEAD", "main", "master"}:
            sha = self._request("GET", f"/repos/{owner}/{repo}/git/ref/heads/{sha}")["object"]["sha"]
        return self._request("POST", f"/repos/{owner}/{repo}/git/refs", {"ref": f"refs/heads/{branch}", "sha": sha})

    def create_commit(self, owner: str, repo: str, branch: str, message: str, files: dict[str, str]) -> dict:
        reference = self._request("GET", f"/repos/{owner}/{repo}/git/ref/heads/{branch}")
        parent_sha = reference["object"]["sha"]
        parent_commit = self._request("GET", f"/repos/{owner}/{repo}/git/commits/{parent_sha}")
        blobs = []
        for path, content in files.items():
            blob = self._request("POST", f"/repos/{owner}/{repo}/git/blobs", {"content": content, "encoding": "utf-8"})
            blobs.append({"path": path, "mode": "100644", "type": "blob", "sha": blob["sha"]})
        tree = self._request("POST", f"/repos/{owner}/{repo}/git/trees", {"base_tree": parent_commit["tree"]["sha"], "tree": blobs})
        commit = self._request("POST", f"/repos/{owner}/{repo}/git/commits", {"message": message, "tree": tree["sha"], "parents": [parent_sha]})
        return self._request("PATCH", f"/repos/{owner}/{repo}/git/refs/heads/{branch}", {"sha": commit["sha"]})

    def open_pull_request(self, owner: str, repo: str, head: str, base: str, title: str, body: str) -> dict:
        return self._request("POST", f"/repos/{owner}/{repo}/pulls", {"title": title, "body": body, "head": head, "base": base})

    def branch_ci_result(self, repository: str, branch: str) -> dict:
        runs = self._request("GET", f"/repos/{repository}/actions/runs?{urlencode({'branch': branch, 'per_page': '20'})}").get("workflow_runs", [])
        if not runs: return {"completed": False, "success": False, "reason": "no_run_yet", "sonar": []}
        latest = runs[0]
        if latest.get("status") != "completed": return {"completed": False, "success": False, "sonar": []}
        return {"completed": True, "success": latest.get("conclusion") == "success", "sonar": []}

    def delete_branch(self, owner: str, repo: str, branch: str) -> dict:
        return self._request("DELETE", f"/repos/{owner}/{repo}/git/refs/heads/{branch}")
