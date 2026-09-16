"""
Reconciles the semantic (embedding) signal and the heuristic (rule-based)
signal into one risk score + confidence. Disagreement between the two is
surfaced explicitly (signals_agree=False + a warning) rather than silently
resolved -- this is the "no silent fallbacks" requirement in practice.
"""
from dataclasses import dataclass

SEMANTIC_WEIGHT = 0.6
HEURISTIC_WEIGHT = 0.4

# Similarity threshold above which we consider the semantic engine to have
# found a meaningful match at all.
SEMANTIC_MATCH_THRESHOLD = 0.55


@dataclass
class ConsensusResult:
    risk_score: float          # 0-1 blended score
    risk_category: str         # low | moderate | high
    confidence: float          # 0-1, higher when signals agree
    quality_score: float       # 0-1, reflects strength of underlying evidence
    signals_agree: bool
    warnings: list[str]


def _severity_to_score(severity: str) -> float:
    return {"none": 0.0, "low": 0.3, "moderate": 0.6, "high": 0.9}[severity]


def _score_to_category(score: float) -> str:
    if score >= 0.7:
        return "high"
    if score >= 0.4:
        return "moderate"
    return "low"


def reconcile(
    semantic_category: str | None,
    semantic_similarity: float,
    heuristic_flags: list[str],
    heuristic_severity: str,
) -> ConsensusResult:
    warnings: list[str] = []

    semantic_found_risk = (
        semantic_category is not None and semantic_similarity >= SEMANTIC_MATCH_THRESHOLD
    )
    heuristic_found_risk = heuristic_severity != "none"

    semantic_score = semantic_similarity if semantic_found_risk else 0.0
    heuristic_score = _severity_to_score(heuristic_severity)

    blended = SEMANTIC_WEIGHT * semantic_score + HEURISTIC_WEIGHT * heuristic_score
    risk_category = _score_to_category(blended)

    signals_agree = semantic_found_risk == heuristic_found_risk

    if signals_agree:
        confidence = 0.85 + 0.15 * min(semantic_similarity, 1.0)
        quality_score = 0.9
    else:
        confidence = 0.5
        quality_score = 0.6
        warnings.append(
            "semantic and heuristic signals disagree on whether this clause "
            "is risky -- manual review recommended"
        )

    confidence = round(min(confidence, 1.0), 3)
    quality_score = round(quality_score, 3)
    blended = round(blended, 3)

    return ConsensusResult(
        risk_score=blended,
        risk_category=risk_category,
        confidence=confidence,
        quality_score=quality_score,
        signals_agree=signals_agree,
        warnings=warnings,
    )
