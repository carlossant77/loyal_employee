from __future__ import annotations
import json
import os
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen


def get(url: str, token: str | None = None) -> dict:
    headers = {"Accept": "application/vnd.github+json"}
    if token: headers["Authorization"] = f"Bearer {token}"
    request = Request(url, headers=headers)
    with urlopen(request, timeout=30) as response: return json.loads(response.read())


def main() -> None:
    repository = os.environ["GITHUB_REPOSITORY"]
    github_token = os.environ.get("GITHUB_TOKEN")
    findings: list[dict] = []
    runs = get(f"https://api.github.com/repos/{repository}/actions/runs?{urlencode({'status':'failure','per_page':'20'})}", github_token).get("workflow_runs", [])
    for run in runs:
        jobs = get(run["jobs_url"], github_token).get("jobs", [])
        for job in jobs:
            if job.get("conclusion") == "failure":
                findings.append({"origin":"ci", "category":None, "path":job.get("workflow_name") or ".github/workflows", "test_name":job.get("name") or "unknown-job", "failure_type":"workflow_failure"})
    sonar_token = os.environ.get("SONAR_TOKEN")
    sonar_host = os.environ.get("SONAR_HOST_URL")
    project_key = os.environ.get("SONAR_PROJECT_KEY")
    if sonar_token and sonar_host and project_key:
        query = urlencode({"componentKeys": project_key, "statuses":"OPEN", "ps":"500"})
        issues = get(f"{sonar_host.rstrip('/')}/api/issues/search?{query}", sonar_token).get("issues", [])
        for issue in issues:
            findings.append({"origin":"sonar", "category":issue.get("type", "code_smell").lower(), "path":issue.get("component", project_key), "sonar_key":issue["key"]})
    json.dump({"findings": findings}, sys.stdout)


if __name__ == "__main__": main()
