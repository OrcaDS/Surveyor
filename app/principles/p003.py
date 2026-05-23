"""
app/principles/p003.py

PRINCIPLE: P003 — Undefined Terms and Ambiguous Concepts
SOURCE: Fowler — Survey Research Methods, Ch. 6, p. 79–82
        Tourangeau et al. — Ch. 2, Section 2.4
OPERATIONALIZABILITY: High
CONFIDENCE: High

WHAT THIS RULE CHECKS:
    Terms that appear clear to the question author but carry multiple valid
    interpretations across different respondents. When respondents use different
    private definitions without signaling it, the resulting data is unreliable
    in proportion to how much definitions vary.

    This is NOT the same as P001:
        P001 = the term has no clear referent for anyone (unmeasurable)
        P003 = the term has different referents for different respondents (ambiguous)

DETECTION CATEGORIES:

    CATEGORY 1 — Role terms without scope definition:
        Formal role nouns like "subordinates", "personnel", "members", "staff"
        that could refer to different subgroups depending on the respondent.
        NOTE: Pronouns (them, they, others) and possessive constructions
        ("my people") are EXCLUDED — these are referential, not ambiguous.
        "my people" in a superintendent survey is contextually scoped.

    CATEGORY 2 — Behavioral terms with no observable referent:
        Terms that describe behaviors but give no observable definition
        of what counts as performing them. Restricted to terms where
        the behavioral referent is genuinely unclear in context.

    CATEGORY 3 — Evaluative terms with no defined standard:
        Terms that require a comparison benchmark that is never provided.

    CATEGORY 4 — Scope terms with no defined boundary:
        Terms implying comprehensiveness that is never defined.
        Excluded: intensity modifiers like "total control", "complete control"
        where the modifier amplifies rather than scopes.

BOUNDARY WITH P001:
    P001 fires when a term is fundamentally unmeasurable (no referent exists).
    P003 fires when a term is measurable but defined differently by different
    respondents (multiple referents exist, none specified).

BOUNDARY WITH P016:
    P016 fires when a term carries directional bias.
    P003 fires when a term carries interpretive ambiguity.
    A term can be both — but the violations are distinct.

SEVERITY:
    1 category triggered  → 0.30
    2 categories triggered → 0.50
    3+ categories triggered → 0.70

PROXY NOTE:
    True ambiguity requires population-level semantic variation data.
    This rule uses a curated term list grounded in Fowler's documented
    examples of problematic survey vocabulary. Domain-specific ambiguity
    outside this list will not be detected.
"""

import re
from app.principles.base_rule import BaseRule, Violation


class P003(BaseRule):

    id = "P003"
    description = (
        "Detects terms that carry multiple valid interpretations across "
        "respondents, producing unreliable data when left undefined."
    )

    # ------------------------------------------------------------------
    # CATEGORY 1 — Formal role nouns without scope definition
    # Restricted to formal organizational nouns only.
    # Pronouns and possessive constructions excluded (referential, not ambiguous).
    # ------------------------------------------------------------------
    ROLE_TERMS = [
        "subordinates",
        "personnel",
        "members",
        "staff",
        "individuals",
    ]

    # ------------------------------------------------------------------
    # CATEGORY 2 — Behavioral terms with no observable referent
    # Restricted to terms where behavioral referent is genuinely unclear.
    # Removed: "communicate" (too generic), "interact" (same),
    #           "contribute" (too generic), "coordinate" (clear enough).
    # ------------------------------------------------------------------
    BEHAVIORAL_TERMS = [
        "engage",
        "involve",
        "participate",
        "collaborate",
        "facilitate",
        "affiliate",
    ]

    # ------------------------------------------------------------------
    # CATEGORY 3 — Evaluative terms with no defined standard
    # ------------------------------------------------------------------
    EVALUATIVE_TERMS = [
        "effective",
        "appropriate",
        "proper",
        "adequate",
        "successful",
        "quality",
        "excellent",
    ]

    # ------------------------------------------------------------------
    # CATEGORY 4 — Scope terms with no defined boundary
    # Removed: "total", "complete", "full", "entire", "whole", "all", "every"
    # when used as intensity modifiers (e.g. "total control", "complete authority")
    # These only fire when followed by an undefined domain noun, not a
    # clearly scoped noun like "control", "authority", "knowledge".
    # ------------------------------------------------------------------
    SCOPE_TERMS = [
        "overall",
        "general",
    ]

    # ------------------------------------------------------------------
    # SUPPRESSION — contextually scoped phrases in this instrument
    # These match signal terms but are unambiguous in context.
    # ------------------------------------------------------------------
    SUPPRESSED_IN_CONTEXT = [
        "my people",                # possessive + relational — contextually scoped
        "my subordinates",          # possessive — scoped to respondent's reports
        "all departments",          # scoped by "departments"
        "entire schools division",  # scoped by "schools division"
        "total control",            # intensity modifier, not scope claim
        "complete control",         # intensity modifier
        "full control",             # intensity modifier
        "good ideas",               # colloquial, not evaluative claim
        "good persuasion",          # domain-qualified
        "effective and efficient",  # paired term, standard management phrase
        "quality and accessible",   # policy language, scoped by DepEd context
    ]

    def evaluate(self, item: dict) -> Violation | None:
        """
        Check a single item for undefined or ambiguous terms.

        Args:
            item (dict): Parsed survey item from SurveyParser.

        Returns:
            Violation if ambiguous terms detected, else None.
        """
        text = self._get_text(item)
        text_lower = text.lower()

        # Apply suppression before any checking
        scrubbed = text_lower
        for suppressed in self.SUPPRESSED_IN_CONTEXT:
            scrubbed = scrubbed.replace(suppressed, "[OK]")

        findings = []

        # --- Category 1: Role terms ---
        role_hits = self._find_word_matches(self.ROLE_TERMS, scrubbed)
        if role_hits:
            findings.append(
                f"undefined scope role term(s): "
                f"{', '.join(repr(t) for t in role_hits)}"
            )

        # --- Category 2: Behavioral terms ---
        behavioral_hits = self._find_word_matches(self.BEHAVIORAL_TERMS, scrubbed)
        if behavioral_hits:
            findings.append(
                f"behaviorally undefined term(s): "
                f"{', '.join(repr(t) for t in behavioral_hits)}"
            )

        # --- Category 3: Evaluative terms ---
        evaluative_hits = self._find_word_matches(self.EVALUATIVE_TERMS, scrubbed)
        if evaluative_hits:
            findings.append(
                f"evaluative term(s) without defined standard: "
                f"{', '.join(repr(t) for t in evaluative_hits)}"
            )

        # --- Category 4: Scope terms ---
        scope_hits = self._find_word_matches(self.SCOPE_TERMS, scrubbed)
        if scope_hits:
            findings.append(
                f"undefined scope term(s): "
                f"{', '.join(repr(t) for t in scope_hits)}"
            )

        if not findings:
            return None

        severity_map = {1: 0.30, 2: 0.50}
        severity = severity_map.get(len(findings), 0.70)

        evidence = "Ambiguous undefined term(s) detected. " + " | ".join(findings)

        return Violation(
            principle=self.id,
            severity=round(severity, 2),
            evidence=evidence
        )

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _find_word_matches(self, term_list: list, text: str) -> list:
        """
        Find whole-word matches from a term list in the given text.
        Uses word boundary matching to avoid partial hits.

        Args:
            term_list (list): List of terms to search for.
            text (str):       Lowercased, suppression-applied item text.

        Returns:
            list: Terms that matched, deduplicated, in order of appearance.
        """
        hits = []
        seen = set()
        for term in term_list:
            pattern = rf"\b{re.escape(term)}\b"
            if re.search(pattern, text) and term not in seen:
                hits.append(term)
                seen.add(term)
        return hits