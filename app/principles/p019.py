"""
app/principles/p019.py

PRINCIPLE: P019 — Response Task Specification
SOURCE: Dillman — Mail and Internet Surveys, Ch. 5, p. 200–204
        Fowler — Survey Research Methods, Ch. 7, p. 112–114
OPERATIONALIZABILITY: High
CONFIDENCE: High

WHAT THIS RULE CHECKS:
    Whether response instructions are clearly specified at the item level.

    SIGNAL 1 — Ambiguous response instruction:
        Items that could be answered in multiple ways without clear
        instruction on which format is expected.
        e.g. "check one" vs "check all that apply" — if not stated,
        respondents make their own assumptions.

    SIGNAL 2 — Missing unit for numeric responses:
        Items asking for a number without specifying the unit.
        e.g. "How many hours?" — hours per day? per week? per year?

    SIGNAL 3 — Unclear branching or skip logic:
        Items that reference other items or conditions without
        clear instruction on how to navigate them.
        e.g. "If yes to Q5, answer Q6" — without clear formatting.

GATE:
    Standard Likert items with a defined uniform scale need no
    additional response task specification — the scale IS the task.
    Return None immediately for uniform scale items.

SEVERITY:
    Ambiguous instruction    -> 0.50
    Missing unit             -> 0.45
    Unclear branching        -> 0.55
"""

import re
from app.principles.base_rule import BaseRule, Violation


class P019(BaseRule):

    id = "P019"
    description = (
        "Detects ambiguous response task specifications including unclear "
        "instructions, missing units, and undefined branching logic."
    )

    AMBIGUOUS_INSTRUCTION_SIGNALS = [
        r"\bcheck (all|any)\b",
        r"\bselect (all|any)\b",
        r"\bcircle (all|any)\b",
        r"\bmark (all|any)\b",
    ]

    NUMERIC_WITHOUT_UNIT = [
        r"\bhow many\b(?!.{0,30}\b(times|days|weeks|months|years|"
        r"hours|minutes|people|items)\b)",
        r"\bnumber of\b(?!.{0,30}\b(times|days|people|items|hours)\b)",
    ]

    BRANCHING_SIGNALS = [
        r"\bif yes\b.{0,30}\b(go to|answer|skip)\b",
        r"\bif no\b.{0,30}\b(go to|answer|skip)\b",
        r"\bskip to\b",
        r"\bgo to question\b",
        r"\bif applicable\b",
    ]

    def evaluate(self, item: dict) -> Violation | None:
        text = self._get_text(item).lower()
        scale = item.get("scale", {})

        # Gate: uniform Likert scale — task is clearly defined
        if scale.get("points", 0) > 0 and scale.get("labels"):
            return None

        signals = []

        ambig = [p for p in self.AMBIGUOUS_INSTRUCTION_SIGNALS
                 if re.search(p, text)]
        if ambig:
            signals.append(
                "ambiguous response instruction — 'check all' vs "
                "'check one' not specified"
            )

        numeric = [p for p in self.NUMERIC_WITHOUT_UNIT
                   if re.search(p, text)]
        if numeric:
            signals.append(
                "numeric response requested without unit specification"
            )

        branching = [p for p in self.BRANCHING_SIGNALS
                     if re.search(p, text)]
        if branching:
            signals.append(
                "branching/skip logic detected without clear navigation"
            )

        if not signals:
            return None

        severity_map = {"ambiguous": 0.50, "numeric": 0.45, "branching": 0.55}
        severity = 0.55 if branching else (0.50 if ambig else 0.45)

        return Violation(
            principle=self.id,
            severity=round(severity, 2),
            evidence=(
                "Response task specification problem(s) detected. "
                "Signal(s): " + " | ".join(signals)
            )
        )