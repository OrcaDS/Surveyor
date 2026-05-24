"""
app/principles/p014.py

PRINCIPLE: P014 — Open vs. Closed Question Trade-offs
SOURCE: Fowler — Survey Research Methods, Ch. 6, p. 92–95
OPERATIONALIZABILITY: Medium
CONFIDENCE: Medium

WHAT THIS RULE CHECKS:
    Whether the question format (open vs closed) matches the construct
    being measured.

    CLOSED questions force respondents into predefined categories.
    Appropriate when: construct space is known and bounded.
    Inappropriate when: response space is genuinely open-ended.

    OPEN questions allow free response.
    Appropriate when: exploring unknown response distributions.
    Inappropriate when: closed options would produce more reliable data.

DETECTION:
    SIGNAL 1 — Closed question on genuinely open construct:
        Items asking about specific opinions, explanations, or
        narratives that cannot be captured by a Likert scale.
        Detected by: "why", "how", "explain", "describe" stems
        paired with a closed response format.

    SIGNAL 2 — Opinion/belief items on frequency scale:
        Items measuring attitudes or beliefs rated on a frequency
        scale (Always/Never) rather than an agreement scale.
        Frequency scales are inappropriate for attitude items —
        "How often do you believe X?" is a category mismatch.

GATE:
    Items using agreement scales for attitude measurement are
    correctly formatted. Skip immediately.

SEVERITY:
    Open construct on closed format  -> 0.55
    Attitude on frequency scale      -> 0.40
"""

import re
from app.principles.base_rule import BaseRule, Violation


class P014(BaseRule):

    id = "P014"
    description = (
        "Detects mismatches between question format (open/closed) "
        "and the construct being measured."
    )

    # Stems suggesting open-ended response is needed
    OPEN_CONSTRUCT_STEMS = [
        r"\bwhy\b",
        r"\bexplain\b",
        r"\bdescribe\b",
        r"\bhow did you\b",
        r"\bwhat was\b",
        r"\btell us\b",
        r"\bin your own words\b",
        r"\bwhat do you think\b",
    ]

    # Attitude/belief verbs — inappropriate for frequency scale
    ATTITUDE_STEMS = [
        r"\bi believe\b",
        r"\bi think\b",
        r"\bi feel that\b",
        r"\bin my opinion\b",
        r"\bi am of the view\b",
    ]

    def evaluate(self, item: dict) -> Violation | None:
        text = self._get_text(item).lower()
        scale = item.get("scale", {})
        labels = scale.get("labels", {})
        label_values = [v.lower() for v in labels.values()]

        is_frequency_scale = any(
            "always" in l or "never" in l or "often" in l
            for l in label_values
        )
        is_agreement_scale = any(
            "agree" in l or "disagree" in l
            for l in label_values
        )

        # Gate: agreement scale used for attitude — correct format
        if is_agreement_scale:
            return None

        signals = []

        # Signal 1: Open construct on closed format
        open_hits = [
            p for p in self.OPEN_CONSTRUCT_STEMS
            if re.search(p, text)
        ]
        if open_hits:
            signals.append(
                f"open-ended construct stem detected "
                f"({[re.search(p, text).group() for p in open_hits]}) "
                f"paired with closed response format — "
                f"respondent's full answer cannot be captured"
            )

        # Signal 2: Attitude item on frequency scale
        attitude_hits = [
            p for p in self.ATTITUDE_STEMS
            if re.search(p, text)
        ]
        if attitude_hits and is_frequency_scale:
            signals.append(
                f"attitude/belief stem "
                f"({[re.search(p, text).group() for p in attitude_hits]}) "
                f"paired with frequency scale — "
                f"'how often do you believe X' is a format mismatch"
            )

        if not signals:
            return None

        severity = 0.55 if any("open-ended" in s for s in signals) else 0.40
        evidence = (
            "Question format mismatch detected. "
            "Signal(s): " + " | ".join(signals)
        )

        return Violation(
            principle=self.id,
            severity=round(severity, 2),
            evidence=evidence
        )