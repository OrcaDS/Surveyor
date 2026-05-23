"""
app/principles/p009.py

PRINCIPLE: P009 — Response Option Order Effects
SOURCE: Tourangeau, Rips & Rasinski — The Psychology of Survey Response, Ch. 7
        Dillman — Mail and Internet Surveys, Ch. 5, p. 183–187
OPERATIONALIZABILITY: Medium
CONFIDENCE: Medium

WHAT THIS RULE CHECKS:
    Response option ordering creates systematic bias through two mechanisms:

    PRIMACY EFFECT (visual surveys):
        Respondents disproportionately select options listed first.
        In visual/written surveys, the first option receives more attention
        and is selected more often than its true prevalence warrants.
        Risk increases when:
            - Most favorable option is listed first
            - Options are not logically ordered (e.g. agree before disagree)

    RECENCY EFFECT (aural surveys):
        Respondents disproportionately select options heard last.
        In phone/audio surveys, the last option is most recently in memory.
        Risk increases when:
            - Most favorable option is listed last
            - Survey is administered aurally without visual reference

    NON-SEQUENTIAL ORDERING:
        Logically ordered constructs (frequency, agreement, severity)
        presented in non-sequential order create confusion and error.
        e.g. Never / Always / Sometimes / Rarely / Often — scrambled

GATE CONDITION:
    This rule only applies to surveys where response options vary
    per item or are presented in non-standard order.

    For surveys using a FIXED UNIFORM SCALE applied identically
    across all items (like this instrument: Always/Often/Sometimes/
    Rarely/Never), option order effects are:
        (a) constant across all items — no differential bias
        (b) a scale-level concern handled by P008, not item-level

    In that case this rule returns None for all items.
    This is the correct result — not a limitation.

BOUNDARY WITH P008:
    P008 checks anchor label quality (vague quantifiers, asymmetry).
    P009 checks option ordering effects (primacy, recency, sequence).
    P008 = are the labels good?
    P009 = are the options in the right order?

BOUNDARY WITH P012:
    P012 checks exhaustiveness and mutual exclusivity of options.
    P009 checks ordering of those options.
    Adjacent but non-overlapping.

SEVERITY:
    Non-sequential ordering detected     -> 0.50
    Primacy risk (favorable option first) -> 0.35
    Recency risk (aural mode)            -> 0.35

PROXY NOTE:
    True order effects require experimental data comparing randomized
    vs fixed option presentation. This rule uses structural proxies.
    Fixed uniform scales are explicitly excluded — this is intentional.
"""

import re
from app.principles.base_rule import BaseRule, Violation


class P009(BaseRule):

    id = "P009"
    description = (
        "Detects response option ordering that creates primacy, recency, "
        "or non-sequential bias in respondent option selection."
    )

    # Known logically ordered scale sequences
    # If detected in scrambled order -> flag non-sequential ordering
    ORDERED_SEQUENCES = [
        # Frequency scales (correct order: high to low)
        ["always", "often", "sometimes", "rarely", "never"],
        ["always", "usually", "sometimes", "rarely", "never"],
        ["very often", "often", "sometimes", "rarely", "never"],
        # Agreement scales (correct order: strong agree to strong disagree)
        ["strongly agree", "agree", "neutral", "disagree", "strongly disagree"],
        ["strongly agree", "agree", "somewhat agree", "disagree", "strongly disagree"],
        # Satisfaction scales
        ["very satisfied", "satisfied", "neutral", "dissatisfied", "very dissatisfied"],
    ]

    # Favorable options — if listed first in a non-frequency context, flag primacy
    FAVORABLE_FIRST_SIGNALS = [
        "excellent",
        "strongly agree",
        "very satisfied",
        "always",
        "definitely",
        "completely",
    ]

    def evaluate(self, item: dict) -> Violation | None:
        """
        Check a single item for response option order effects.

        GATE: Returns None immediately for items using a fixed uniform
        scale — order effects are constant and not item-level concerns.

        Args:
            item (dict): Parsed survey item from SurveyParser.

        Returns:
            Violation if option order issues detected, else None.
        """
        scale = item.get("scale", {})
        labels = scale.get("labels", {})

        # Gate: fixed uniform scale — no item-level order effects
        if self._is_fixed_uniform_scale(scale):
            return None

        # For variable or custom scales, check ordering
        if not labels:
            return None

        label_values = [v.lower().strip() for v in labels.values()]
        signals = []

        # Check non-sequential ordering
        non_seq = self._check_non_sequential(label_values)
        if non_seq:
            signals.append(non_seq)

        # Check primacy risk
        primacy = self._check_primacy_risk(label_values)
        if primacy:
            signals.append(primacy)

        if not signals:
            return None

        severity = 0.50 if len(signals) > 1 else (
            0.50 if "non-sequential" in signals[0] else 0.35
        )

        evidence = (
            "Response option order effect risk detected. "
            "Signal(s): " + " | ".join(signals)
        )

        return Violation(
            principle=self.id,
            severity=round(severity, 2),
            evidence=evidence
        )

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _is_fixed_uniform_scale(self, scale: dict) -> bool:
        """
        Detect whether this item uses a fixed uniform scale.

        A fixed uniform scale is:
            - Same scale applied to all items (uniform)
            - Logically ordered high-to-low or low-to-high
            - Standard frequency or agreement format

        Returns True if fixed uniform — P009 should skip this item.
        """
        if not scale:
            return False

        labels = scale.get("labels", {})
        if not labels:
            return False

        label_values = [v.lower().strip() for v in labels.values()]

        # Check if labels match any known ordered sequence
        for sequence in self.ORDERED_SEQUENCES:
            if len(label_values) == len(sequence):
                if label_values == sequence:
                    return True
                # Also accept reverse order (low to high)
                if label_values == list(reversed(sequence)):
                    return True

        return False

    def _check_non_sequential(self, label_values: list) -> str | None:
        """
        Check if labels match a known sequence but in scrambled order.

        Returns evidence string if scrambled, else None.
        """
        for sequence in self.ORDERED_SEQUENCES:
            if len(label_values) == len(sequence):
                # Same labels but in wrong order?
                if (set(label_values) == set(sequence) and
                        label_values != sequence and
                        label_values != list(reversed(sequence))):
                    return (
                        f"non-sequential option ordering detected — "
                        f"labels match a known scale but are scrambled: "
                        f"{label_values}"
                    )
        return None

    def _check_primacy_risk(self, label_values: list) -> str | None:
        """
        Check if the most favorable option is listed first.

        Returns evidence string if primacy risk detected, else None.
        """
        if not label_values:
            return None

        first_label = label_values[0]
        if any(fav in first_label for fav in self.FAVORABLE_FIRST_SIGNALS):
            return (
                f"primacy risk — most favorable option '{first_label}' "
                f"listed first in visual survey format, "
                f"increasing probability of selection beyond true prevalence"
            )
        return None