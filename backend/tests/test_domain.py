import pytest
from app.domain import (
    Finding, FindingOrigin, PendingStatus, ScopePolicy, ScopeAxis,
    ScopeEngine, Correlation, InvalidTransition, ReprocessingGuard
)


def ci_finding():
    return Finding(origin=FindingOrigin.CI, category=None, path="src/a.py",
                   test_name="test_a", failure_type="AssertionError")


def test_pending_state_machine_allows_documented_transitions():
    assert PendingStatus.NOT_FIXED.transition_to(PendingStatus.SKIPPED) == PendingStatus.SKIPPED
    assert PendingStatus.NOT_FIXED.transition_to(PendingStatus.WAITING_MERGE) == PendingStatus.WAITING_MERGE
    assert PendingStatus.WAITING_MERGE.transition_to(PendingStatus.FIXED) == PendingStatus.FIXED
    assert PendingStatus.WAITING_MERGE.transition_to(PendingStatus.NOT_FIXED) == PendingStatus.NOT_FIXED


def test_pending_state_machine_rejects_implicit_transitions():
    with pytest.raises(InvalidTransition):
        PendingStatus.SKIPPED.transition_to(PendingStatus.FIXED)
    with pytest.raises(InvalidTransition):
        PendingStatus.FIXED.transition_to(PendingStatus.NOT_FIXED)


def test_correlation_uses_sonar_native_key_and_stable_ci_fingerprint():
    assert Correlation.sonar("issue-123") == "sonar:issue-123"
    first = Correlation.ci("src/a.py", "test_a", "AssertionError")
    second = Correlation.ci("src/a.py", "test_a", "AssertionError")
    assert first == second
    assert first != Correlation.ci("src/a.py", "test_b", "AssertionError")
    assert first.startswith("ci:")


def test_scope_combines_axes_with_explicit_allowlist_and_denylist():
    policy = ScopePolicy(
        category=ScopeAxis(allowlist={"reliability"}, denylist=set()),
        path=ScopeAxis(allowlist={"src/"}, denylist={"src/generated/"}),
        origin=ScopeAxis(allowlist={"sonar"}, denylist=set()),
        combination="AND",
    )
    engine = ScopeEngine(policy)
    assert engine.allows(Finding(FindingOrigin.SONAR, "reliability", "src/a.py"))
    assert not engine.allows(Finding(FindingOrigin.SONAR, "reliability", "src/generated/a.py"))
    assert not engine.allows(Finding(FindingOrigin.CI, "reliability", "src/a.py"))
    assert not engine.allows(Finding(FindingOrigin.SONAR, "security", "src/a.py"))


def test_scope_or_combination_is_explicit_and_deterministic():
    policy = ScopePolicy(
        category=ScopeAxis(allowlist={"reliability"}, denylist=set()),
        path=ScopeAxis(allowlist={"src/"}, denylist=set()),
        origin=ScopeAxis(allowlist={"sonar"}, denylist=set()),
        combination="OR",
    )
    engine = ScopeEngine(policy)
    assert not engine.allows(Finding(FindingOrigin.CI, "security", "docs/a.md"))
    assert engine.allows(Finding(FindingOrigin.SONAR, "security", "docs/a.md"))


def test_waiting_merge_correlation_is_skipped_on_next_run():
    guard = ReprocessingGuard({"ci:" + Correlation.ci("src/a.py", "test_a", "AssertionError").split(":", 1)[1]})
    assert guard.is_blocked(ci_finding())
    assert not guard.is_blocked(Finding(FindingOrigin.CI, None, "src/b.py", "test_a", "AssertionError"))


def test_scope_policy_is_serializable_data_not_runtime_agent_decision():
    policy = ScopePolicy.default()
    data = policy.to_dict()
    restored = ScopePolicy.from_dict(data)
    assert restored == policy
    assert data["combination"] == "AND"


def test_default_scope_fails_safe_for_ci_findings_without_category():
    """CI findings have no Sonar category and stay skipped until explicitly configured."""
    assert not ScopeEngine(ScopePolicy.default()).allows(ci_finding())
