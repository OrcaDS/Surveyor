"""
app/principles/p008.py

PRINCIPLE: P008 — Scale Anchor Calibration
SOURCE: Fowler — Survey Research Methods, Ch. 7, p. 100-104
        Dillman — Mail and Internet Surveys, Ch. 5
        Tourangeau et al. — Ch. 7, Section 7.3
OPERATIONALIZABILITY: High
CONFIDENCE: High

WHAT THIS RULE CHECKS:
    The quality of response scale anchor labels. Poor anchor calibration
    produces data where the same numerical score means different things
    to different respondents, destroying comparability.

    This rule evaluates the SCALE object, not individual item text.
    It fires once per instrument, not once per item.

    THREE PROBLEMS DETECTED:

    PROBLEM 1 — Vague quantifier labels:
        Frequency labels like "Often", "Sometimes", "Rarely" have no
        numerical referent. Dillman (2014) documents that respondents
        interpret "often" as anywhere from 30% to 90% of the time.
        These labels produce non-comparable data across respondents.

    PROBLEM 2 — Asymmetric scale distribution:
        A well-calibrated scale should have equal numbers of positive
        and negative options around a midpoint.
        e.g. Always / Often / Sometimes / Rarely / Never
             2 positive + 1 neutral + 2 negative = balanced
        Asymmetric scales (3 positive, 1 neutral, 1 negative) push
        responses toward the positive end artificially.

    PROBLEM 3 — Missing endpoint anchors:
        Both ends of the scale must be labeled. Unlabeled endpoints
        are interpreted inconsistently across respondents.

BOUNDARY WITH P001 Stage 2:
    P001 Stage 2 flags vague frequency ADVERBS in ITEM TEXT.
    P008 flags vague quantifier LABELS in SCALE ANCHORS.
    Same words can appear in both locations — but they are different
    problems with different fixes:
        P001 fix: rewrite the item stem
        P008 fix: replace or supplement scale anchor labels

BOUNDARY WITH P011:
    P011 checks whether a midpoint or Don't Know option exists.
    P008 checks whether existing anchor labels are well-calibrated.
    P011 = does the midpoint exist?
    P008 = is the midpoint (and all anchors) clearly defined?

BOUNDARY WITH P013:
    P013 checks scale direction consistency across items.
    P008 checks anchor label quality within a single scale.

SEVERITY:
    1 problem detected -> 0.35
    2 problems detected -> 0.60
    3 problems detected -> 0.80

PROXY NOTE:
    True anchor calibration requires cognitive interview data showing
    how respondents interpret each label. This rule uses a curated
    list of known vague quantifiers from Fowler and Dillman's documented
    problematic labels. Domain-specific miscalibration will not be detected.
"""

import re
from app.principles.base_rule import BaseRule, InstrumentViolation


class P008(BaseRule):

    id = "P008"
    description = (
        "Detects scale anchor calibration problems: vague quantifier labels, "
        "asymmetric distribution, and missing endpoint anchors."
    )

    # ------------------------------------------------------------------
    # PROBLEM 1 — Known vague quantifier labels
    # Sourced from Fowler (2014) and Dillman (2014) documented examples.
    # These labels have no numerical referent and vary widely by respondent.
    # ------------------------------------------------------------------
    VAGUE_QUANTIFIERS = [
        "often",
        "sometimes",
        "rarely",
        "occasionally",
        "frequently",
        "seldom",
        "usually",
        "generally",
        "regularly",
        "normally",
        "typically",
        "almost always",
        "almost never",
        "a lot",
        "a little",
        "somewhat",
        "fairly",
        "quite",
    ]

    # ------------------------------------------------------------------
    # PROBLEM 2 — Positive vs negative label classification
    # Used to detect asymmetric scale distribution.
    # ------------------------------------------------------------------
    POSITIVE_LABELS = [
        "always", "often", "frequently", "usually", "regularly",
        "strongly agree", "agree", "mostly agree", "almost always",
        "excellent", "very good", "good", "satisfied", "very satisfied",
        "extremely", "very much", "completely", "definitely",
        "true", "very true", "absolutely",
    ]

    NEGATIVE_LABELS = [
        "never", "rarely", "seldom", "occasionally",
        "strongly disagree", "disagree", "mostly disagree", "almost never",
        "poor", "very poor", "dissatisfied", "very dissatisfied",
        "not at all", "not true", "false", "definitely not",
    ]

    NEUTRAL_LABELS = [
        "sometimes", "neutral", "neither", "moderate", "average",
        "undecided", "no opinion", "not applicable", "n/a",
        "somewhat", "partially", "mixed",
    ]

    def is_instrument_level(self) -> bool:
        return True

    def evaluate_instrument(self, items: list) -> list | None:
        """
        Evaluate the scale anchors for calibration problems.

        Extracts scale from first item (scale is shared across all items).

        Args:
            items (list): Full list of item dicts from SurveyParser.

        Returns:
            list[InstrumentViolation] if calibration problems found, else None.
        """
        if not items:
            return None

        # Extract scale from first item — same scale applies to all items
        scale = items[0].get("scale", {})
        if not scale:
            return [
                InstrumentViolation(
                    principle=self.id,
                    severity=0.70,
                    evidence=(
                        "No scale definition detected in parsed survey. "
                        "Cannot evaluate anchor calibration. "
                        "Ensure scale header is present in the survey file."
                    ),
                    affected_items=[]
                )
            ]

        labels = scale.get("labels", {})
        points = scale.get("points", 0)
        label_values = [v.lower().strip() for v in labels.values()]

        problems = []

        # --- Problem 1: Vague quantifier labels ---
        vague_hits = [
            label for label in label_values
            if any(vq in label for vq in self.VAGUE_QUANTIFIERS)
        ]
        if vague_hits:
            problems.append(
                f"vague quantifier label(s) with no numerical referent: "
                f"{', '.join(repr(l) for l in vague_hits)}. "
                f"Respondents interpret these inconsistently "
                f"(Fowler 2014; Dillman 2014)."
            )

        # --- Problem 2: Asymmetric scale distribution ---
        positive_count = sum(
            1 for label in label_values
            if any(pos in label for pos in self.POSITIVE_LABELS)
        )
        negative_count = sum(
            1 for label in label_values
            if any(neg in label for neg in self.NEGATIVE_LABELS)
        )
        neutral_count = sum(
            1 for label in label_values
            if any(neu in label for neu in self.NEUTRAL_LABELS)
        )

        if positive_count != negative_count:
            problems.append(
                f"asymmetric scale distribution: "
                f"{positive_count} positive label(s), "
                f"{neutral_count} neutral label(s), "
                f"{negative_count} negative label(s). "
                f"Unequal positive/negative options push responses "
                f"artificially toward the dominant pole."
            )

        # --- Problem 3: Missing endpoint anchors ---
        # Check that the highest and lowest scale points have labels
        if points > 0:
            highest = str(points)
            lowest = "1"
            missing_endpoints = []
            if highest not in labels:
                missing_endpoints.append(f"top endpoint ({highest})")
            if lowest not in labels:
                missing_endpoints.append(f"bottom endpoint ({lowest})")
            if missing_endpoints:
                problems.append(
                    f"missing endpoint anchor(s): "
                    f"{', '.join(missing_endpoints)}. "
                    f"Unlabeled endpoints are interpreted inconsistently."
                )

        if not problems:
            return None

        severity_map = {1: 0.35, 2: 0.60}
        severity = severity_map.get(len(problems), 0.80)

        evidence = (
            f"Scale anchor calibration problem(s) detected "
            f"({points}-point scale, labels: "
            f"{', '.join(repr(v) for v in labels.values())}). "
            "Problem(s): " + " | ".join(problems)
        )

        return [
            InstrumentViolation(
                principle=self.id,
                severity=round(severity, 2),
                evidence=evidence,
                affected_items=list(range(1, len(items) + 1))
            )
        ]

    def evaluate(self, item: dict):
        raise NotImplementedError(
            "P008 is an instrument-level rule. "
            "Call evaluate_instrument(items) with the full item list."
        )