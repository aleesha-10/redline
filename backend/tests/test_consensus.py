from backend.app import consensus


def test_both_signals_agree_on_high_risk():
    result = consensus.reconcile(
        semantic_category="Uncapped Liability",
        semantic_similarity=0.9,
        heuristic_flags=["uncapped_liability"],
        heuristic_severity="high",
    )
    assert result.risk_category == "high"
    assert result.signals_agree is True
    assert result.confidence > 0.8
    assert result.warnings == []


def test_both_signals_agree_on_low_risk():
    result = consensus.reconcile(
        semantic_category=None,
        semantic_similarity=0.1,
        heuristic_flags=[],
        heuristic_severity="none",
    )
    assert result.risk_category == "low"
    assert result.signals_agree is True


def test_signals_disagree_lowers_confidence_and_warns():
    result = consensus.reconcile(
        semantic_category="Non-Compete",
        semantic_similarity=0.8,
        heuristic_flags=[],
        heuristic_severity="none",
    )
    assert result.signals_agree is False
    assert result.confidence <= 0.5
    assert any("disagree" in w for w in result.warnings)


def test_risk_score_bounded_between_zero_and_one():
    result = consensus.reconcile(
        semantic_category="Uncapped Liability",
        semantic_similarity=1.0,
        heuristic_flags=["uncapped_liability"],
        heuristic_severity="high",
    )
    assert 0.0 <= result.risk_score <= 1.0
