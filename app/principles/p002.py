"""
app/principles/p002.py

PRINCIPLE: P002 — The Double-Barreled Question
SOURCE: Fowler — Survey Research Methods (5th ed.), Ch. 6, p. 83-84
OPERATIONALIZABILITY: High
CONFIDENCE: High

REFACTORED: Stage 2 — now produces typed Signal objects.

Detection strategy unchanged. Evidence strings are now generated
from Signal objects rather than hardcoded strings, enabling:
    - Signal-type-specific weighting in P025
    - Cross-principle interaction detection
    - Dashboard filtering by signal category
    - Confidence-aware scoring
"""

import re
from app.principles.base_rule import BaseRule, Violation
from app.principles.signals import Signal, SignalType


class P002(BaseRule):

    id = "P002"
    description = (
        "Detects items that may ask about two distinct concepts simultaneously "
        "(double-barreled questions), forcing uninterpretable responses."
    )

    FUSED_COMPOUNDS = [
        "teaching and non-teaching",
        "non-teaching and teaching",
        "rules and regulations",
        "policies and procedures",
        "goals and objectives",
        "roles and responsibilities",
        "mission and vision",
        "flora and fauna",
        "pros and cons",
        "checks and balances",
        "terms and conditions",
        "parks and recreation",
        "health and safety",
        "law and order",
    ]

    EVALUATIVE_PAIRS = [
        ("reward", "recognition"),
        ("reward", "punishment"),
        ("praise", "criticism"),
        ("vision", "values"),
        ("skill", "knowledge"),
        ("efficiency", "productivity"),
        ("trust", "loyalty"),
        ("motivation", "compliance"),
        ("creativity", "competition"),
        ("empowerment", "compliance"),
        ("direction", "control"),
        ("incentive", "sanction"),
        ("leadership", "communication"),
        ("gratification", "success"),
        ("development", "competenc"),
    ]

    MULTI_PROP_CONNECTORS = [
        r"\bwhile\b",
        r"\bas well as\b",
        r"\bin addition to\b",
        r"\bbut also\b",
        r"\band also\b",
        r"\band at the same time\b",
    ]

    def evaluate(self, item: dict) -> Violation | None:
        text = self._get_text(item)
        text_lower = text.lower()

        # Suppress whitelisted compounds
        scrubbed = text_lower
        for compound in self.FUSED_COMPOUNDS:
            scrubbed = scrubbed.replace(compound, "[FUSED]")

        signals = []

        # --- Check 1: Dual verb phrases ---
        dual_vp = self._check_dual_verb_phrases(scrubbed)
        if dual_vp:
            signals.append(dual_vp)

        # --- Check 2: Evaluative noun pairs ---
        eval_pair = self._check_evaluative_pairs(scrubbed)
        if eval_pair:
            signals.append(eval_pair)

        # --- Check 3: Multi-proposition connectors ---
        multi_prop = self._check_multi_proposition(scrubbed)
        if multi_prop:
            signals.append(multi_prop)

        if not signals:
            return None

        # Severity from signal count
        severity = 0.60 if len(signals) == 1 else 0.85

        # Generate evidence from signals — not hardcoded
        signal_descriptions = " | ".join(s.description for s in signals)
        evidence = (
            "Possible double-barrel — verify manually. "
            f"Signal(s): {signal_descriptions}"
        )

        return Violation(
            principle=self.id,
            severity=round(severity, 2),
            evidence=evidence,
            signals=signals
        )

    # ------------------------------------------------------------------
    # PRIVATE CHECKERS — now return Signal objects
    # ------------------------------------------------------------------

    def _check_dual_verb_phrases(self, text: str) -> Signal | None:
        dual_subject = re.search(
            r"\bi\s+\w+\b.{5,60}?\b(and|or)\b.{1,30}?\bi\s+\w+\b",
            text
        )
        if dual_subject:
            return Signal(
                type=SignalType.DUAL_VERB_PHRASE,
                description="two subject-verb phrases detected in one item",
                terms=[],
                confidence=0.75,
            )

        dual_action = re.search(
            r"\b(affirm|attest|assert|ensure|understand|believe|know|"
            r"guarantee|ascertain|utilize|maintain|develop|engage|"
            r"promote|foster|create|build|establish|use|give|make)\b"
            r".{5,80}?\b(and|or)\b.{1,40}?"
            r"\b(affirm|attest|assert|ensure|understand|believe|know|"
            r"guarantee|ascertain|utilize|maintain|develop|engage|"
            r"promote|foster|create|build|establish|use|give|make)\b",
            text
        )
        if dual_action:
            return Signal(
                type=SignalType.DUAL_VERB_PHRASE,
                description="two distinct action verbs joined by conjunction",
                terms=[],
                confidence=0.70,
            )

        return None

    def _check_evaluative_pairs(self, text: str) -> Signal | None:
        for term_a, term_b in self.EVALUATIVE_PAIRS:
            if term_a in text and term_b in text:
                pattern = (
                    rf"\b{re.escape(term_a)}\b.{{0,60}}"
                    rf"\b(and|or)\b.{{0,60}}"
                    rf"\b{re.escape(term_b)}\b"
                    rf"|\b{re.escape(term_b)}\b.{{0,60}}"
                    rf"\b(and|or)\b.{{0,60}}"
                    rf"\b{re.escape(term_a)}\b"
                )
                if re.search(pattern, text):
                    return Signal(
                        type=SignalType.EVALUATIVE_PAIR,
                        description=(
                            f"evaluative pair joined by conjunction"
                        ),
                        terms=[term_a, term_b],
                        confidence=0.80,
                    )
        return None

    def _check_multi_proposition(self, text: str) -> Signal | None:
        for pattern in self.MULTI_PROP_CONNECTORS:
            if re.search(pattern, text):
                match = re.search(pattern, text)
                connector = match.group().strip()
                return Signal(
                    type=SignalType.MULTI_PROPOSITION_CONNECTOR,
                    description=(
                        f"multi-proposition connector detected: "
                        f"'{connector}'"
                    ),
                    terms=[connector],
                    confidence=0.85,
                )
        return None