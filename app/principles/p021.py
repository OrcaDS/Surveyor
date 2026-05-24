"""
app/principles/p021.py

PRINCIPLE: P021 — Aural vs. Visual Mode Differences
SOURCE: Tourangeau et al. — The Psychology of Survey Response, Ch. 10
        Dillman — Mail and Internet Surveys, Ch. 6
OPERATIONALIZABILITY: Medium
CONFIDENCE: Medium

WHAT THIS RULE CHECKS:
    Items designed for visual presentation may fail in aural (phone/audio)
    administration mode, and vice versa.

    SIGNAL 1 — Items exceeding aural working memory capacity (ITEM-LEVEL):
        Items longer than 25 words are difficult to process aurally.
        Respondents cannot re-read and must hold the entire item in
        working memory while formulating a response.
        NOTE: Threshold raised to 25 words (from 20) to avoid overlap
        with P007 which already flags items over 20 words for satisficing.

    SIGNAL 2 — Scale requires visual reference (INSTRUMENT-LEVEL):
        Scales with 5+ non-intuitive labels require visual reference.
        This is a CONSTANT across all items and is NOT checked here —
        it belongs to an instrument-level rule. Checking it per item
        would fire on every item of any standard Likert survey.

    SIGNAL 3 — Visual formatting dependency (ITEM-LEVEL):
        Items referencing visual elements that cannot be conveyed aurally.

BOUNDARY WITH P007:
    P007 flags items over 20 words for satisficing risk.
    P021 flags items over 25 words for aural memory risk specifically.
    Different thresholds, different failure modes, can co-occur.

SEVERITY:
    Long item (aural memory risk only)          -> 0.30
    Visual formatting dependency only           -> 0.60
    Long item + visual formatting dependency    -> 0.65

PROXY NOTE:
    Scale visual dependency (5+ options) is a known aural risk but
    is constant across all items in a uniform-scale survey. It is
    intentionally excluded from item-level detection to avoid
    firing on every item. Future instrument-level P021 extension
    should handle this at survey level.
"""

import re
from app.principles.base_rule import BaseRule, Violation


class P021(BaseRule):

    id = "P021"
    description = (
        "Detects items that may fail in aural survey administration "
        "due to excessive length or visual formatting dependency."
    )

    # Raised from 20 to 25 to avoid overlap with P007
    AURAL_WORD_LIMIT = 25

    VISUAL_FORMAT_SIGNALS = [
        r"\bsee (table|figure|chart|grid|matrix)\b",
        r"\brefer to\b",
        r"\bas shown\b",
        r"\brank the following\b",
        r"\bplace an x\b",
        r"\bdrag and drop\b",
    ]

    def evaluate(self, item: dict) -> Violation | None:
        text = self._get_text(item).lower()
        word_count = item.get("word_count", len(text.split()))

        signals = []

        # Signal 1: Exceeds aural working memory (item-level only)
        if word_count > self.AURAL_WORD_LIMIT:
            signals.append(
                f"item length ({word_count} words) exceeds aural "
                f"working memory limit ({self.AURAL_WORD_LIMIT} words) — "
                f"respondents cannot re-read in phone/audio mode"
            )

        # Signal 3: Visual formatting dependency (item-level only)
        visual_hits = [
            p for p in self.VISUAL_FORMAT_SIGNALS
            if re.search(p, text)
        ]
        if visual_hits:
            signals.append(
                "visual formatting dependency detected — "
                "item cannot be administered aurally"
            )

        if not signals:
            return None

        if any("visual formatting" in s for s in signals) and len(signals) > 1:
            severity = 0.65
        elif any("visual formatting" in s for s in signals):
            severity = 0.60
        else:
            severity = 0.30

        return Violation(
            principle=self.id,
            severity=round(severity, 2),
            evidence=(
                "Aural administration risk detected. "
                "Signal(s): " + " | ".join(signals)
            )
        )