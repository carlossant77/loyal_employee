from __future__ import annotations
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from .domain import ScopePolicy, Finding, FindingOrigin, PendingStatus, ScopeEngine, Correlation, ReprocessingGuard
from .persistence import TursoStore
from .providers import LeaderProvider, ReviewerProvider, StubLeader, StubReviewer, GroqLeader, GoogleReviewer
from .github_provider import GitHubPullRequestProvider
from .services import ValidationOrchestrator
import os
from .auth import api_key_middleware

app = FastAPI(title="Agente CI/SonarQube API", version="0.1.0")
app.middleware("http")(api_key_middleware)
store = TursoStore.from_environment()
leader: LeaderProvider = GroqLeader.from_environment() if os.getenv("GROQ_API_KEY") else StubLeader()
reviewer: ReviewerProvider = GoogleReviewer.from_environment() if os.getenv("GOOGLE_AI_API_KEY") else StubReviewer()

class ScopeIn(BaseModel):
    category: dict = Field(default_factory=dict)
    path: dict = Field(default_factory=dict)
    origin: dict = Field(default_factory=dict)
    combination: str = "AND"
class FindingIn(BaseModel):
    origin: FindingOrigin
    category: str | None = None
    path: str
    test_name: str | None = None
    failure_type: str | None = None
    sonar_key: str | None = None
class JobIn(BaseModel):
    repository: str
    ref: str = "main"
    findings: list[FindingIn] = Field(default_factory=list)

def policy(): return ScopePolicy.from_dict(store.get_scope())

@app.get("/health")
def health(): return {"status": "ok"}
@app.get("/jobs")
def jobs(): return store.list_jobs()
@app.get("/findings")
def findings(status: str | None = None):
    if status and status not in {item.value for item in PendingStatus}: raise HTTPException(400, "status inválido")
    return store.list_findings(status)
@app.get("/scope")
def get_scope(): return store.get_scope()
@app.put("/scope")
def put_scope(payload: ScopeIn):
    try: store.set_scope(payload.model_dump())
    except ValueError as exc: raise HTTPException(422, str(exc)) from exc
    return store.get_scope()
@app.post("/jobs")
def create_job(payload: JobIn):
    job_id = str(uuid.uuid4())
    store.create_job(job_id, payload.repository, payload.ref, "completed", datetime.now(timezone.utc).isoformat())
    engine = ScopeEngine(policy())
    guard = ReprocessingGuard(store.waiting_correlations())
    inserted = 0
    for item in payload.findings:
        finding = Finding(**item.model_dump())
        if guard.is_blocked(finding): continue
        status = PendingStatus.NOT_FIXED.value if engine.allows(finding) else PendingStatus.SKIPPED.value
        store.add_finding(str(uuid.uuid4()), job_id, Correlation.for_finding(finding), item.origin.value, item.category, item.path, status, None)
        inserted += 1
    return {"job_id": job_id, "status": "completed", "findings_persisted": inserted}

@app.post("/findings/{finding_id}/process")
def process_finding(finding_id: str):
    try:
        github = GitHubPullRequestProvider.from_environment()
        return ValidationOrchestrator(store, leader, reviewer, github).process(finding_id)
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc
