"""
app/principles/p001.py

PRINCIPLE: P001 — The CASM Four-Stage Response Process Model
SOURCE: Tourangeau, Rips & Rasinski — The Psychology of Survey Response, Ch. 1
OPERATIONALIZABILITY: Medium
CONFIDENCE: High

WHAT THIS RULE CHECKS:
    The CASM model says respondents pass through four stages:
        1. Comprehension  — can they understand the question?
        2. Retrieval      — can they recall the relevant information?
        3. Judgment       — can they form a meaningful estimate?
        4. Response       — do the answer options fit their judgment?

    This rule detects signals that one or more of these stages will fail:

    STAGE 1 FAILURE — Comprehension:
        Abstract behavioral nouns with no definition in the item text.
        e.g. "physical activity", "social engagement", "effective leadership"

    STAGE 2 FAILURE — Retrieval:
        Vague frequency adverbs with no numerical anchor.
        e.g. "often", "usually", "sometimes", "rarely"
        NOTE: These words also appear in Likert scale LABELS (Always/Often/etc.)
        We only flag them when they appear in the ITEM TEXT itself, not in the scale.

    STAGE 3 FAILURE — Judgment:
        Items that ask the respondent to make an impossible or undefined judgment.
        Signal: highly abstract evaluative targets with no measurable referent.
        e.g. "total development", "complete knowledge", "overall effectiveness"

    STAGE 4 FAILURE — Response:
        Detected by P008 (Scale Anchor Calibration) — not this rule's responsibility.

SEVERITY LOGIC:
    Each stage failure detected adds to severity:
        1 failure  → 0.25
        2 failures → 0.50
        3 failures → 0.75
    Severity is capped at 0.75 for this rule alone (P025 handles composite scoring).
"""

import re
from app.principles.base_rule import BaseRule, Violation
from app.principles.signals import Signal, SignalType


class P001(BaseRule):

    id = "P001"
    description = (
        "Detects items likely to cause CASM stage failures: "
        "vague frequency terms, abstract undefined concepts, or unmeasurable judgments."
    )

    # ------------------------------------------------------------------
    # SIGNAL DICTIONARIES
    # Each list contains lowercase trigger terms for that failure type.
    # ------------------------------------------------------------------

    # Stage 2: Vague frequency adverbs in item TEXT (not scale labels)
    VAGUE_FREQUENCY_TERMS = [
        "often", "usually", "sometimes", "rarely", "frequently",
        "occasionally", "seldom", "regularly", "normally", "generally"
    ]

    # Stage 1: Abstract behavioral/organizational nouns with no definition
    ABSTRACT_CONCEPT_TERMS = [
        "physical activity", "social engagement", "healthy eating",
        "effective leadership", "good performance", "proper behavior",
        "total development", "overall effectiveness", "general welfare",
        "complete knowledge", "full compliance", "active participation",
        "positive relationship", "strong bond", "healthy competition",
        "better change", "desired actions", "desired goal",
        "strategic interest", "organizational objective"
    ]

    # Stage 3: Unmeasurable judgment targets
    UNMEASURABLE_JUDGMENT_TERMS = [
        "total development", "complete knowledge", "full understanding",
        "deep appreciation", "strong motivator", "superior knowledge",
        "elevated level", "complex process", "important factor",
        "important role", "better understanding"
    ]

    def evaluate(self, item: dict) -> Violation | None:
        """
        Check a single item for CASM stage failure signals.

        Args:
            item (dict): Parsed survey item from SurveyParser.

        Returns:
            Violation if one or more CASM stage failures detected, else None.
        """
        text = self._get_text(item).lower()

        signals = []

        # --- Stage 1: Comprehension failure ---
        abstract_hits = [
            term for term in self.ABSTRACT_CONCEPT_TERMS
            if term in text
        ]
        if abstract_hits:
            signals.append(
                Signal(
                    type=SignalType.ABSTRACT_CONCEPT,
                    description="Stage 1 (Comprehension): abstract undefined concept(s) detected",
                    terms=abstract_hits,
                    confidence=0.80,
                )
            )

        # --- Stage 2: Retrieval failure ---
        # Tokenize to avoid partial matches (e.g. "often" inside "softening")
        words = re.findall(r"\b\w+\b", text)

        freq_hits = [
            term for term in self.VAGUE_FREQUENCY_TERMS
            if term in words
        ]
        if freq_hits:
            signals.append(
                Signal(
                    type=SignalType.VAGUE_FREQUENCY_ADVERB,
                    description="Stage 2 (Retrieval): vague frequency term(s) in item text",
                    terms=freq_hits,
                    confidence=0.85,
                )
            )

        # --- Stage 3: Judgment failure ---
        # Exclude terms already reported in Stage 1 to avoid redundant evidence
        already_reported = set(abstract_hits)

        judgment_hits = [
            term for term in self.UNMEASURABLE_JUDGMENT_TERMS
            if term in text and term not in already_reported
        ]
        if judgment_hits:
            signals.append(
                Signal(
                    type=SignalType.UNMEASURABLE_JUDGMENT,
                    description="Stage 3 (Judgment): unmeasurable judgment target(s) detected",
                    terms=judgment_hits,
                    confidence=0.80,
                )
            )

        if not signals:
            return None

        # Severity scales with number of stage failures, capped at 0.75
        severity = min(len(signals) * 0.25, 0.75)

        # Evidence derived from signals — includes terms for human readability
        evidence = " | ".join(
            f"{s.description}: {', '.join(repr(t) for t in s.terms)}"
            if s.terms else s.description
            for s in signals
        )

        return Violation(
            principle=self.id,
            severity=round(severity, 2),
            evidence=evidence,
            signals=signals
        )