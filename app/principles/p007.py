"""
app/principles/p007.py

PRINCIPLE: P007 — Satisficing
SOURCE: Tourangeau, Rips & Rasinski — The Psychology of Survey Response, Ch. 9
        Krosnick — Survey Research, Annual Review of Psychology, 1999
OPERATIONALIZABILITY: Medium
CONFIDENCE: Medium

WHAT THIS RULE CHECKS:
    Satisficing occurs when respondents abandon effortful processing and
    select a "good enough" answer rather than the most accurate one.
    This rule detects ITEM-LEVEL structural features that increase the
    probability of satisficing behavior:

    SIGNAL 1 — Excessive word count:
        Items longer than 25 words place high working memory demand
        on respondents. Fowler (2014) recommends items under 20 words.
        Threshold:
            20-25 words -> mild satisficing risk  (severity contribution: low)
            25+  words  -> high satisficing risk  (severity contribution: high)

    SIGNAL 2 — Embedded subordinate clauses:
        Multiple nested subclauses require recursive parsing that
        most respondents will shortcut. Detected by:
            - Multiple "that" / "which" / "who" / "where" connectors
            - "if...then" conditional structures
            - "because...therefore" causal chains

    SIGNAL 3 — Information integration demand:
        Items requiring the respondent to mentally hold and combine
        multiple propositions before selecting a response.
        Detected by high subordinate clause count relative to item length.

BOUNDARY WITH P001:
    P001 fires on specific linguistic signals of CASM stage failure.
    P007 fires on structural features (length, complexity) that make
    effortful processing unlikely to be completed at all.
    P001 = what is in the item causes failure
    P007 = how much is in the item causes abandonment

BOUNDARY WITH P020:
    P007 = item-level satisficing risk from individual item complexity
    P020 = instrument-level fatigue from total survey length
    P007 fires per item. P020 fires on the instrument as a whole.

SEVERITY:
    Word count signal only         -> 0.30
    Clause complexity signal only  -> 0.35
    Both signals                   -> 0.60
    All three signals              -> 0.75

PROXY NOTE:
    True satisficing detection requires behavioral data (response times,
    response patterns). This rule uses structural proxies only.
    A long, complex item does not guarantee satisficing —
    it raises the probability. All outputs should be treated as flags.
"""

import re
from app.principles.base_rule import BaseRule, Violation
from app.principles.signals import Signal, SignalType


class P007(BaseRule):

    id = "P007"
    description = (
        "Detects item-level structural features that increase satisficing risk: "
        "excessive length, embedded clauses, and information integration demand."
    )

    # Word count thresholds
    MILD_LENGTH_THRESHOLD = 20
    HIGH_LENGTH_THRESHOLD = 25

    # Subordinate clause connectors
    SUBORDINATE_CONNECTORS = [
        r"\bthat\b",
        r"\bwhich\b",
        r"\bwho\b",
        r"\bwhere\b",
        r"\bwhen\b",
        r"\bif\b",
        r"\bbecause\b",
        r"\balthough\b",
        r"\bwhile\b",
        r"\bsince\b",
        r"\bunless\b",
        r"\bwhereby\b",
    ]

    # High integration demand: conditional + causal chains in same item
    CONDITIONAL_PATTERNS = [r"\bif\b.{5,80}\bthen\b"]
    CAUSAL_PATTERNS = [r"\bbecause\b.{5,80}\b(therefore|thus|hence|so)\b"]

    def evaluate(self, item: dict) -> Violation | None:
        """
        Check a single item for satisficing risk signals.

        Args:
            item (dict): Parsed survey item from SurveyParser.

        Returns:
            Violation if satisficing risk signals detected, else None.
        """
        text = self._get_text(item)
        text_lower = text.lower()
        word_count = item.get("word_count", len(text.split()))

        signals = []

        # --- Signal 1: Excessive word count ---
        if word_count >= self.HIGH_LENGTH_THRESHOLD:
            signals.append(
                Signal(
                    type=SignalType.HIGH_WORD_COUNT,
                    description="high word count detected",
                    terms=[str(word_count)],
                    confidence=0.85,
                )
            )
        elif word_count >= self.MILD_LENGTH_THRESHOLD:
            signals.append(
                Signal(
                    type=SignalType.ELEVATED_WORD_COUNT,
                    description="elevated word count detected",
                    terms=[str(word_count)],
                    confidence=0.80,
                )
            )

        # --- Signal 2: Embedded subordinate clauses ---
        clause_count = sum(
            1 for pattern in self.SUBORDINATE_CONNECTORS
            if re.search(pattern, text_lower)
        )
        if clause_count >= 3:
            signals.append(
                Signal(
                    type=SignalType.HIGH_CLAUSE_DENSITY,
                    description="high subordinate clause density detected",
                    terms=[str(clause_count)],
                    confidence=0.85,
                )
            )

        # --- Signal 3: Information integration demand ---
        has_conditional = any(
            re.search(p, text_lower) for p in self.CONDITIONAL_PATTERNS
        )
        has_causal = any(
            re.search(p, text_lower) for p in self.CAUSAL_PATTERNS
        )

        if has_conditional or has_causal:
            chain_type = []
            terms = []

            if has_conditional:
                chain_type.append("conditional (if...then)")
                terms.append("if...then")

            if has_causal:
                chain_type.append("causal chain (because...therefore)")
                terms.append("because...therefore")

            signals.append(
                Signal(
                    type=SignalType.INTEGRATION_DEMAND,
                    description="information integration demand detected",
                    terms=terms,
                    confidence=0.85,
                )
            )

        if not signals:
            return None

        # Severity based on signal count
        severity_map = {1: 0.30, 2: 0.60}
        severity = severity_map.get(len(signals), 0.75)

        # Special adjustment preserved from original logic
        if len(signals) == 1 and signals[0].type == SignalType.HIGH_CLAUSE_DENSITY:
            severity = 0.35

        # Evidence derived from signals (with readable terms preserved)
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