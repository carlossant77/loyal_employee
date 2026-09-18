import pytest
from app.persistence import TursoStore


def test_production_store_requires_turso_configuration(monkeypatch):
    monkeypatch.delenv("TURSO_DATABASE_URL", raising=False)
    monkeypatch.delenv("TURSO_AUTH_TOKEN", raising=False)
    with pytest.raises(RuntimeError, match="TURSO_DATABASE_URL"):
        TursoStore.from_environment()
