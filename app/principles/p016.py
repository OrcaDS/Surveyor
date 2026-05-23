"""
app/principles/p016.py

PRINCIPLE: P016 — Leading and Loaded Wording
SOURCE: Fowler — Survey Research Methods, Ch. 6, p. 84–86
        Tourangeau et al. — The Psychology of Survey Response, Ch. 2
        Dillman — Mail and Internet Surveys, Ch. 4
OPERATIONALIZABILITY: High
CONFIDENCE: High

WHAT THIS RULE CHECKS:
    Leading and loaded wording biases responses by embedding directional
    pressure into the question itself — before the respondent has formed
    an independent judgment.

    This is distinct from P005:
        P005 = pressure from self-presentation in item CONTENT
               (respondent is being flattered or presupposed competent)
        P016 = pressure from directional bias in item WORDING
               (the question itself steers toward a specific answer)

    THREE SIGNALS DETECTED:

    SIGNAL 1 — Emotionally valenced terms:
        Words with strong positive or negative emotional charge that
        prime the respondent's evaluation before they form one.
        Positive valence: inspiring, remarkable, empowering, transformative
        Negative valence: toxic, destructive, harmful, corrupt
        In self-report leadership surveys, positive valence terms are
        the primary risk — they frame leadership behaviors as inherently good
        before the respondent evaluates whether they actually are.

    SIGNAL 2 — Presupposition:
        Items that assume a fact is true before asking about it.
        e.g. "I carry out a policy or course of action, mandated by the region"
        — presupposes the respondent does carry it out, asks only about manner.
        e.g. "I ensure quality and accessible education"
        — presupposes this is happening, asks only about commitment to it.
        Detected by: factive verbs + embedded clauses presenting facts as given.

    SIGNAL 3 — Authority/institutional loading:
        References to institutional authority (DepEd, Department of Education,
        laws, rules, mandates) embedded within items measuring voluntary
        leadership behavior. These create compliance pressure that conflates
        institutional obligation with personal leadership disposition.

BOUNDARY WITH P005:
    P005 = self-aggrandizing stems and competence presupposition
           (the respondent is being flattered)
    P016 = emotionally valenced terms and institutional authority loading
           (the question is steering the answer)
    Both produce directional bias but from different sources.
    An item can trigger both — violations are distinct.

BOUNDARY WITH P003:
    P003 fires on terms with multiple valid interpretations (ambiguity).
    P016 fires on terms with directional evaluative charge (bias).
    A term can be ambiguous without being loaded, and loaded without
    being ambiguous. They are orthogonal problems.

SEVERITY:
    1 signal detected -> 0.40
    2 signals detected -> 0.65
    3 signals detected -> 0.80

PROXY NOTE:
    Emotional valence is context-dependent. A term positive in one domain
    may be neutral or negative in another. This rule uses a curated list
    grounded in survey methodology literature for leadership/organizational
    contexts. Cross-domain surveys require list expansion.
"""

import re
from app.principles.base_rule import BaseRule, Violation


class P016(BaseRule):

    id = "P016"
    description = (
        "Detects leading and loaded wording that embeds directional pressure "
        "into the item before the respondent forms an independent judgment."
    )

    # ------------------------------------------------------------------
    # SIGNAL 1 — Emotionally valenced terms
    # Positive valence terms dominant in leadership self-report surveys.
    # ------------------------------------------------------------------
    POSITIVE_VALENCE_TERMS = [
        r"\binspiring\b",
        r"\binspire\b",
        r"\binspiration\b",
        r"\bremarkable\b",
        r"\bempowering\b",
        r"\bempowerment\b",
        r"\btransformative\b",
        r"\bexceptional\b",
        r"\boutstanding\b",
        r"\bexcellent\b",
        r"\bsuccessful\b",
        r"\bpositive\b",
        r"\bstrong\b",
        r"\beffective\b",
        r"\bsuperior\b",
        r"\belevated\b",
        r"\bproven\b",
        r"\bcredible\b",
        r"\bdecisive\b",
        r"\bsincer\b",        # sincere/sincerely
        r"\bgenuine\b",
        r"\bwholehearted\b",
        r"\bcomplete\b",
    ]

    NEGATIVE_VALENCE_TERMS = [
        r"\btoxic\b",
        r"\bdestructive\b",
        r"\bharmful\b",
        r"\bcorrupt\b",
        r"\bmanipulative\b",
        r"\bcoercive\b",
        r"\bintimidating\b",
        r"\bexploitative\b",
        r"\bpunitive\b",
        r"\boppressive\b",
    ]

    # ------------------------------------------------------------------
    # SIGNAL 2 — Presupposition markers
    # Factive verbs and constructions that present embedded clauses as
    # established facts rather than matters for the respondent to evaluate.
    # ------------------------------------------------------------------
    PRESUPPOSITION_PATTERNS = [
        r"\bi ensure\b",
        r"\bi guarantee\b",
        r"\bi make sure\b",
        r"\bi maintain\b",
        r"\bi carry out\b",
        r"\bi implement\b",
        r"\bi fulfill\b",
        r"\bi accomplish\b",
        r"\bi succeed\b",
        r"\bi manage to\b",
        r"\bi am able to\b",
        r"\bi have the ability\b",
        r"\bi have the authority\b",
        r"\bi have the power\b",
    ]

    # ------------------------------------------------------------------
    # SIGNAL 3 — Authority/institutional loading
    # References to institutional authority embedded in leadership items.
    # ------------------------------------------------------------------
    AUTHORITY_REFERENCES = [
        r"\bdepartment of education\b",
        r"\bdeped\b",
        r"\bthe department\b",
        r"\bthe region\b",
        r"\bmandated by\b",
        r"\bmandate\b",
        r"\bby law\b",
        r"\bunder the law\b",
        r"\bpolicies of the department\b",
        r"\brules and.{0,10}laws\b",
        r"\blaws\b.{0,20}\bcontrol\b",
        r"\bunderpinned by rules\b",
        r"\bunderpinned by.{0,10}laws\b",
    ]

    # ------------------------------------------------------------------
    # SUPPRESSION — terms that look loaded but are neutral in context
    # ------------------------------------------------------------------
    SUPPRESSED_TERMS = [
        "positive reinforcement",   # technical psychology term, not loaded
        "positive relationship",    # relational descriptor, not evaluative push
        "complete knowledge",       # P001/P003 territory, not valence loading
        "complete and total",       # intensity, handled by P001
    ]

    def evaluate(self, item: dict) -> Violation | None:
        """
        Check a single item for leading and loaded wording signals.

        Args:
            item (dict): Parsed survey item from SurveyParser.

        Returns:
            Violation if leading/loaded signals detected, else None.
        """
        text = self._get_text(item)
        text_lower = text.lower()

        # Apply suppressions first
        scrubbed = text_lower
        for suppressed in self.SUPPRESSED_TERMS:
            scrubbed = scrubbed.replace(suppressed, "[OK]")

        signals = []

        # --- Signal 1: Emotionally valenced terms ---
        pos_hits = [
            re.search(p, scrubbed).group().strip()
            for p in self.POSITIVE_VALENCE_TERMS
            if re.search(p, scrubbed)
        ]
        neg_hits = [
            re.search(p, scrubbed).group().strip()
            for p in self.NEGATIVE_VALENCE_TERMS
            if re.search(p, scrubbed)
        ]
        all_valence_hits = pos_hits + neg_hits

        if all_valence_hits:
            polarity = []
            if pos_hits:
                polarity.append(f"positive: {', '.join(repr(h) for h in pos_hits)}")
            if neg_hits:
                polarity.append(f"negative: {', '.join(repr(h) for h in neg_hits)}")
            signals.append(
                f"emotionally valenced term(s) detected — "
                f"primes respondent evaluation before judgment formed. "
                f"{' | '.join(polarity)}"
            )

        # --- Signal 2: Presupposition ---
        presup_hits = [
            re.search(p, scrubbed).group().strip()
            for p in self.PRESUPPOSITION_PATTERNS
            if re.search(p, scrubbed)
        ]
        if presup_hits:
            signals.append(
                f"presupposition marker(s) detected: "
                f"{', '.join(repr(h) for h in presup_hits)} — "
                f"item presents embedded claim as established fact, "
                f"not as matter for respondent evaluation"
            )

        # --- Signal 3: Authority/institutional loading ---
        authority_hits = [
            re.search(p, scrubbed).group().strip()
            for p in self.AUTHORITY_REFERENCES
            if re.search(p, scrubbed)
        ]
        if authority_hits:
            signals.append(
                f"institutional authority reference(s): "
                f"{', '.join(repr(h) for h in authority_hits)} — "
                f"invoking institutional mandate conflates obligation "
                f"with voluntary leadership disposition"
            )

        if not signals:
            return None

        severity_map = {1: 0.40, 2: 0.65}
        severity = severity_map.get(len(signals), 0.80)

        evidence = (
            "Leading/loaded wording detected — directional pressure "
            "embedded in item wording before respondent forms judgment. "
            "Signal(s): " + " | ".join(signals)
        )

        return Violation(
            principle=self.id,
            severity=round(severity, 2),
            evidence=evidence
        )