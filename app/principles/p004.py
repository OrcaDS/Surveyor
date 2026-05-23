"""
app/principles/p004.py

PRINCIPLE: P004 — Recall Period Calibration
SOURCE: Tourangeau, Rips & Rasinski — The Psychology of Survey Response, Ch. 3
        Fowler — Survey Research Methods, Ch. 6, p. 85–87
OPERATIONALIZABILITY: Medium
CONFIDENCE: Medium

WHAT THIS RULE CHECKS:
    Behavioral frequency questions that ask respondents to recall past events
    over a time window that is either:
        (a) too long to retrieve accurately (telescoping risk), or
        (b) completely unanchored (no time window specified at all)

    This rule ONLY applies to behavioral frequency items — items that ask
    how often a respondent performed or experienced a concrete behavior.

    It does NOT apply to:
        - Attitude or belief items ("I believe that...", "I affirm that...")
        - Dispositional self-report items ("I have the ability to...")
        - Likert-style agreement items on stable traits

    Most Likert-style leadership/attitude surveys will produce ZERO violations
    on P004. That is the correct result — not a failure of the rule.

DETECTION STRATEGY:

    STEP 1 — Is this a behavioral frequency item?
        Must contain BOTH:
            (a) a behavioral verb (did, performed, attended, reported, used, went)
            (b) a frequency expression (how many times, how often, number of)
        If not both — skip, return None immediately.

    STEP 2 — Is there a time anchor?
        Look for time-bounding expressions:
            "in the past week", "last month", "in the past year",
            "since January", "during the semester", etc.
        If no anchor → flag as UNANCHORED (severity 0.60)

    STEP 3 — If anchored, is the window too long?
        Windows longer than 3 months for event-frequency questions
        introduce significant telescoping error (Tourangeau et al.).
        Flag if window > 3 months → severity 0.40

BOUNDARY WITH P001:
    P001 Stage 2 flags vague frequency ADVERBS in item text (often, usually).
    P004 flags unanchored or over-long recall WINDOWS for behavioral events.
    Same domain, different targets:
        P001 = the adverb itself is vague
        P004 = the recall window makes accurate retrieval impossible

BOUNDARY WITH P017:
    P017 checks whether the item provides recall-enabling STRATEGIES.
    P004 checks whether the recall PERIOD is appropriate.
    Both can fire on the same item without overlap:
        P004 = window too long
        P017 = no landmark cue or decomposition strategy provided

SEVERITY:
    Unanchored behavioral frequency item → 0.60
    Recall window > 3 months            → 0.40

PROXY NOTE:
    Behavioral frequency detection relies on verb + frequency expression
    co-occurrence. Items phrased as attitudes or dispositions will not
    trigger this rule even if they implicitly reference behavior.
    This is intentional — attitude items are a different measurement mode.
"""

import re
from app.principles.base_rule import BaseRule, Violation


class P004(BaseRule):

    id = "P004"
    description = (
        "Detects behavioral frequency items with unanchored or excessively "
        "long recall periods that produce unreliable retrospective data."
    )

    # ------------------------------------------------------------------
    # BEHAVIORAL FREQUENCY SIGNALS
    # Both a behavioral verb AND a frequency expression must be present
    # for this rule to activate. Attitude/belief items will not match.
    # ------------------------------------------------------------------

    BEHAVIORAL_VERBS = [
        r"\bdid\b",
        r"\bperformed\b",
        r"\battended\b",
        r"\breported\b",
        r"\bwent\b",
        r"\bvisited\b",
        r"\bused\b",
        r"\bexercised\b",
        r"\bconsumed\b",
        r"\bpurchased\b",
        r"\bcontacted\b",
        r"\bsubmitted\b",
        r"\bcompleted\b",
        r"\breceived\b",
    ]

    FREQUENCY_EXPRESSIONS = [
        r"\bhow many times\b",
        r"\bhow often\b",
        r"\bnumber of times\b",
        r"\bfrequency of\b",
        r"\bon how many\b",
        r"\bhow frequently\b",
        r"\btimes per\b",
        r"\boccasions\b",
    ]

    # ------------------------------------------------------------------
    # TIME ANCHOR PATTERNS
    # If any of these are present, the item has a defined recall window.
    # ------------------------------------------------------------------

    TIME_ANCHORS = [
        r"\blast week\b",
        r"\blast month\b",
        r"\blast year\b",
        r"\bpast week\b",
        r"\bpast month\b",
        r"\bpast year\b",
        r"\bpast \d+ days\b",
        r"\bpast \d+ weeks\b",
        r"\bpast \d+ months\b",
        r"\bin the past\b",
        r"\bsince \w+\b",
        r"\bduring the\b",
        r"\bthis week\b",
        r"\bthis month\b",
        r"\bthis year\b",
        r"\bthis semester\b",
        r"\bthis quarter\b",
    ]

    # ------------------------------------------------------------------
    # LONG WINDOW PATTERNS (> 3 months)
    # If anchored but the window is too long, flag telescoping risk.
    # ------------------------------------------------------------------

    LONG_WINDOW_PATTERNS = [
        r"\blast year\b",
        r"\bpast year\b",
        r"\bpast \d+ years\b",
        r"\bpast 6 months\b",
        r"\bpast 12 months\b",
        r"\bover the past year\b",
        r"\bsince last year\b",
        r"\bin the past year\b",
    ]

    def evaluate(self, item: dict) -> Violation | None:
        """
        Check a single item for recall period calibration issues.

        Returns None immediately for non-behavioral items.
        Only fires on behavioral frequency items.

        Args:
            item (dict): Parsed survey item from SurveyParser.

        Returns:
            Violation if recall period issue detected, else None.
        """
        text = self._get_text(item).lower()

        # Step 1 — Gate: is this a behavioral frequency item?
        # Must have BOTH a behavioral verb AND a frequency expression.
        has_behavioral_verb = any(
            re.search(pattern, text) for pattern in self.BEHAVIORAL_VERBS
        )
        has_frequency_expression = any(
            re.search(pattern, text) for pattern in self.FREQUENCY_EXPRESSIONS
        )

        if not (has_behavioral_verb and has_frequency_expression):
            # This is an attitude/disposition item — P004 does not apply.
            return None

        # Step 2 — Does the item have a time anchor?
        has_anchor = any(
            re.search(pattern, text) for pattern in self.TIME_ANCHORS
        )

        if not has_anchor:
            return Violation(
                principle=self.id,
                severity=0.60,
                evidence=(
                    "Behavioral frequency item has no time anchor. "
                    "Respondents cannot retrieve an accurate count without "
                    "a defined recall window. Add a specific time period "
                    "(e.g. 'in the past month', 'during this semester')."
                )
            )

        # Step 3 — Is the anchor window too long?
        has_long_window = any(
            re.search(pattern, text) for pattern in self.LONG_WINDOW_PATTERNS
        )

        if has_long_window:
            return Violation(
                principle=self.id,
                severity=0.40,
                evidence=(
                    "Behavioral frequency item uses a recall window longer "
                    "than 3 months. Telescoping error is likely — respondents "
                    "will over-report recent events and under-report distant ones. "
                    "Consider shortening the recall window or using landmark cues."
                )
            )

        # Anchored and window is acceptable — no violation.
        return None