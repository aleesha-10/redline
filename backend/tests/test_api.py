import time

import numpy as np
import pytest

from backend.app import db, main
from backend.app.embeddings import IndexNotBuiltError


class _FakeSemanticEngine:
    """Deterministic stand-in for the real embedding engine in tests."""

    def score(self, clause: str, top_k: int = 3):
        return "Uncapped Liability", 0.82, ["example clause snippet"]


class _FailingSemanticEngine:
    def score(self, clause: str, top_k: int = 3):
        raise IndexNotBuiltError("index not built (simulated failure)")


@pytest.fixture(autouse=True)
def _stub_persistence(monkeypatch):
    """Avoid requiring a live Postgres instance for these tests."""

    async def _fake_insert_raw_clause(clause, context):
        return "00000000-0000-0000-0000-000000000000"

    async def _fake_insert_consensus_result(raw_id, result):
        return None

    monkeypatch.setattr(db, "insert_raw_clause", _fake_insert_raw_clause)
    monkeypatch.setattr(db, "insert_consensus_result", _fake_insert_consensus_result)


@pytest.mark.asyncio
async def test_health_endpoint_available(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_clause_risk_happy_path(client, monkeypatch):
    monkeypatch.setattr(main, "get_semantic_engine", lambda: _FakeSemanticEngine())

    resp = await client.post(
        "/v1/legal/contract/risk",
        json={"clause": "The Vendor shall have unlimited liability for any breach."},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["risk_category"] in {"low", "moderate", "high"}
    assert "confidence" in body["meta"]["trust"]
    assert body["meta"]["freshness"]["ttl_seconds"] > 0


@pytest.mark.asyncio
async def test_freshness_sla_fields_present_and_consistent(client, monkeypatch):
    monkeypatch.setattr(main, "get_semantic_engine", lambda: _FakeSemanticEngine())

    resp = await client.post("/v1/legal/contract/risk", json={"clause": "Sample clause."})
    freshness = resp.json()["meta"]["freshness"]
    # Freshness SLA: age_seconds must never exceed ttl_seconds without being
    # flagged stale.
    if freshness["age_seconds"] > freshness["ttl_seconds"]:
        assert freshness["stale"] is True
    else:
        assert freshness["stale"] is False


@pytest.mark.asyncio
async def test_p95_latency_under_200ms(client, monkeypatch):
    monkeypatch.setattr(main, "get_semantic_engine", lambda: _FakeSemanticEngine())

    latencies = []
    for _ in range(30):
        start = time.perf_counter()
        resp = await client.post("/v1/legal/contract/risk", json={"clause": "Sample clause."})
        latencies.append((time.perf_counter() - start) * 1000)
        assert resp.status_code == 200

    p95 = float(np.percentile(latencies, 95))
    assert p95 < 200, f"p95 latency {p95:.1f}ms exceeded 200ms SLA"


@pytest.mark.asyncio
async def test_failover_returns_explicit_error_not_silent_fallback(client, monkeypatch):
    """
    If the semantic engine is unavailable, the API must fail loudly (503
    with a clear detail message) rather than silently serving a
    heuristic-only result mislabeled as a full consensus result.
    """
    monkeypatch.setattr(main, "get_semantic_engine", lambda: _FailingSemanticEngine())

    resp = await client.post("/v1/legal/contract/risk", json={"clause": "Sample clause."})
    assert resp.status_code == 503
    assert "index not built" in resp.json()["detail"].lower()
