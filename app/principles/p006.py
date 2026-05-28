"""
app/principles/p006.py

PRINCIPLE: P006 — Acquiescence Bias (Yea-Saying)
SOURCE: Tourangeau, Rips & Rasinski — The Psychology of Survey Response, Ch. 8
        Fowler — Survey Research Methods, Ch. 6, p. 88-89
OPERATIONALIZABILITY: High
CONFIDENCE: High

WHAT THIS RULE CHECKS:
    Acquiescence bias (yea-saying) is the tendency for respondents to agree
    with survey items regardless of their actual beliefs, especially when:
        (a) all items are positively worded (no reverse-scored items), and
        (b) the response format is agree/disagree or a frequency scale

    This is an INSTRUMENT-LEVEL phenomenon.
    A single positively-worded item is not a violation.
    The violation is the ABSENCE of negatively-worded or reverse-scored items
    across the full instrument — which eliminates the ability to detect or
    correct for yea-saying in the data.

DETECTION STRATEGY:

    STEP 1 — Suppress idiomatic and subordinate-clause negation
        Not all negation words reverse item polarity. Suppress:
            - Idiomatic phrases: "no matter", "no longer", "not only"
            - Subordinate negation describing OTHERS: "who do not", "that others do not"
            - "without" used as a preposition modifying a clause, not the main claim

    STEP 2 — Count items with MAIN-CLAUSE negation only
        Only flag an item as negatively worded if negation appears in
        the respondent's OWN main clause — reversing their own claim.

    STEP 3 — Calculate positive polarity ratio
        ratio = positive_count / total_items
        If ratio >= 0.95 -> flag acquiescence risk

    STEP 4 — Check for reverse-scored item markers
        Explicit researcher-added reverse-scoring indicators.
        If none found -> compound the severity.

SEVERITY:
    ratio >= 0.95, reverse items present -> 0.55
    ratio >= 0.95, no reverse items      -> 0.80
    ratio = 1.00 (all positive)          -> 0.90

BOUNDARY WITH P005:
    P005 = item-level social self-presentation pressure
    P006 = instrument-level uniform polarity pattern
    P005 fires per item. P006 fires once on the full instrument.
    Both produce upward response bias but from different mechanisms:
        P005 fix: rewrite individual item stems
        P006 fix: add reverse-scored items to the instrument

BOUNDARY WITH P013:
    P013 = mixed scale direction is a problem
    P006 = missing polarity reversal is a problem
    Adjacent but non-overlapping.

PROXY NOTE:
    This rule detects MAIN-CLAUSE negation as a proxy for negative polarity.
    Items that are semantically negative but syntactically positive
    will not be detected. Explicit reverse-scoring markers are the most
    reliable signal — encourage researchers to annotate them.
"""

import re
from app.principles.base_rule import BaseRule, InstrumentViolation
from app.principles.signals import Signal, SignalType

class P006(BaseRule):

    id = "P006"
    description = (
        "Detects instrument-level acquiescence bias risk from uniform "
        "positive item polarity with no reverse-scored items."
    )

    POSITIVE_POLARITY_THRESHOLD = 0.95

    # ------------------------------------------------------------------
    # IDIOMATIC SUPPRESSIONS
    # Replace these before checking for negation so they don't trigger.
    # ------------------------------------------------------------------
    IDIOMATIC_SUPPRESSIONS = [
        "no matter",
        "not only",
        "no longer",
        "not necessarily",
        "not just",
        "not always",
        "not merely",
    ]

    # ------------------------------------------------------------------
    # SUBORDINATE NEGATION PATTERNS
    # Negation describing others, not the respondent's own claim.
    # Suppressed before polarity check.
    # ------------------------------------------------------------------
    SUBORDINATE_NEGATION_PATTERNS = [
        r"who do not\b",
        r"who does not\b",
        r"who did not\b",
        r"that others do not\b",
        r"that others in the organization do not\b",
        r"if he or she is not\b",
        r"if they do not\b",
        r"without the prospect\b",
        r"without external\b",
        r"if .{0,30} do not\b",
        r"if .{0,30} does not\b",
    ]

    # ------------------------------------------------------------------
    # MAIN-CLAUSE NEGATION SIGNALS
    # Only these count as genuine polarity reversal in the respondent's claim.
    # ------------------------------------------------------------------
    MAIN_CLAUSE_NEGATION = [
        r"\bi do not\b",
        r"\bi don't\b",
        r"\bi cannot\b",
        r"\bi can't\b",
        r"\bi would not\b",
        r"\bi never\b",
        r"\bi am not\b",
        r"\bi have not\b",
        r"\bi will not\b",
        r"\bi won't\b",
        r"\bi neither\b",
        r"\bi fail\b",
        r"\bi am unable\b",
    ]

    # ------------------------------------------------------------------
    # EXPLICIT REVERSE-SCORE MARKERS
    # ------------------------------------------------------------------
    REVERSE_SCORE_MARKERS = [
        r"\(r\)",
        r"\[r\]",
        r"\breverse\b",
        r"\breverse-scored\b",
        r"\breverse scored\b",
    ]

    def is_instrument_level(self) -> bool:
        return True

    def evaluate_instrument(self, items: list) -> list | None:
        """
        Evaluate the full item set for acquiescence bias risk.

        Args:
            items (list): Full list of item dicts from SurveyParser.

        Returns:
            list[InstrumentViolation] if acquiescence risk detected, else None.
        """
        if not items:
            return None

        total = len(items)
        negative_items = []
        reverse_scored_items = []

        for item in items:
            text = self._get_text(item).lower()
            item_id = item.get("item_id")

            # Step 1 — Suppress idiomatic phrases
            scrubbed = text
            for phrase in self.IDIOMATIC_SUPPRESSIONS:
                scrubbed = scrubbed.replace(phrase, "[IDIOM]")

            # Step 2 — Suppress subordinate-clause negation
            for pattern in self.SUBORDINATE_NEGATION_PATTERNS:
                scrubbed = re.sub(pattern, "[SUBORD]", scrubbed)

            # Step 3 — Check for MAIN-CLAUSE negation only
            has_main_negation = any(
                re.search(pattern, scrubbed)
                for pattern in self.MAIN_CLAUSE_NEGATION
            )

            if has_main_negation:
                negative_items.append(item_id)

            # Step 4 — Check for explicit reverse-score markers
            has_reverse_marker = any(
                re.search(pattern, text)
                for pattern in self.REVERSE_SCORE_MARKERS
            )

            if has_reverse_marker:
                reverse_scored_items.append(item_id)

        positive_count = total - len(negative_items)
        positive_ratio = positive_count / total

        if positive_ratio < self.POSITIVE_POLARITY_THRESHOLD:
            return None

        # Determine severity
        if positive_ratio == 1.0:
            severity = 0.90
        elif reverse_scored_items:
            severity = 0.55
        else:
            severity = 0.80

        evidence = (
            f"Acquiescence bias risk detected. "
            f"{positive_count}/{total} items ({positive_ratio:.0%}) are "
            f"positively worded with no main-clause negation. "
        )

        if not reverse_scored_items:
            evidence += (
                "No reverse-scored items found. "
                "Yea-saying cannot be detected or corrected in the data. "
                "Recommend adding reverse-scored items (minimum 20-30% of instrument)."
            )
        else:
            evidence += (
                f"Reverse-scored items found: {reverse_scored_items}. "
                "However, positive polarity ratio remains above threshold."
            )

        # Build signal
        if positive_ratio == 1.0:
            signal_type = SignalType.ALL_POSITIVE_POLARITY
            signal_description = (
                f"All {total} items ({positive_ratio:.0%}) are positively "
                f"worded — no main-clause negation detected anywhere in "
                f"the instrument."
            )
            confidence = 0.95
        else:
            signal_type = SignalType.HIGH_POSITIVE_POLARITY
            signal_description = (
                f"{positive_count}/{total} items ({positive_ratio:.0%}) are "
                f"positively worded — above the "
                f"{self.POSITIVE_POLARITY_THRESHOLD:.0%} "
                f"acquiescence risk threshold."
            )
            confidence = 0.85

        signal = Signal(
            type=signal_type,
            description=signal_description,
            terms=[],
            confidence=confidence,
            metadata={
                "positive_count": positive_count,
                "total_items": total,
                "positive_ratio": round(positive_ratio, 3),
                "reverse_scored_items": reverse_scored_items,
                "negative_items": negative_items,
            }
        )

        return [
            InstrumentViolation(
                principle=self.id,
                severity=round(severity, 2),
                evidence=evidence,
                affected_items=list(range(1, total + 1)),
                signals=[signal]
            )
        ]

    def evaluate(self, item: dict):
        raise NotImplementedError(
            "P006 is an instrument-level rule. "
            "Call evaluate_instrument(items) with the full item list."
        )