"""
app/principles/p002.py

PRINCIPLE: P002 — The Double-Barreled Question (One Question = One Concept)
SOURCE: Fowler — Survey Research Methods (5th ed.), Ch. 6, p. 83–84
OPERATIONALIZABILITY: High
CONFIDENCE: High

WHAT THIS RULE CHECKS:
    A double-barreled question asks about two distinct concepts simultaneously,
    forcing respondents who agree with one but not the other to give an
    uninterpretable answer.

DETECTION STRATEGY (deterministic proxy):
    Full conceptual independence detection requires semantic embeddings (Phase 4).
    At this layer we use syntax as a proxy signal with three checks:

    CHECK 1 — Dual verb phrases:
        "and" / "or" joining two distinct verb phrases in the same stem.
        e.g. "I support X and believe Y" — two separate cognitive acts.
        This is the strongest syntactic signal for a true double-barrel.

    CHECK 2 — Evaluative noun pairs:
        "and" / "or" joining two known evaluative/organizational nouns
        that are independently ratable in leadership/HR contexts.
        e.g. "rewards and recognition", "vision and values"

    CHECK 3 — Multiple "while" / "as well as" connectors:
        Subordinating connectors that introduce a second proposition
        within the same item stem.
        e.g. "X improves efficiency while contributing to development"

SUPPRESSION (known false positives):
    Compound nouns that look like double-barrels but are semantically fused
    are whitelisted and suppressed from flagging.
    e.g. "teaching and non-teaching", "rules and regulations",
         "policies and procedures", "parks and recreation"

SEVERITY:
    Single signal detected  → 0.60
    Multiple signals        → 0.85
    (P002 is high-confidence so base severity is higher than P001)

EVIDENCE MESSAGE:
    Always qualified as "possible double-barrel — verify manually"
    because deterministic syntax cannot measure conceptual independence.
"""

import re
from app.principles.base_rule import BaseRule, Violation


class P002(BaseRule):

    id = "P002"
    description = (
        "Detects items that may ask about two distinct concepts simultaneously "
        "(double-barreled questions), forcing uninterpretable responses."
    )

    # ------------------------------------------------------------------
    # WHITELISTED COMPOUND NOUNS — suppress these from flagging
    # These look like dual concepts but behave as single evaluative units.
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # EVALUATIVE NOUN PAIRS — independently ratable in org/leadership context
    # If both members of a pair appear joined by "and"/"or", flag it.
    # ------------------------------------------------------------------
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
        ("development", "competenc"),   # partial: covers "competency/competencies"
    ]

    # ------------------------------------------------------------------
    # MULTI-PROPOSITION CONNECTORS
    # These introduce a second independent clause within one item.
    # ------------------------------------------------------------------
    MULTI_PROP_CONNECTORS = [
        r"\bwhile\b",
        r"\bas well as\b",
        r"\bin addition to\b",
        r"\bbut also\b",
        r"\band also\b",
        r"\band at the same time\b",
    ]

    def evaluate(self, item: dict) -> Violation | None:
        """
        Check a single item for double-barreled question signals.

        Args:
            item (dict): Parsed survey item from SurveyParser.

        Returns:
            Violation if double-barrel signals detected, else None.
        """
        text = self._get_text(item)
        text_lower = text.lower()

        # Suppress whitelisted compound nouns before any checking
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

        severity = 0.60 if len(signals) == 1 else 0.85
        evidence = (
            "Possible double-barrel — verify manually. "
            "Signal(s): " + " | ".join(signals)
        )

        return Violation(
            principle=self.id,
            severity=round(severity, 2),
            evidence=evidence
        )

    # ------------------------------------------------------------------
    # PRIVATE CHECKERS
    # ------------------------------------------------------------------

    def _check_dual_verb_phrases(self, text: str) -> str | None:
        """
        Detect 'and'/'or' joining two verb phrases.

        Pattern: verb + ... + and/or + verb
        We look for two action verbs within the same clause separated by
        a coordinating conjunction, which strongly suggests two propositions.

        Common survey stem verbs in this instrument:
        affirm, attest, assert, ensure, understand, believe, know,
        guarantee, ascertain, utilize, maintain, develop, use, engage
        """
        # Match: I <verb> ... and/or ... I <verb>  (explicit dual subject)
        dual_subject = re.search(
            r"\bi\s+\w+\b.{5,60}?\b(and|or)\b.{1,30}?\bi\s+\w+\b",
            text
        )
        if dual_subject:
            return "two subject-verb phrases detected in one item"

        # Match: verb phrase + and/or + verb phrase (same subject, two actions)
        # Look for: <verb> X and <verb> Y where verbs are different action words
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
            return "two distinct action verbs joined by conjunction in one item"

        return None

    def _check_evaluative_pairs(self, text: str) -> str | None:
        """
        Detect known evaluative noun pairs joined by 'and' or 'or'.
        Both members of the pair must appear in the text.
        """
        for term_a, term_b in self.EVALUATIVE_PAIRS:
            if term_a in text and term_b in text:
                # Check they are actually joined by and/or (within 10 words)
                pattern = (
                    rf"\b{re.escape(term_a)}\b.{{0,60}}"
                    rf"\b(and|or)\b.{{0,60}}"
                    rf"\b{re.escape(term_b)}\b"
                    rf"|\b{re.escape(term_b)}\b.{{0,60}}"
                    rf"\b(and|or)\b.{{0,60}}"
                    rf"\b{re.escape(term_a)}\b"
                )
                if re.search(pattern, text):
                    return (
                        f"evaluative pair joined by conjunction: "
                        f"'{term_a}' and '{term_b}'"
                    )
        return None

    def _check_multi_proposition(self, text: str) -> str | None:
        """
        Detect subordinating connectors that introduce a second proposition.
        """
        for pattern in self.MULTI_PROP_CONNECTORS:
            if re.search(pattern, text):
                match = re.search(pattern, text)
                return f"multi-proposition connector detected: '{match.group().strip()}'"
        return None