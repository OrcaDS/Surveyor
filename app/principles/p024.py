"""
app/principles/p024.py

PRINCIPLE: P024 — Funnel Principle (General Before Specific)
SOURCE: Tourangeau, Rips & Rasinski — The Psychology of Survey Response, Ch. 6
        Fowler — Survey Research Methods, Ch. 5, p. 68–71
        Dillman — Mail and Internet Surveys, Ch. 4, p. 162–165
OPERATIONALIZABILITY: Medium
CONFIDENCE: Medium

WHAT THIS RULE CHECKS:
    The funnel principle states that within a topic domain, general
    questions should precede specific ones. Violating this order
    causes specific items to prime and inflate (or deflate) responses
    on subsequent general items — a form of carry-over effect.

    Example violation:
        Q1: "I use punishment to enforce compliance" (specific)
        Q2: "I maintain control of the schools division" (general)
        → Q1 primes a coercive frame that inflates Q2's rating

    Example correct order:
        Q1: "I maintain control of the schools division" (general)
        Q2: "I use punishment to enforce compliance" (specific)

    This rule evaluates WITHIN construct blocks, not across them.
    Cross-block sequencing is P010's responsibility.

DETECTION STRATEGY:
    STEP 1 — Classify each item as GENERAL or SPECIFIC:
        GENERAL markers: broad organizational scope, role-level claims,
            outcome statements, division-wide references
        SPECIFIC markers: named behaviors, specific tools or methods,
            conditional actions, single-instance claims

    STEP 2 — Within each construct block, check ordering:
        If a SPECIFIC item precedes a GENERAL item on the same topic,
        flag the pair as a funnel violation.

    STEP 3 — Report affected item pairs with evidence.

BOUNDARY WITH P010:
    P010 = carry-over contamination between adjacent items / block transitions
    P024 = general-before-specific ordering within a topic domain
    P010 is broader. P024 is a specific sequencing sub-case.
    Both can fire on the same instrument without overlap.

SEVERITY:
    1-3 funnel violations   -> 0.35
    4-6 funnel violations   -> 0.50
    7+ funnel violations    -> 0.65

PROXY NOTE:
    General vs specific classification relies on surface lexical signals.
    True classification requires semantic understanding of construct
    hierarchy — which is Phase 4 (semantic layer) territory.
    This rule's proxy approach will produce false positives on items
    where specificity is contextually determined rather than lexically
    signaled. Treat all findings as flags for manual review.
"""

import re
from app.principles.base_rule import BaseRule, InstrumentViolation


class P024(BaseRule):

    id = "P024"
    description = (
        "Detects violations of the funnel principle where specific "
        "items precede general items within the same construct block, "
        "causing specific-to-general priming effects."
    )

    BLOCK_SIZE = 15

    # ------------------------------------------------------------------
    # GENERAL ITEM MARKERS
    # Broad scope, role-level, outcome-oriented, division-wide claims.
    # ------------------------------------------------------------------
    GENERAL_MARKERS = [
        r"\boverall\b",
        r"\bin general\b",
        r"\bschools division\b",
        r"\bthe organization\b",
        r"\bthe entire\b",
        r"\bmy (role|position|duties|responsibilities)\b",
        r"\bas (a|the) (head|leader|superintendent)\b",
        r"\bin (all|every) (department|school|area)\b",
        r"\borganizational\b",
        r"\bdivision.wide\b",
        r"\bwhole organization\b",
    ]

    # ------------------------------------------------------------------
    # SPECIFIC ITEM MARKERS
    # Named behaviors, specific tools, conditional actions, single instances.
    # ------------------------------------------------------------------
    SPECIFIC_MARKERS = [
        r"\bpunish\b",
        r"\breprimand\b",
        r"\bsuspend\b",
        r"\bterminate\b",
        r"\breward\b",
        r"\bpromotion\b",
        r"\bincentive\b",
        r"\bspecifically\b",
        r"\bin (this|a specific) case\b",
        r"\bif (he|she|they|the subordinate)\b",
        r"\bfor (non-?compliance|disobedience|defiance)\b",
        r"\busing my (charisma|expertise|knowledge|position)\b",
        r"\bthrough (promotions|awards|sanctions)\b",
        r"\bsuspension or termination\b",
        r"\bdisciplinary action\b",
    ]

    def is_instrument_level(self) -> bool:
        return True

    def evaluate_instrument(self, items: list) -> list | None:
        """
        Evaluate item sequencing within construct blocks for funnel
        principle violations.

        Args:
            items (list): Full list of item dicts from SurveyParser.

        Returns:
            list[InstrumentViolation] if funnel violations detected, else None.
        """
        if len(items) < 2:
            return None

        total = len(items)
        violations = []

        # Evaluate within each block
        block_starts = list(range(0, total, self.BLOCK_SIZE))

        for start in block_starts:
            block = items[start:start + self.BLOCK_SIZE]
            block_violations = self._check_block_funnel(block)
            violations.extend(block_violations)

        if not violations:
            return None

        # Severity scales with violation count
        count = len(violations)
        if count >= 7:
            severity = 0.65
        elif count >= 4:
            severity = 0.50
        else:
            severity = 0.35

        # Collect affected item IDs
        affected = []
        for specific_id, general_id in violations:
            affected.extend([specific_id, general_id])
        affected = sorted(set(affected))

        # Build violation pairs description
        pairs_desc = ", ".join(
            f"item {s} (specific) before item {g} (general)"
            for s, g in violations[:5]
        )
        if len(violations) > 5:
            pairs_desc += f" (and {len(violations) - 5} more)"

        evidence = (
            f"Funnel principle violation(s) detected — "
            f"{count} specific item(s) precede general item(s) within "
            f"construct block(s), causing specific-to-general priming. "
            f"Violation pair(s): {pairs_desc}. "
            f"Reorder so general construct items precede specific "
            f"behavioral items within each block."
        )

        return [
            InstrumentViolation(
                principle=self.id,
                severity=round(severity, 2),
                evidence=evidence,
                affected_items=affected
            )
        ]

    def evaluate(self, item: dict):
        raise NotImplementedError(
            "P024 is an instrument-level rule. "
            "Call evaluate_instrument(items) with the full item list."
        )

    # ------------------------------------------------------------------
    # PRIVATE HELPERS
    # ------------------------------------------------------------------

    def _classify_item(self, item: dict) -> str:
        """
        Classify an item as GENERAL, SPECIFIC, or NEUTRAL.

        Returns:
            str: "GENERAL", "SPECIFIC", or "NEUTRAL"
        """
        text = self._get_text(item).lower()

        has_general = any(
            re.search(p, text) for p in self.GENERAL_MARKERS
        )
        has_specific = any(
            re.search(p, text) for p in self.SPECIFIC_MARKERS
        )

        if has_general and not has_specific:
            return "GENERAL"
        if has_specific and not has_general:
            return "SPECIFIC"
        if has_specific and has_general:
            # Both signals — treat as specific (more constrained)
            return "SPECIFIC"
        return "NEUTRAL"

    def _check_block_funnel(self, block: list) -> list:
        """
        Within a single construct block, find SPECIFIC items that
        immediately precede GENERAL items within a 3-item window.

        Look-ahead capped at 3 positions to avoid combinatorial explosion.
        A funnel violation is only meaningful when a specific item
        directly precedes a general one.

        Returns:
            list of (specific_item_id, general_item_id) violation pairs
        """
        LOOK_AHEAD = 3
        classifications = [
            (item["item_id"], self._classify_item(item))
            for item in block
        ]

        violations = []
        seen_pairs = set()

        for i, (id_i, class_i) in enumerate(classifications):
            if class_i != "SPECIFIC":
                continue
            for j in range(i + 1, min(i + LOOK_AHEAD + 1, len(classifications))):
                id_j, class_j = classifications[j]
                if class_j == "GENERAL":
                    pair = (id_i, id_j)
                    if pair not in seen_pairs:
                        violations.append(pair)
                        seen_pairs.add(pair)
                    break

        return violations