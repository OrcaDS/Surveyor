"""
app/principles/p015.py

PRINCIPLE: P015 — Negative and Double-Negative Wording
SOURCE: Fowler — Survey Research Methods, Ch. 6, p. 86–88
        Tourangeau et al. — The Psychology of Survey Response, Ch. 2
OPERATIONALIZABILITY: High
CONFIDENCE: High

WHAT THIS RULE CHECKS:
    Negated item stems require respondents to perform additional cognitive
    transformation before mapping their answer onto the response scale.
    This increases error, satisficing, and response time.

    Double negatives are especially problematic — they require the respondent
    to reverse polarity twice, often producing answers opposite to intent.

    THREE SIGNALS DETECTED:

    SIGNAL 1 — Main-clause negation:
        Negation in the respondent's own primary clause.
        e.g. "I do not punish without cause"
        Requires mental reversal before scale mapping.
        NOTE: Subordinate-clause negation (describing others) is NOT flagged —
        that is P006's domain for polarity detection.

    SIGNAL 2 — Double negation:
        Two negation signals within the same clause, reversing polarity twice.
        e.g. "I never fail to punish non-compliance"
        Respondents frequently misinterpret these as their literal opposite.

    SIGNAL 3 — Negated prefix terms:
        Words with negative prefixes that invert meaning subtly.
        e.g. "noncompliance", "uncooperative", "ineffective", "inappropriate"
        These are softer negations but still add parsing burden.

BOUNDARY WITH P002:
    P002 fires on conceptual duality — two ideas joined by conjunction.
    P015 fires on negation logic — polarity reversal in the item structure.
    Negated phrases can resemble dual propositions syntactically but the
    violations are distinct and have different fixes:
        P002 fix: split the item into two separate items
        P015 fix: rewrite using positive framing

BOUNDARY WITH P006:
    P006 uses main-clause negation to detect instrument-level polarity.
    P015 uses the same signals to flag item-level cognitive burden.
    They share detection logic but serve different purposes:
        P006 = is the instrument missing negative-polarity items?
        P015 = does this item's negation structure increase error?

SEVERITY:
    Negated prefix terms only    -> 0.20
    Main-clause negation         -> 0.45
    Double negation              -> 0.75

PROXY NOTE:
    Negation detection is reliable for explicit negation markers.
    Semantic negation without syntactic markers
    (e.g. "I avoid punishing unnecessarily") will not be detected.
"""

import re
from app.principles.base_rule import BaseRule, Violation


class P015(BaseRule):

    id = "P015"
    description = (
        "Detects negated and double-negative item wording that forces "
        "cognitive polarity reversal before scale mapping."
    )

    # ------------------------------------------------------------------
    # SIGNAL 1 — Main-clause negation
    # Negation in the respondent's own primary clause only.
    # Subordinate-clause negation excluded (see P006 boundary note).
    # ------------------------------------------------------------------
    MAIN_CLAUSE_NEGATION = [
        r"\bi do not\b",
        r"\bi don't\b",
        r"\bi cannot\b",
        r"\bi can't\b",
        r"\bi would not\b",
        r"\bi won't\b",
        r"\bi never\b",
        r"\bi am not\b",
        r"\bi have not\b",
        r"\bi will not\b",
        r"\bi neither\b",
        r"\bi fail to\b",
        r"\bi am unable\b",
        r"\bi refuse\b",
    ]

    # ------------------------------------------------------------------
    # SIGNAL 2 — Double negation patterns
    # Two negation signals within close proximity reversing polarity twice.
    # ------------------------------------------------------------------
    DOUBLE_NEGATION_PATTERNS = [
        r"\bnever\b.{0,40}\bnot\b",
        r"\bnot\b.{0,40}\bnever\b",
        r"\bnever\b.{0,40}\bno\b",
        r"\bnot\b.{0,40}\bnon\w+",
        r"\bnever\b.{0,40}\bfail\b",
        r"\bnot\b.{0,40}\bwithout\b",
        r"\bwithout\b.{0,40}\bnot\b",
        r"\bcannot\b.{0,40}\bfail\b",
        r"\bunable\b.{0,40}\bnot\b",
    ]

    # ------------------------------------------------------------------
    # SIGNAL 3 — Negated prefix terms
    # Words with negative prefixes that invert meaning subtly.
    # ------------------------------------------------------------------
    NEGATED_PREFIX_TERMS = [
        r"\bnoncompliance\b",
        r"\bnon-compliance\b",
        r"\buncooperative\b",
        r"\bineffective\b",
        r"\binappropriate\b",
        r"\bincapable\b",
        r"\bdisobey\b",
        r"\bdisobedience\b",
        r"\bnoncompliant\b",
        r"\bdisregard\b",
        r"\bdefiance\b",
        r"\bdefy\b",
        r"\bdeter\b",
        r"\bimpede\b",
        r"\bprevent\b",
        r"\bprohibit\b",
        r"\brefuse\b",
        r"\breject\b",
        r"\bresist\b",
        r"\bundermine\b",
    ]

    def evaluate(self, item: dict) -> Violation | None:
        """
        Check a single item for negation-related cognitive burden signals.

        Args:
            item (dict): Parsed survey item from SurveyParser.

        Returns:
            Violation if negation signals detected, else None.
        """
        text = self._get_text(item).lower()
        signals = []
        highest_severity = 0.0

        # --- Signal 2: Double negation (check first — highest severity) ---
        double_neg_hits = [
            p for p in self.DOUBLE_NEGATION_PATTERNS
            if re.search(p, text)
        ]
        if double_neg_hits:
            signals.append(
                "double negation detected — polarity reversed twice, "
                "high risk of respondent misinterpretation"
            )
            highest_severity = 0.75

        # --- Signal 1: Main-clause negation ---
        if highest_severity < 0.75:
            main_neg_hits = [
                p for p in self.MAIN_CLAUSE_NEGATION
                if re.search(p, text)
            ]
            if main_neg_hits:
                matched = [
                    re.search(p, text).group().strip()
                    for p in main_neg_hits
                ]
                signals.append(
                    f"main-clause negation detected: "
                    f"{', '.join(repr(m) for m in matched)} — "
                    f"requires mental polarity reversal before scale mapping"
                )
                highest_severity = max(highest_severity, 0.45)

        # --- Signal 3: Negated prefix terms ---
        prefix_hits = [
            re.search(p, text).group().strip()
            for p in self.NEGATED_PREFIX_TERMS
            if re.search(p, text)
        ]
        if prefix_hits:
            signals.append(
                f"negated prefix term(s): "
                f"{', '.join(repr(h) for h in prefix_hits)} — "
                f"subtle polarity inversion adds parsing burden"
            )
            highest_severity = max(highest_severity, 0.20)

        if not signals:
            return None

        evidence = (
            "Negated wording detected — additional cognitive transformation "
            "required before scale mapping increases error rate. "
            "Signal(s): " + " | ".join(signals)
        )

        return Violation(
            principle=self.id,
            severity=round(highest_severity, 2),
            evidence=evidence
        )