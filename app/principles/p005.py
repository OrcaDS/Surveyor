"""
app/principles/p005.py

PRINCIPLE: P005 — Social Desirability Bias
SOURCE: Tourangeau, Rips & Rasinski — The Psychology of Survey Response, Ch. 8
        Fowler — Survey Research Methods, Ch. 6, p. 90–91
        Dillman — Mail and Internet Surveys, Ch. 2
OPERATIONALIZABILITY: High
CONFIDENCE: High

WHAT THIS RULE CHECKS:
    Social desirability bias occurs when item wording creates pressure on
    respondents to answer in ways that make them appear competent, ethical,
    virtuous, or authoritative — regardless of their actual beliefs or behaviors.

    This is a RESPONSE PROCESS phenomenon:
        The respondent's answer reflects self-presentation goals,
        not honest assessment of the construct being measured.

    This rule detects THREE surface markers of social desirability pressure:

    SIGNAL 1 — Self-aggrandizing stem verbs:
        Verbs that frame the respondent as already asserting, guaranteeing,
        or affirming something before the content is even stated.
        e.g. "I affirm that...", "I attest that...", "I guarantee..."
        These presuppose the respondent holds the position described,
        making disagreement feel like self-contradiction.

    SIGNAL 2 — Virtuous self-attribution:
        Items that attribute positive traits or ethical standing to the
        respondent directly in the item stem.
        e.g. "I am well trained", "I have superior knowledge",
             "I practice what I preach", "I treat my people with respect"
        Disagreeing with these items requires the respondent to
        actively self-deprecate, which most respondents avoid.

    SIGNAL 3 — Authority/competence presupposition:
        Items that presuppose the respondent's authority or competence
        as a given, asking only about the degree or manner of its expression.
        e.g. "I have the ability to...", "I have the authority to...",
             "I have the power to...", "I have the superior knowledge..."
        These are not neutral — they embed a flattering assumption.

BOUNDARY WITH P006:
    P005 = item-level bias from self-presentation pressure in content
    P006 = instrument-level bias from uniform positive polarity across all items
    Both produce upward response bias but from different mechanisms.
    P005 fires per item. P006 fires on the instrument as a whole.

BOUNDARY WITH P016:
    P016 = directional bias from leading or loaded question WORDING
    P005 = directional bias from self-presentation pressure in CONTENT
    An item can trigger both: loaded wording (P016) in a self-aggrandizing
    stem (P005) — but the violations are distinct and have different fixes.

SEVERITY:
    1 signal detected  → 0.40
    2 signals detected → 0.65
    3 signals detected → 0.80

PROXY NOTE:
    Social desirability is a response process phenomenon — not purely lexical.
    Items without these surface markers can still produce socially desirable
    responses (especially in hierarchical organizational contexts), and vice versa.
    This rule detects high-probability surface indicators, not the phenomenon itself.
"""

import re
from app.principles.base_rule import BaseRule, Violation


class P005(BaseRule):

    id = "P005"
    description = (
        "Detects item wording that pressures respondents toward socially "
        "desirable responses through self-aggrandizing stems, virtuous "
        "self-attribution, or authority/competence presupposition."
    )

    # ------------------------------------------------------------------
    # SIGNAL 1 — Self-aggrandizing stem verbs
    # These appear at the START of the item stem and frame the respondent
    # as already asserting or guaranteeing the content that follows.
    # Only flagged when they appear as the primary verb of the item stem.
    # ------------------------------------------------------------------
    AGGRANDIZING_STEMS = [
        r"^i affirm\b",
        r"^i attest\b",
        r"^i assert\b",
        r"^i guarantee\b",
        r"^i ascertain\b",
        r"^i assure\b",
        r"^i certify\b",
        r"^i declare\b",
        r"^i proclaim\b",
    ]

    # ------------------------------------------------------------------
    # SIGNAL 2 — Virtuous self-attribution phrases
    # These directly attribute positive traits to the respondent.
    # Disagreement requires active self-deprecation.
    # ------------------------------------------------------------------
    VIRTUOUS_ATTRIBUTION = [
        r"\bi am well trained\b",
        r"\bi practice what i preach\b",
        r"\bi treat my people with respect\b",
        r"\bi respect\b",
        r"\bi care\b",
        r"\bi am capable\b",
        r"\bi am a strong\b",
        r"\bi am well[- ]trained\b",
        r"\bi always place\b",
        r"\bi keep and commit\b",
        r"\bi know that i possess\b",
    ]

    # ------------------------------------------------------------------
    # SIGNAL 3 — Authority/competence presupposition phrases
    # These embed a flattering assumption about the respondent's
    # standing before asking about its expression.
    # ------------------------------------------------------------------
    COMPETENCE_PRESUPPOSITION = [
        r"\bi have the ability to\b",
        r"\bi have the authority to\b",
        r"\bi have the power to\b",
        r"\bi have superior\b",
        r"\bi have the superior\b",
        r"\bi have an elevated\b",
        r"\bi have proven\b",
        r"\bi possess superior\b",
        r"\bi have complete\b",
        r"\bi have the capacity\b",
    ]

    def evaluate(self, item: dict) -> Violation | None:
        """
        Check a single item for social desirability bias signals.

        Args:
            item (dict): Parsed survey item from SurveyParser.

        Returns:
            Violation if social desirability signals detected, else None.
        """
        text = self._get_text(item).lower()
        signals = []

        # --- Signal 1: Self-aggrandizing stem ---
        stem_hits = [
            p for p in self.AGGRANDIZING_STEMS
            if re.search(p, text)
        ]
        if stem_hits:
            # Extract the actual matched phrase for evidence
            matched = [
                re.search(p, text).group().strip()
                for p in stem_hits
            ]
            signals.append(
                f"self-aggrandizing stem verb(s): "
                f"{', '.join(repr(m) for m in matched)}"
            )

        # --- Signal 2: Virtuous self-attribution ---
        virtue_hits = [
            p for p in self.VIRTUOUS_ATTRIBUTION
            if re.search(p, text)
        ]
        if virtue_hits:
            matched = [
                re.search(p, text).group().strip()
                for p in virtue_hits
            ]
            signals.append(
                f"virtuous self-attribution: "
                f"{', '.join(repr(m) for m in matched)}"
            )

        # --- Signal 3: Competence presupposition ---
        competence_hits = [
            p for p in self.COMPETENCE_PRESUPPOSITION
            if re.search(p, text)
        ]
        if competence_hits:
            matched = [
                re.search(p, text).group().strip()
                for p in competence_hits
            ]
            signals.append(
                f"competence/authority presupposition: "
                f"{', '.join(repr(m) for m in matched)}"
            )

        if not signals:
            return None

        severity_map = {1: 0.40, 2: 0.65}
        severity = severity_map.get(len(signals), 0.80)

        evidence = (
            "Social desirability pressure detected — respondents are "
            "unlikely to disagree without self-deprecation. "
            "Signal(s): " + " | ".join(signals)
        )

        return Violation(
            principle=self.id,
            severity=round(severity, 2),
            evidence=evidence
        )