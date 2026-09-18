from __future__ import annotations
from abc import ABC, abstractmethod
import json
import os
from typing import Any
from urllib.request import Request, urlopen

class LeaderProvider(ABC):
    @abstractmethod
    def propose_fix(self, finding: dict[str, Any]) -> dict[str, Any]: ...

class ReviewerProvider(ABC):
    @abstractmethod
    def review(self, report: dict[str, Any], verification: dict[str, Any]) -> dict[str, Any]: ...

class StubLeader(LeaderProvider):
    def propose_fix(self, finding): return {"accepted": False, "pull_request": None, "report": {"finding": finding}, "reason": "stub: correção real não implementada"}
class StubReviewer(ReviewerProvider):
    def review(self, report, verification): return {"accepted": False, "pull_request": None, "reason": "stub: revisão real não implementada"}

class GroqLeader(LeaderProvider):
    model = "llama-3.1-8b-instant"
    def __init__(self, api_key: str): self.api_key = api_key
    @classmethod
    def from_environment(cls):
        key = os.getenv("GROQ_API_KEY")
        if not key: raise RuntimeError("GROQ_API_KEY não configurada")
        return cls(key)
    def propose_fix(self, finding):
        prompt = "Return JSON with accepted:boolean, patch:object mapping file paths to complete contents, report:string. Propose a minimal isolated fix for this finding: " + json.dumps(finding, ensure_ascii=False)
        request = Request("https://api.groq.com/openai/v1/chat/completions", data=json.dumps({"model":self.model,"temperature":0,"response_format":{"type":"json_object"},"messages":[{"role":"user","content":prompt}]}).encode(), method="POST", headers={"Authorization":f"Bearer {self.api_key}","Content-Type":"application/json"})
        with urlopen(request, timeout=90) as response: return json.loads(json.loads(response.read())["choices"][0]["message"]["content"])

class GoogleReviewer(ReviewerProvider):
    model = "gemini-3.5-flash-lite"
    def __init__(self, api_key: str): self.api_key = api_key
    @classmethod
    def from_environment(cls):
        key = os.getenv("GOOGLE_AI_API_KEY")
        if not key: raise RuntimeError("GOOGLE_AI_API_KEY não configurada")
        return cls(key)
    def review(self, report, verification):
        prompt = "Return JSON with accepted:boolean and reason:string. Adversarially review whether this patch is validated. Report: " + json.dumps(report, ensure_ascii=False) + " Verification: " + json.dumps(verification, ensure_ascii=False)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        body = {"contents":[{"parts":[{"text":prompt}]}],"generationConfig":{"responseMimeType":"application/json"}}
        with urlopen(Request(url, data=json.dumps(body).encode(), method="POST", headers={"Content-Type":"application/json"}), timeout=90) as response:
            return json.loads(json.loads(response.read())["candidates"][0]["content"]["parts"][0]["text"])
