import re

# Each rule: (label, compiled pattern, severity weight 0-1)
RULES: list[tuple[str, re.Pattern, float]] = [
    ("uncapped_liability", re.compile(r"\bunlimited liability\b|\bwithout limit(ation)?\b", re.I), 0.9),
    ("sole_discretion", re.compile(r"\bsole( and absolute)? discretion\b", re.I), 0.5),
    ("unilateral_termination", re.compile(r"\bterminate.{0,30}\bwithout cause\b|\bfor any reason\b", re.I), 0.6),
    ("perpetual_obligation", re.compile(r"\bperpetual(ly)?\b|\bin perpetuity\b", re.I), 0.6),
    ("irrevocable", re.compile(r"\birrevocabl[ey]\b", re.I), 0.5),
    ("automatic_renewal", re.compile(r"\bautomatic(ally)? renew\b|\bauto[- ]renewal\b", re.I), 0.4),
    ("indemnification", re.compile(r"\bindemnif(y|ication)\b", re.I), 0.5),
    ("non_compete", re.compile(r"\bnon[- ]compete\b|\bnoncompetition\b", re.I), 0.5),
    ("exclusive_jurisdiction", re.compile(r"\bexclusive jurisdiction\b|\bwaiv(e|es|er) of jury trial\b", re.I), 0.3),
    ("assignment_restriction", re.compile(r"\bmay not assign\b|\bwithout prior written consent\b", re.I), 0.3),
]


def evaluate(clause: str) -> tuple[list[str], str, float]:
    """
    Scan a clause against the red-flag rule set.
    Returns (matched_flag_labels, severity_label, severity_score[0-1]).
    """
    matched = []
    max_weight = 0.0
    for label, pattern, weight in RULES:
        if pattern.search(clause):
            matched.append(label)
            max_weight = max(max_weight, weight)

    if not matched:
        severity = "none"
    elif max_weight >= 0.7:
        severity = "high"
    elif max_weight >= 0.4:
        severity = "moderate"
    else:
        severity = "low"

    return matched, severity, max_weight
