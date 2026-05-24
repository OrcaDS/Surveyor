"""
app/principles/p013.py

PRINCIPLE: P013 — Scale Direction Consistency
SOURCE: Fowler — Survey Research Methods, Ch. 7, p. 110–112
        Dillman — Mail and Internet Surveys, Ch. 5, p. 196–199
OPERATIONALIZABILITY: High
CONFIDENCE: High

WHAT THIS RULE CHECKS:
    Scale direction consistency ensures that the same numerical value
    means the same thing across all items in the instrument. Violations
    corrupt composite scoring and make cross-item comparisons meaningless.

    TWO CHECKS:

    CHECK 1 — Mixed scale types:
        Frequency labels (Always/Never) and agreement labels
        (Strongly Agree/Strongly Disagree) in the same instrument
        create incomparable response distributions. A score of 4
        means "Often" on one item and "Agree" on another — these
        are not equivalent and cannot be averaged into a composite.

    CHECK 2 — Undocumented reverse-scored items:
        Items that are semantically negative (contain main-clause
        negation or negated constructs) but are scored in the same
        direction as positive items without annotation produce
        artificially suppressed composite scores.
        e.g. "I never punish unfairly" scored 5=Always means
        high scores indicate NEVER punishing unfairly — but the
        composite treats 5 the same as "I always reward fairly."
        Without documentation and reverse-scoring in analysis,
        this corrupts reliability coefficients.

BOUNDARY WITH P006:
    P006 detects missing polarity reversal (acquiescence bias risk).
    P013 detects inconsistent scale DIRECTION across items.
    P006 = no negative items exist (instrument-level polarity problem)
    P013 = negative items exist but are not handled consistently

BOUNDARY WITH P008:
    P008 checks anchor label QUALITY (vague quantifiers).
    P013 checks scale direction CONSISTENCY across items.
    P008 = are the labels good?
    P013 = are the directions consistent?

SEVERITY:
    Mixed scale types detected              -> 0.80
    Undocumented reverse-scored items only  -> 0.55
    Both                                    -> 0.90

PROXY NOTE:
    Scale direction detection relies on label classification and
    main-clause negation detection. Semantically reversed items
    without syntactic negation markers will not be detected.
    Explicit reverse-score annotation (R) is the most reliable signal.
"""

import re
from app.principles.base_rule import BaseRule, InstrumentViolation


class P013(BaseRule):

    id = "P013"
    description = (
        "Detects mixed scale types and undocumented reverse-scored items "
        "that corrupt composite scoring and cross-item comparability."
    )

    # Frequency scale label markers
    FREQUENCY_MARKERS = [
        "always", "often", "usually", "frequently", "sometimes",
        "rarely", "seldom", "never", "occasionally",
    ]

    # Agreement scale label markers
    AGREEMENT_MARKERS = [
        "strongly agree", "agree", "disagree", "strongly disagree",
        "neither agree nor disagree", "somewhat agree", "somewhat disagree",
    ]

    # Satisfaction scale label markers
    SATISFACTION_MARKERS = [
        "very satisfied", "satisfied", "dissatisfied",
        "very dissatisfied", "neutral",
    ]

    # Main-clause negation — same as P006/P015
    MAIN_CLAUSE_NEGATION = [
        r"\bi do not\b",
        r"\bi don't\b",
        r"\bi cannot\b",
        r"\bi can't\b",
        r"\bi never\b",
        r"\bi am not\b",
        r"\bi have not\b",
        r"\bi will not\b",
        r"\bi won't\b",
        r"\bi neither\b",
        r"\bi fail to\b",
        r"\bi am unable\b",
        r"\bi refuse\b",
    ]

    # Explicit reverse-score markers
    REVERSE_MARKERS = [
        r"\(r\)", r"\[r\]", r"\breverse\b",
        r"\breverse-scored\b", r"\breverse scored\b",
    ]

    def is_instrument_level(self) -> bool:
        return True

    def evaluate_instrument(self, items: list) -> list | None:
        """
        Evaluate the instrument for scale direction consistency problems.

        Args:
            items (list): Full list of item dicts from SurveyParser.

        Returns:
            list[InstrumentViolation] if direction issues detected, else None.
        """
        if not items:
            return None

        scale = items[0].get("scale", {})
        labels = scale.get("labels", {})
        label_values = [v.lower().strip() for v in labels.values()]

        problems = []

        # --- Check 1: Mixed scale types ---
        mixed = self._check_mixed_scale_types(label_values)
        if mixed:
            problems.append((0.80, mixed))

        # --- Check 2: Undocumented reverse-scored items ---
        reverse_result = self._check_undocumented_reverse(items)
        if reverse_result:
            sev, msg = reverse_result
            problems.append((sev, msg))

        if not problems:
            return None

        severity = max(sev for sev, _ in problems)
        if len(problems) > 1:
            severity = 0.90

        evidence = (
            "Scale direction consistency problem(s) detected. "
            "Problem(s): " + " | ".join(msg for _, msg in problems)
        )

        affected = list(range(1, len(items) + 1))

        return [
            InstrumentViolation(
                principle=self.id,
                severity=round(severity, 2),
                evidence=evidence,
                affected_items=affected
            )
        ]

    def evaluate(self, item: dict):
        raise NotImplementedError(
            "P013 is an instrument-level rule. "
            "Call evaluate_instrument(items) with the full item list."
        )

    # ------------------------------------------------------------------
    # PRIVATE CHECKERS
    # ------------------------------------------------------------------

    def _check_mixed_scale_types(self, label_values: list) -> str | None:
        """
        Detect frequency and agreement labels mixed in same scale.

        Returns evidence string if mixed, else None.
        """
        has_frequency = any(
            m in label_values for m in self.FREQUENCY_MARKERS
        )
        has_agreement = any(
            any(m in label for m in self.AGREEMENT_MARKERS)
            for label in label_values
        )
        has_satisfaction = any(
            any(m in label for m in self.SATISFACTION_MARKERS)
            for label in label_values
        )

        scale_types = []
        if has_frequency:
            scale_types.append("frequency")
        if has_agreement:
            scale_types.append("agreement")
        if has_satisfaction:
            scale_types.append("satisfaction")

        if len(scale_types) > 1:
            return (
                f"mixed scale types detected in same instrument: "
                f"{' + '.join(scale_types)} labels used together. "
                f"Composite scores across items are meaningless when "
                f"scale types differ — a score of 4 means different "
                f"things on frequency vs agreement items."
            )

        return None

    def _check_undocumented_reverse(
        self, items: list
    ) -> tuple | None:
        """
        Detect semantically negative items without reverse-score annotation.

        Returns (severity, evidence_string) or None.
        """
        undocumented = []

        for item in items:
            text = self._get_text(item).lower()

            # Check for main-clause negation
            has_negation = any(
                re.search(p, text) for p in self.MAIN_CLAUSE_NEGATION
            )

            if not has_negation:
                continue

            # Check for explicit reverse-score marker
            has_reverse_marker = any(
                re.search(p, text) for p in self.REVERSE_MARKERS
            )

            if not has_reverse_marker:
                undocumented.append(item["item_id"])

        if not undocumented:
            return None

        return (
            0.55,
            f"undocumented reverse-scored item(s) detected: "
            f"items {undocumented} contain main-clause negation but "
            f"have no reverse-score annotation (R). "
            f"Scoring these items in positive direction corrupts "
            f"composite reliability coefficients (Cronbach alpha). "
            f"Add (R) annotation and reverse-score in analysis."
        )