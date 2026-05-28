"""
app/principles/p011.py

PRINCIPLE: P011 — Middle Category and Don't Know (DK) Option
SOURCE: Fowler — Survey Research Methods, Ch. 7, p. 105–108
        Tourangeau et al. — The Psychology of Survey Response, Ch. 7
        Dillman — Mail and Internet Surveys, Ch. 5, p. 189–192
OPERATIONALIZABILITY: High
CONFIDENCE: High

WHAT THIS RULE CHECKS:
    Two related but distinct scale design problems:

    PROBLEM 1 — Missing midpoint on even-numbered scales:
        Even-numbered scales (2, 4, 6 points) force respondents to
        choose a side even when their true position is neutral.
        This produces artificial polarization in the data.
        Odd-numbered scales (3, 5, 7 points) with a labeled midpoint
        allow genuine neutral responses.
        NOTE: If the scale already has an odd number of points with
        a labeled midpoint, this check passes cleanly.

    PROBLEM 2 — Missing Don't Know / Not Applicable option:
        Some respondents genuinely:
            (a) have no opinion on the topic (non-attitudes)
            (b) find the item inapplicable to their situation
        Without a DK/NA option, these respondents are forced to
        fabricate an answer, producing noise in the data.
        Risk is higher when:
            - Items cover specialized behaviors not universal to role
            - Respondent population is heterogeneous in experience
            - Items reference specific tools, contexts, or situations

BOUNDARY WITH P008:
    P008 checks anchor label quality (vague quantifiers, asymmetry).
    P011 checks whether midpoint and DK options EXIST.
    P008 = are the labels good?
    P011 = are the right options present?

BOUNDARY WITH P012:
    P012 checks exhaustiveness and mutual exclusivity.
    P011 checks specific option presence (midpoint, DK).
    P011 is a subset concern of P012's exhaustiveness check,
    but focused specifically on neutral and non-attitude options.

SEVERITY:
    Missing midpoint (even scale)    -> 0.60
    Missing DK/NA option             -> 0.35
    Both missing                     -> 0.75

PROXY NOTE:
    Whether a DK option is needed depends on the construct and
    respondent population. For attitude/self-report items on
    role-specific behaviors (like this instrument), DK risk is
    moderate — some superintendents may not engage in all described
    behaviors. For factual knowledge items, DK risk is high.
"""

from app.principles.base_rule import BaseRule, InstrumentViolation
from app.principles.signals import Signal, SignalType

class P011(BaseRule):

    id = "P011"
    description = (
        "Detects missing midpoint options on even-numbered scales and "
        "absence of Don't Know or Not Applicable response options."
    )

    # Labels that indicate a midpoint exists
    MIDPOINT_LABELS = [
        "sometimes", "neutral", "neither", "moderate", "average",
        "undecided", "no opinion", "middle", "unsure", "uncertain",
        "occasionally", "partially", "mixed", "neither agree nor disagree",
    ]

    # Labels that indicate a DK/NA option exists
    DK_NA_LABELS = [
        "don't know", "do not know", "dk", "n/a", "not applicable",
        "not sure", "no opinion", "cannot say", "prefer not to answer",
        "not relevant", "does not apply", "na",
    ]

    def is_instrument_level(self) -> bool:
        return True

    def evaluate_instrument(self, items: list) -> list | None:
        """
        Evaluate the scale for missing midpoint and DK/NA options.

        Args:
            items (list): Full list of item dicts from SurveyParser.

        Returns:
            list[InstrumentViolation] if scale design issues detected,
            else None.
        """
        if not items:
            return None

        scale = items[0].get("scale", {})
        if not scale:
            return None

        points = scale.get("points", 0)
        labels = scale.get("labels", {})
        label_values = [v.lower().strip() for v in labels.values()]

        problems = []

        # --- Problem 1: Missing midpoint on even-numbered scale ---
        if points > 0 and points % 2 == 0:
            # Even-numbered scale — check if any label serves as midpoint
            has_midpoint = any(
                any(mid in label for mid in self.MIDPOINT_LABELS)
                for label in label_values
            )
            if not has_midpoint:
                problems.append(
                    f"even-numbered scale ({points} points) with no midpoint — "
                    f"respondents forced to choose a side even when genuinely "
                    f"neutral, producing artificial polarization. "
                    f"Add a labeled midpoint or switch to an odd-numbered scale."
                )

        # --- Problem 2: Missing DK/NA option ---
        has_dk = any(
            any(dk in label for dk in self.DK_NA_LABELS)
            for label in label_values
        )

        if not has_dk:
            problems.append(
                f"no Don't Know or Not Applicable option detected in scale "
                f"({points}-point scale: "
                f"{', '.join(repr(v) for v in labels.values())}). "
                f"Respondents who lack an opinion or find items inapplicable "
                f"are forced to fabricate responses, introducing noise. "
                f"Consider adding a DK/NA option, especially for role-specific "
                f"behavioral items where not all respondents have equal exposure."
            )

        if not problems:
            return None

        severity_map = {1: 0.35, 2: 0.75}
        # Adjust: missing midpoint alone is more severe than missing DK alone
        if len(problems) == 1 and "even-numbered" in problems[0]:
            severity = 0.60
        else:
            severity = severity_map.get(len(problems), 0.75)

        evidence = (
            f"Scale design problem(s) detected. "
            "Problem(s): " + " | ".join(problems)
        )

        signals = []

        if any("even-numbered" in p for p in problems):
            signals.append(Signal(
                type=SignalType.MISSING_MIDPOINT,
                description=(
                    f"even-numbered scale ({points} points) with no "
                    f"midpoint — forces artificial polarization"
                ),
                terms=[],
                confidence=0.90,
                metadata={
                    "scale_points": points,
                    "labels": label_values,
                }
            ))

        if not has_dk:
            signals.append(Signal(
                type=SignalType.MISSING_DK_OPTION,
                description=(
                    f"no Don't Know or Not Applicable option in "
                    f"{points}-point scale"
                ),
                terms=[],
                confidence=0.75,
                metadata={
                    "scale_points": points,
                    "labels": label_values,
                }
            ))

        return [
            InstrumentViolation(
                principle=self.id,
                severity=round(severity, 2),
                evidence=evidence,
                affected_items=list(range(1, len(items) + 1)),
                signals=signals
            )
        ]
    def evaluate(self, item: dict):
        raise NotImplementedError(
            "P011 is an instrument-level rule. "
            "Call evaluate_instrument(items) with the full item list."
        )