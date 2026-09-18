from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
import hashlib
from typing import Optional

class InvalidTransition(ValueError): pass

class PendingStatus(str, Enum):
    NOT_FIXED = "não_corrigida"
    SKIPPED = "skipped"
    IN_VALIDATION = "em_validacao"
    WAITING_MERGE = "aguardando_merge"
    FIXED = "corrigida"
    def transition_to(self, target: "PendingStatus") -> "PendingStatus":
        allowed = {
            self.NOT_FIXED: {self.SKIPPED, self.IN_VALIDATION, self.WAITING_MERGE},
            self.IN_VALIDATION: {self.WAITING_MERGE, self.NOT_FIXED},
            self.WAITING_MERGE: {self.FIXED, self.NOT_FIXED},
            self.SKIPPED: set(), self.FIXED: set(),
        }
        if target not in allowed[self]:
            raise InvalidTransition(f"{self.value} -> {target.value} não permitida")
        return target

class FindingOrigin(str, Enum):
    CI = "ci"
    SONAR = "sonar"

@dataclass(frozen=True)
class Finding:
    origin: FindingOrigin
    category: Optional[str]
    path: str
    test_name: Optional[str] = None
    failure_type: Optional[str] = None
    sonar_key: Optional[str] = None

class Correlation:
    @staticmethod
    def sonar(native_key: str) -> str:
        if not native_key: raise ValueError("chave Sonar obrigatória")
        return f"sonar:{native_key}"
    @staticmethod
    def ci(path: str, test_name: str, failure_type: str) -> str:
        raw = "|".join((path, test_name, failure_type)).encode()
        return f"ci:{hashlib.sha256(raw).hexdigest()}"
    @staticmethod
    def for_finding(finding: Finding) -> str:
        return Correlation.sonar(finding.sonar_key) if finding.origin == FindingOrigin.SONAR else Correlation.ci(finding.path, finding.test_name or '', finding.failure_type or '')

@dataclass(frozen=True)
class ScopeAxis:
    allowlist: set[str] = field(default_factory=set)
    denylist: set[str] = field(default_factory=set)
    def matches(self, value: Optional[str]) -> bool:
        if value is None: return False
        if any(value == x or value.startswith(x) for x in self.denylist): return False
        return not self.allowlist or any(value == x or value.startswith(x) for x in self.allowlist)

@dataclass(frozen=True)
class ScopePolicy:
    category: ScopeAxis
    path: ScopeAxis
    origin: ScopeAxis
    combination: str = "AND"
    @staticmethod
    def default() -> "ScopePolicy":
        return ScopePolicy(ScopeAxis(), ScopeAxis(), ScopeAxis(allowlist={"ci", "sonar"}), "AND")
    def to_dict(self):
        def axis(a): return {"allowlist": sorted(a.allowlist), "denylist": sorted(a.denylist)}
        return {"category": axis(self.category), "path": axis(self.path), "origin": axis(self.origin), "combination": self.combination}
    @staticmethod
    def from_dict(data):
        def axis(v): return ScopeAxis(set(v.get("allowlist", [])), set(v.get("denylist", [])))
        if data.get("combination") not in {"AND", "OR"}: raise ValueError("combination deve ser AND ou OR")
        return ScopePolicy(axis(data["category"]), axis(data["path"]), axis(data["origin"]), data["combination"])

class ScopeEngine:
    def __init__(self, policy: ScopePolicy): self.policy = policy
    def allows(self, finding: Finding) -> bool:
        values = [self.policy.category.matches(finding.category), self.policy.path.matches(finding.path), self.policy.origin.matches(finding.origin.value)]
        return all(values) if self.policy.combination == "AND" else any(values)

class ReprocessingGuard:
    def __init__(self, waiting_correlations: set[str]): self.waiting_correlations = waiting_correlations
    def is_blocked(self, finding: Finding) -> bool: return Correlation.for_finding(finding) in self.waiting_correlations
