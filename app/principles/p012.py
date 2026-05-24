"""
app/principles/p012.py

PRINCIPLE: P012 — Exhaustive and Mutually Exclusive Response Options
SOURCE: Fowler — Survey Research Methods, Ch. 7, p. 108–110
        Dillman — Mail and Internet Surveys, Ch. 5, p. 193–196
OPERATIONALIZABILITY: High
CONFIDENCE: High

WHAT THIS RULE CHECKS:
    Response options must satisfy two conditions:

    CONDITION 1 — EXHAUSTIVE:
        Options must cover all possible answers a respondent might
        legitimately give. If a respondent's true answer falls outside
        the provided options, they are forced to misrepresent themselves.
        Gaps in coverage introduce systematic measurement error.

    CONDITION 2 — MUTUALLY EXCLUSIVE:
        No two options should apply simultaneously to the same respondent.
        Overlapping options force arbitrary choice between equivalent
        answers, producing unreliable data.

    DETECTION STRATEGY:

    CHECK 1 — Known overlapping label pairs:
        Pairs of labels where both could legitimately apply to the
        same respondent at the same time.
        e.g. "often" and "usually" — a respondent who does something
        70% of the time could select either.

    CHECK 2 — Subset containment:
        One label is a strict semantic subset of another.
        e.g. "always" contains "almost always" — if always is true,
        almost always is also technically true.

    CHECK 3 — Coverage gaps in ordered scales:
        Ordered scales missing logical intermediate steps.
        e.g. "Always / Sometimes / Never" — missing "Often" and "Rarely"
        creates a scale where respondents who are between positions
        have no accurate option.

    GATE CONDITION:
        For well-known standard scales (Likert frequency, agreement,
        satisfaction) that are widely validated, this rule returns
        None — these scales are presumed exhaustive and mutually
        exclusive by design and empirical validation.

BOUNDARY WITH P011:
    P011 checks whether specific options (midpoint, DK) EXIST.
    P012 checks whether ALL options together are exhaustive and
    non-overlapping. P011 is a specific case; P012 is the general rule.

BOUNDARY WITH P009:
    P009 checks option ORDERING.
    P012 checks option CONTENT (exhaustiveness, exclusivity).

SEVERITY:
    Overlapping options detected  -> 0.65
    Coverage gap detected         -> 0.50
    Subset containment detected   -> 0.55

PROXY NOTE:
    True exhaustiveness and mutual exclusivity require domain knowledge
    about all possible respondent states. This rule uses pattern matching
    on known problematic label combinations. Novel overlapping labels
    outside the known pairs list will not be detected.
"""

from app.principles.base_rule import BaseRule, InstrumentViolation


class P012(BaseRule):

    id = "P012"
    description = (
        "Detects response options that are non-exhaustive (coverage gaps) "
        "or non-mutually-exclusive (overlapping options)."
    )

    # ------------------------------------------------------------------
    # VALIDATED STANDARD SCALES — skip P012 for these
    # These are empirically validated and presumed E+ME by design.
    # ------------------------------------------------------------------
    VALIDATED_SCALES = [
        # Standard Likert frequency
        {"always", "often", "sometimes", "rarely", "never"},
        {"always", "usually", "sometimes", "rarely", "never"},
        {"very often", "often", "sometimes", "rarely", "never"},
        # Standard agreement
        {"strongly agree", "agree", "neutral", "disagree", "strongly disagree"},
        {"strongly agree", "agree", "disagree", "strongly disagree"},
        # Standard satisfaction
        {
            "very satisfied", "satisfied", "neutral",
            "dissatisfied", "very dissatisfied"
        },
        # Binary
        {"yes", "no"},
        {"true", "false"},
    ]

    # ------------------------------------------------------------------
    # KNOWN OVERLAPPING LABEL PAIRS
    # Both labels in a pair can apply to the same respondent simultaneously.
    # ------------------------------------------------------------------
    OVERLAPPING_PAIRS = [
        ("often", "usually"),
        ("often", "frequently"),
        ("usually", "frequently"),
        ("rarely", "seldom"),
        ("rarely", "occasionally"),
        ("seldom", "occasionally"),
        ("agree", "somewhat agree"),
        ("disagree", "somewhat disagree"),
        ("good", "very good"),
        ("satisfied", "very satisfied"),
        ("dissatisfied", "very dissatisfied"),
        ("sometimes", "occasionally"),
        ("sometimes", "at times"),
    ]

    # ------------------------------------------------------------------
    # SUBSET CONTAINMENT PAIRS
    # First label is a strict subset of the second —
    # if first is true, second is also technically true.
    # ------------------------------------------------------------------
    SUBSET_PAIRS = [
        ("always", "almost always"),
        ("never", "almost never"),
        ("strongly agree", "agree"),
        ("strongly disagree", "disagree"),
        ("completely", "mostly"),
    ]

    # ------------------------------------------------------------------
    # MINIMUM COVERAGE: ordered scales should have at least N options
    # to avoid coverage gaps for intermediate positions.
    # ------------------------------------------------------------------
    MIN_FREQUENCY_SCALE_POINTS = 4
    MIN_AGREEMENT_SCALE_POINTS = 4

    def is_instrument_level(self) -> bool:
        return True

    def evaluate_instrument(self, items: list) -> list | None:
        """
        Evaluate scale options for exhaustiveness and mutual exclusivity.

        Args:
            items (list): Full list of item dicts from SurveyParser.

        Returns:
            list[InstrumentViolation] if E+ME violations detected, else None.
        """
        if not items:
            return None

        scale = items[0].get("scale", {})
        if not scale:
            return None

        labels = scale.get("labels", {})
        points = scale.get("points", 0)

        if not labels:
            return None

        label_values = [v.lower().strip() for v in labels.values()]
        label_set = set(label_values)

        # Gate: validated standard scale — skip
        if label_set in self.VALIDATED_SCALES:
            return None

        problems = []

        # --- Check 1: Overlapping label pairs ---
        overlap_hits = [
            pair for pair in self.OVERLAPPING_PAIRS
            if pair[0] in label_set and pair[1] in label_set
        ]
        if overlap_hits:
            problems.append((
                0.65,
                f"overlapping response options detected — "
                f"respondents could legitimately select multiple options: "
                f"{overlap_hits}. Options must be mutually exclusive."
            ))

        # --- Check 2: Subset containment ---
        subset_hits = [
            pair for pair in self.SUBSET_PAIRS
            if pair[0] in label_set and pair[1] in label_set
        ]
        if subset_hits:
            problems.append((
                0.55,
                f"subset containment detected — "
                f"one option is a logical subset of another: "
                f"{subset_hits}. If the subset is true, the superset "
                f"is also technically true, violating mutual exclusivity."
            ))

        # --- Check 3: Coverage gaps ---
        gap = self._check_coverage_gap(label_set, points)
        if gap:
            problems.append((0.50, gap))

        if not problems:
            return None

        # Use highest severity among detected problems
        severity = max(sev for sev, _ in problems)
        evidence_parts = [msg for _, msg in problems]

        evidence = (
            f"Exhaustiveness/mutual exclusivity violation(s) detected "
            f"({points}-point scale). "
            "Problem(s): " + " | ".join(evidence_parts)
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
            "P012 is an instrument-level rule. "
            "Call evaluate_instrument(items) with the full item list."
        )

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _check_coverage_gap(self, label_set: set, points: int) -> str | None:
        """
        Detect coverage gaps in ordered frequency or agreement scales.

        A frequency scale with fewer than 4 points likely has gaps
        where intermediate positions have no accurate option.

        Returns evidence string if gap detected, else None.
        """
        frequency_terms = {
            "always", "often", "usually", "frequently",
            "sometimes", "rarely", "seldom", "never"
        }
        agreement_terms = {
            "strongly agree", "agree", "neutral", "disagree",
            "strongly disagree", "somewhat agree", "somewhat disagree"
        }

        is_frequency = bool(label_set & frequency_terms)
        is_agreement = bool(label_set & agreement_terms)

        if is_frequency and points < self.MIN_FREQUENCY_SCALE_POINTS:
            return (
                f"frequency scale with only {points} points — "
                f"insufficient coverage for intermediate frequency positions. "
                f"Respondents between 'always' and 'never' have no "
                f"accurate option. Recommend minimum 5-point frequency scale."
            )

        if is_agreement and points < self.MIN_AGREEMENT_SCALE_POINTS:
            return (
                f"agreement scale with only {points} points — "
                f"insufficient coverage for nuanced agreement positions. "
                f"Recommend minimum 5-point agreement scale with midpoint."
            )

        return None