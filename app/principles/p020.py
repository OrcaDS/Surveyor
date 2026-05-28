"""
app/principles/p020.py

PRINCIPLE: P020 — Survey Length and Response Fatigue
SOURCE: Dillman — Mail and Internet Surveys, Ch. 4, p. 156–159
        Fowler — Survey Research Methods, Ch. 5, p. 61–63
        Krosnick — Survey Research, Annual Review of Psychology, 1999
OPERATIONALIZABILITY: High
CONFIDENCE: High

WHAT THIS RULE CHECKS:
    Instrument-level response fatigue from excessive survey length.
    As survey length increases, respondents engage in satisficing,
    straight-lining, and early dropout — degrading data quality
    progressively toward the end of the instrument.

    This is distinct from P007:
        P007 = item-level satisficing risk from individual item complexity
        P020 = instrument-level fatigue from cumulative respondent burden

    THREE CHECKS:

    CHECK 1 — Total item count:
        Dillman (2014) thresholds for Likert-style instruments:
            < 50 items  -> acceptable burden
            50-74 items -> elevated fatigue risk
            75+ items   -> high fatigue risk

    CHECK 2 — Estimated completion time:
        Professional respondents (superintendents, managers) process
        Likert items at roughly 8-10 items per minute including reading.
        Dillman recommends keeping surveys under 10-12 minutes for
        professional populations.
            < 8 minutes  -> acceptable
            8-12 minutes -> elevated
            12+ minutes  -> high burden

    CHECK 3 — Cognitive density in final quartile:
        If the last 25% of items have higher average word count than
        the first 25%, respondents encounter the hardest items when
        most fatigued — compounding error at the end of the instrument.

BOUNDARY WITH P007:
    P007 = item-level satisficing from individual complexity
    P020 = instrument-level fatigue from cumulative length
    P007 fires per item. P020 fires once on the full instrument.

BOUNDARY WITH P006:
    P006 detects missing polarity reversal across the instrument.
    P020 detects excessive length causing fatigue.
    Both are instrument-level rules but measure different problems.

SEVERITY:
    Elevated item count only              -> 0.40
    High item count only                  -> 0.60
    High item count + completion time     -> 0.75
    All three checks triggered            -> 0.85

PROXY NOTE:
    Actual fatigue effects depend on respondent motivation, survey mode,
    and topic salience — none of which are detectable from item text alone.
    This rule uses structural proxies (count, time estimate, density)
    that are reliable population-level predictors but not individual guarantees.
"""

from app.principles.base_rule import BaseRule, InstrumentViolation
from app.principles.signals import Signal, SignalType

class P020(BaseRule):

    id = "P020"
    description = (
        "Detects instrument-level response fatigue risk from excessive "
        "survey length, completion time, and cognitive density distribution."
    )

    # Dillman (2014) thresholds for Likert-style instruments
    ELEVATED_ITEM_THRESHOLD = 50
    HIGH_ITEM_THRESHOLD = 75

    # Items per minute for professional Likert respondents (Dillman 2014)
    ITEMS_PER_MINUTE = 9

    # Completion time thresholds in minutes
    ELEVATED_TIME_THRESHOLD = 8
    HIGH_TIME_THRESHOLD = 12

    def is_instrument_level(self) -> bool:
        return True

    def evaluate_instrument(self, items: list) -> list | None:
        """
        Evaluate the full instrument for response fatigue risk.

        Args:
            items (list): Full list of item dicts from SurveyParser.

        Returns:
            list[InstrumentViolation] if fatigue risk detected, else None.
        """
        if not items:
            return None

        total = len(items)
        problems = []

        # --- Check 1: Total item count ---
        if total >= self.HIGH_ITEM_THRESHOLD:
            problems.append(
                f"high item count ({total} items, "
                f"threshold: {self.HIGH_ITEM_THRESHOLD}) — "
                f"Dillman (2014) documents significant response quality "
                f"degradation at this length for professional respondents"
            )
        elif total >= self.ELEVATED_ITEM_THRESHOLD:
            problems.append(
                f"elevated item count ({total} items, "
                f"threshold: {self.ELEVATED_ITEM_THRESHOLD}) — "
                f"fatigue effects likely in final third of instrument"
            )

        # --- Check 2: Estimated completion time ---
        estimated_minutes = round(total / self.ITEMS_PER_MINUTE, 1)

        if estimated_minutes >= self.HIGH_TIME_THRESHOLD:
            problems.append(
                f"high estimated completion time "
                f"({estimated_minutes} minutes at {self.ITEMS_PER_MINUTE} "
                f"items/minute for professional Likert respondents) — "
                f"exceeds Dillman's recommended 10-12 minute ceiling"
            )
        elif estimated_minutes >= self.ELEVATED_TIME_THRESHOLD:
            problems.append(
                f"elevated estimated completion time "
                f"({estimated_minutes} minutes) — "
                f"approaching Dillman's recommended ceiling"
            )

        # --- Check 3: Cognitive density in final quartile ---
        quartile_size = max(1, total // 4)
        first_quartile = items[:quartile_size]
        last_quartile = items[-quartile_size:]

        first_avg = sum(
            i.get("word_count", 0) for i in first_quartile
        ) / len(first_quartile)

        last_avg = sum(
            i.get("word_count", 0) for i in last_quartile
        ) / len(last_quartile)

        if last_avg > first_avg * 1.15:
            problems.append(
                f"cognitive density increases toward end of instrument — "
                f"first quartile avg word count: {first_avg:.1f}, "
                f"last quartile avg word count: {last_avg:.1f}. "
                f"Respondents encounter most complex items when most fatigued"
            )

        if not problems:
            return None

        # Severity based on number and type of problems
        if len(problems) == 1:
            # Single problem: elevated vs high matters
            if "high item count" in problems[0] or "high estimated" in problems[0]:
                severity = 0.60
            else:
                severity = 0.40
        elif len(problems) == 2:
            severity = 0.75
        else:
            severity = 0.85

        evidence = (
            f"Response fatigue risk detected "
            f"({total} items, ~{estimated_minutes} min estimated). "
            "Problem(s): " + " | ".join(problems)
        )

        signals = []

        # --- Item count signals ---
        if total >= self.HIGH_ITEM_THRESHOLD:
            signals.append(Signal(
                type=SignalType.HIGH_ITEM_COUNT,
                description=f"high item count: {total} items",
                terms=[],
                confidence=0.95,
                metadata={
                    "total_items": total,
                    "threshold": self.HIGH_ITEM_THRESHOLD,
                }
            ))

        elif total >= self.ELEVATED_ITEM_THRESHOLD:
            signals.append(Signal(
                type=SignalType.ELEVATED_ITEM_COUNT,
                description=f"elevated item count: {total} items",
                terms=[],
                confidence=0.90,
                metadata={
                    "total_items": total,
                    "threshold": self.ELEVATED_ITEM_THRESHOLD,
                }
            ))

        # --- Completion time signals ---
        if estimated_minutes >= self.HIGH_TIME_THRESHOLD:
            signals.append(Signal(
                type=SignalType.HIGH_COMPLETION_TIME,
                description=(
                    f"high estimated completion time: "
                    f"{estimated_minutes} minutes"
                ),
                terms=[],
                confidence=0.85,
                metadata={
                    "estimated_minutes": estimated_minutes,
                    "threshold": self.HIGH_TIME_THRESHOLD,
                }
            ))

        elif estimated_minutes >= self.ELEVATED_TIME_THRESHOLD:
            signals.append(Signal(
                type=SignalType.ELEVATED_COMPLETION_TIME,
                description=(
                    f"elevated estimated completion time: "
                    f"{estimated_minutes} minutes"
                ),
                terms=[],
                confidence=0.80,
                metadata={
                    "estimated_minutes": estimated_minutes,
                    "threshold": self.ELEVATED_TIME_THRESHOLD,
                }
            ))

        # --- Density distribution signal ---
        if last_avg > first_avg * 1.15:
            signals.append(Signal(
                type=SignalType.DENSITY_INCREASE,
                description=(
                    f"cognitive density increases toward end: "
                    f"first quartile avg {first_avg:.1f} words, "
                    f"last quartile avg {last_avg:.1f} words"
                ),
                terms=[],
                confidence=0.80,
                metadata={
                    "first_quartile_avg_words": round(first_avg, 1),
                    "last_quartile_avg_words": round(last_avg, 1),
                }
            ))

        return [
            InstrumentViolation(
                principle=self.id,
                severity=round(severity, 2),
                evidence=evidence,
                affected_items=[
                    item["item_id"] for item in last_quartile
                ],
                signals=signals
            )
        ]

    def evaluate(self, item: dict):
        raise NotImplementedError(
            "P020 is an instrument-level rule. "
            "Call evaluate_instrument(items) with the full item list."
        )