from typing import Any, Optional
from pydantic import BaseModel, Field


class ClauseRiskRequest(BaseModel):
    clause: str = Field(..., min_length=1, description="Raw contract clause text")
    context: Optional[dict[str, Any]] = Field(
        default=None, description="Optional metadata, e.g. contract type, jurisdiction"
    )


class SemanticResult(BaseModel):
    matched_category: Optional[str]
    similarity: float
    nearest_examples: list[str] = []


class HeuristicResult(BaseModel):
    flags: list[str]
    severity: str  # "none" | "low" | "moderate" | "high"


class Freshness(BaseModel):
    age_seconds: int
    ttl_seconds: int
    stale: bool


class ProvenanceItem(BaseModel):
    source_id: str
    publisher: str
    retrieved_at: str


class Trust(BaseModel):
    confidence: float
    quality_score: float
    verified: bool


class License(BaseModel):
    type: str = "research"
    usage: str = "agent_runtime"


class RateLimit(BaseModel):
    limit: int
    window_seconds: int


class ApiMeta(BaseModel):
    latency_ms: int
    rate_limit: RateLimit


class ResponseMeta(BaseModel):
    request_id: str
    product_id: str
    version: str
    served_at: str
    source_last_updated_at: str
    freshness: Freshness
    provenance: list[ProvenanceItem]
    trust: Trust
    license: License
    api: ApiMeta
    warnings: list[str] = []


class ClauseRiskData(BaseModel):
    clause: str
    risk_score: float
    risk_category: str  # "low" | "moderate" | "high"
    semantic: SemanticResult
    heuristic: HeuristicResult
    signals_agree: bool


class ClauseRiskResponse(BaseModel):
    data: ClauseRiskData
    meta: ResponseMeta
