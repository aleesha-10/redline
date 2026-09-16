import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException

from . import consensus, db, heuristics
from .config import settings
from .embeddings import IndexNotBuiltError, get_semantic_engine
from .schemas import (
    ApiMeta,
    ClauseRiskData,
    ClauseRiskRequest,
    ClauseRiskResponse,
    Freshness,
    HeuristicResult,
    License,
    ProvenanceItem,
    RateLimit,
    ResponseMeta,
    SemanticResult,
    Trust,
)
from .ttl_worker import start_scheduler, stop_scheduler

# Data is static (CUAD + heuristic rules don't change at request time), so
# "age" is measured from when this process loaded the index, and TTL is
# generous -- freshness here is about the corpus/rules, not live polling.
_INDEX_LOADED_AT = datetime.now(timezone.utc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()
    yield
    stop_scheduler()
    await db.close_pool()


app = FastAPI(title="Redline", version=settings.VERSION, lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/v1/legal/contract/risk", response_model=ClauseRiskResponse)
async def check_clause_risk(payload: ClauseRiskRequest):
    start = time.perf_counter()
    request_id = f"req_{uuid.uuid4().hex[:20]}"
    warnings: list[str] = []

    # --- Semantic signal ---------------------------------------------
    try:
        engine = get_semantic_engine()
        semantic_category, semantic_similarity, examples = engine.score(payload.clause)
    except IndexNotBuiltError as e:
        # No silent fallback: a missing/broken semantic engine is a real,
        # explicit failure, not a degraded-but-hidden result.
        raise HTTPException(status_code=503, detail=str(e)) from e

    # --- Heuristic signal ----------------------------------------------
    flags, heuristic_severity, _ = heuristics.evaluate(payload.clause)

    # --- Consensus -------------------------------------------------------
    result = consensus.reconcile(
        semantic_category=semantic_category,
        semantic_similarity=semantic_similarity,
        heuristic_flags=flags,
        heuristic_severity=heuristic_severity,
    )
    warnings.extend(result.warnings)

    # --- Persist (best-effort logging; failure here must not mask the
    #     computed result, but also must not be silently swallowed) -----
    try:
        raw_id = await db.insert_raw_clause(payload.clause, payload.context)
        await db.insert_consensus_result(
            raw_id,
            {
                "risk_score": result.risk_score,
                "risk_category": result.risk_category,
                "semantic_category": semantic_category,
                "semantic_similarity": semantic_similarity,
                "heuristic_flags": flags,
                "heuristic_severity": heuristic_severity,
                "confidence": result.confidence,
                "signals_agree": result.signals_agree,
            },
        )
    except Exception as e:  # noqa: BLE001
        warnings.append(f"result computed but persistence failed: {e}")

    latency_ms = int((time.perf_counter() - start) * 1000)
    now = datetime.now(timezone.utc)
    age_seconds = int((now - _INDEX_LOADED_AT).total_seconds())

    response = ClauseRiskResponse(
        data=ClauseRiskData(
            clause=payload.clause,
            risk_score=result.risk_score,
            risk_category=result.risk_category,
            semantic=SemanticResult(
                matched_category=semantic_category,
                similarity=round(semantic_similarity, 3),
                nearest_examples=examples,
            ),
            heuristic=HeuristicResult(flags=flags, severity=heuristic_severity),
            signals_agree=result.signals_agree,
        ),
        meta=ResponseMeta(
            request_id=request_id,
            product_id=settings.PRODUCT_ID,
            version=settings.VERSION,
            served_at=now.isoformat(),
            source_last_updated_at=_INDEX_LOADED_AT.isoformat(),
            freshness=Freshness(
                age_seconds=age_seconds,
                ttl_seconds=settings.TTL_SECONDS,
                stale=age_seconds > settings.TTL_SECONDS,
            ),
            provenance=[
                ProvenanceItem(
                    source_id="CUAD-v1",
                    publisher="Atticus Project (CUAD dataset)",
                    retrieved_at=_INDEX_LOADED_AT.isoformat(),
                ),
                ProvenanceItem(
                    source_id="REDLINE-HEURISTICS-v1",
                    publisher="Redline internal rule set",
                    retrieved_at=_INDEX_LOADED_AT.isoformat(),
                ),
            ],
            trust=Trust(
                confidence=result.confidence,
                quality_score=result.quality_score,
                verified=result.signals_agree,
            ),
            license=License(),
            api=ApiMeta(
                latency_ms=latency_ms,
                rate_limit=RateLimit(limit=100, window_seconds=60),
            ),
            warnings=warnings,
        ),
    )
    return response
