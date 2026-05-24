"""
app/principles/p017.py

PRINCIPLE: P017 — Recall-Enabling Strategies
SOURCE: Tourangeau, Rips & Rasinski — The Psychology of Survey Response, Ch. 3
        Fowler — Survey Research Methods, Ch. 6, p. 87–89
OPERATIONALIZABILITY: Medium
CONFIDENCE: Medium

WHAT THIS RULE CHECKS:
    Behavioral frequency items that ask respondents to recall past events
    without providing any cognitive strategies to assist accurate retrieval.

    This pairs with P004:
        P004 = is the recall PERIOD appropriate?
        P017 = does the item provide STRATEGIES to assist recall?

    Both can fire on the same item without overlap.

    RECALL STRATEGIES that reduce error:
        Landmark cuing: "Since the last school year began..."
        Decomposition: "Think about each week separately..."
        Bounding: "Between January and March of this year..."

    DETECTION GATE:
        Only applies to behavioral frequency items.
        Attitude/disposition items do not require recall strategies.
        Same gate as P004: must have behavioral verb + frequency expression.

    SEVERITY:
        Behavioral frequency item with no recall strategy -> 0.45
"""

import re
from app.principles.base_rule import BaseRule, Violation


class P017(BaseRule):

    id = "P017"
    description = (
        "Detects behavioral frequency items that lack recall-enabling "
        "strategies such as landmark cues or decomposition prompts."
    )

    BEHAVIORAL_VERBS = [
        r"\bdid\b", r"\bperformed\b", r"\battended\b",
        r"\breported\b", r"\bwent\b", r"\bvisited\b",
        r"\bused\b", r"\bexercised\b", r"\bconsumed\b",
        r"\bpurchased\b", r"\bcontacted\b", r"\bsubmitted\b",
        r"\bcompleted\b", r"\breceived\b",
    ]

    FREQUENCY_EXPRESSIONS = [
        r"\bhow many times\b", r"\bhow often\b",
        r"\bnumber of times\b", r"\bfrequency of\b",
        r"\btimes per\b", r"\boccasions\b",
    ]

    RECALL_STRATEGY_SIGNALS = [
        r"\bsince\b.{0,20}\b(january|february|march|april|may|june|"
        r"july|august|september|october|november|december)\b",
        r"\bsince the last\b",
        r"\bsince the beginning\b",
        r"\bthink about each\b",
        r"\bthink back\b",
        r"\bfor each\b.{0,20}\bseparately\b",
        r"\bland?mark\b",
        r"\bbetween .{0,20} and .{0,20}\b",
        r"\bduring the period\b",
    ]

    def evaluate(self, item: dict) -> Violation | None:
        text = self._get_text(item).lower()

        # Gate: behavioral frequency item only
        has_verb = any(re.search(p, text) for p in self.BEHAVIORAL_VERBS)
        has_freq = any(
            re.search(p, text) for p in self.FREQUENCY_EXPRESSIONS
        )
        if not (has_verb and has_freq):
            return None

        # Check for recall strategy
        has_strategy = any(
            re.search(p, text) for p in self.RECALL_STRATEGY_SIGNALS
        )
        if has_strategy:
            return None

        return Violation(
            principle=self.id,
            severity=0.45,
            evidence=(
                "Behavioral frequency item provides no recall-enabling "
                "strategy. Respondents must estimate without landmark cues "
                "or decomposition prompts, increasing retrieval error. "
                "Add a time anchor or landmark cue to assist accurate recall."
            )
        )