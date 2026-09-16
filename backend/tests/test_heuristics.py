from backend.app import heuristics


def test_flags_uncapped_liability_as_high_severity():
    flags, severity, weight = heuristics.evaluate(
        "The Vendor shall have unlimited liability for any breach of this Agreement."
    )
    assert "uncapped_liability" in flags
    assert severity == "high"
    assert weight >= 0.7


def test_benign_clause_has_no_flags():
    flags, severity, weight = heuristics.evaluate(
        "This Agreement shall be governed by the laws of the State of Delaware."
    )
    assert flags == []
    assert severity == "none"
    assert weight == 0.0


def test_multiple_flags_take_max_severity():
    flags, severity, _ = heuristics.evaluate(
        "This Agreement shall automatically renew and may be terminated by "
        "either party for any reason, in the terminating party's sole discretion."
    )
    assert "automatic_renewal" in flags
    assert "unilateral_termination" in flags
    assert "sole_discretion" in flags
    assert severity == "moderate"
