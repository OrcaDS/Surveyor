"""
app/principles/p010.py

PRINCIPLE: P010 — Question Context / Carry-Over Effects
SOURCE: Tourangeau, Rips & Rasinski — The Psychology of Survey Response, Ch. 6
        Schwarz & Sudman — Context Effects in Social and Psychological Research
OPERATIONALIZABILITY: Medium
CONFIDENCE: Medium

WHAT THIS RULE CHECKS:
    Carry-over effects occur when a respondent's answer to one item
    is systematically influenced by the cognitive frame established
    by preceding items — not by their true attitude on the new item.

    This is an INSTRUMENT-LEVEL rule. It evaluates item SEQUENCES,
    not individual items in isolation.

    THREE SIGNALS:

    SIGNAL 1 — Block transition contamination:
        The last N items of one construct block are adjacent to the
        first N items of the next construct block. Respondents carry
        the cognitive frame from the previous block into the new one,
        inflating or deflating early ratings in the new block.
        Detected by: identifying construct block boundaries and
        flagging the transition zone items.

    SIGNAL 2 — Within-block semantic clustering density:
        Items within a block that share very high lexical overlap
        create response momentum — respondents stop re-evaluating
        and simply repeat prior responses (straight-lining risk).
        Detected by: word overlap ratio between adjacent items.

    SIGNAL 3 — Emotionally escalating sequences:
        Items within a block that escalate in emotional intensity
        (e.g. from "I instruct" to "I punish" to "I threaten")
        anchor subsequent responses at an inflated intensity level.
        Detected by: presence of escalation markers in sequence.

BOUNDARY WITH P024:
    P024 = general-before-specific ordering within a topic domain
    P010 = priming and carry-over contamination between adjacent items
    P010 is broader — it covers emotional and semantic priming,
    not just general-to-specific sequencing violations.

BOUNDARY WITH P007:
    P007 = item-level satisficing from complexity
    P010 = instrument-level carry-over from sequencing
    Different scopes, different fixes.

SEVERITY:
    Block transition only          -> 0.40
    Within-block clustering only   -> 0.35
    Escalating sequence only       -> 0.40
    Two signals                    -> 0.60
    All three signals              -> 0.75

PROXY NOTE:
    True carry-over detection requires experimental split-form designs
    where item order is varied across respondent groups. This rule uses
    structural proxies: lexical overlap, block boundary detection, and
    escalation vocabulary. Results should be treated as flags for
    cognitive interview follow-up, not confirmed carry-over effects.
"""

import re

from app.principles.base_rule import BaseRule, InstrumentViolation
from app.principles.signals import Signal, SignalType


class P010(BaseRule):

    id = "P010"
    description = (
        "Detects carry-over and context effects from item sequencing: "
        "block transition contamination, semantic clustering, and "
        "emotionally escalating sequences."
    )

    # Expected construct block size for detection
    # Surveys with uniform block sizes get more precise detection
    BLOCK_SIZE = 15  # this instrument: 5 blocks of 15 items each

    # Transition zone: items at block boundaries (last N of one, first N of next)
    TRANSITION_ZONE_SIZE = 3

    # Semantic overlap threshold: fraction of shared content words
    # above which adjacent items are considered redundantly clustered
    OVERLAP_THRESHOLD = 0.40

    # Stop words excluded from overlap calculation
    STOP_WORDS = {
        "i", "my", "the", "a", "an", "and", "or", "to", "of", "in",
        "that", "is", "are", "am", "it", "this", "with", "for", "as",
        "by", "at", "be", "have", "has", "do", "not", "can", "will",
        "they", "them", "their", "we", "our", "you", "your", "he",
        "she", "his", "her", "what", "which", "who", "how", "when",
        "if", "then", "because", "but", "so", "from", "on", "all",
        "any", "more", "no", "its", "also", "such", "been", "would",
        "should", "could", "may", "might", "must", "shall", "even",
    }

    # Emotional escalation vocabulary for coercive/authority domains
    ESCALATION_TIERS = [
        # Tier 1 — mild authority
        ["instruct", "direct", "guide", "supervise", "oversee"],
        # Tier 2 — moderate authority
        ["command", "order", "require", "demand", "enforce"],
        # Tier 3 — strong coercion
        ["punish", "reprimand", "sanction", "discipline", "suspend"],
        # Tier 4 — extreme coercion
        ["terminate", "threaten", "coerce", "force", "eliminate"],
    ]

    def is_instrument_level(self) -> bool:
        return True

    def evaluate_instrument(self, items: list) -> list | None:
        """
        Evaluate the full item sequence for carry-over effect risks.

        Args:
            items (list): Full list of item dicts from SurveyParser.

        Returns:
            list[InstrumentViolation] if carry-over risks detected, else None.
        """
        if len(items) < 2:
            return None

        evidence_signals = []
        typed_signals = []
        affected = []

        # --- Signal 1: Block transition contamination ---
        transition_result = self._check_block_transitions(items)
        if transition_result:
            sig_text, aff, signal = transition_result
            evidence_signals.append(sig_text)
            typed_signals.append(signal)
            affected.extend(aff)

        # --- Signal 2: Within-block semantic clustering ---
        clustering_result = self._check_semantic_clustering(items)
        if clustering_result:
            sig_text, aff, signal = clustering_result
            evidence_signals.append(sig_text)
            typed_signals.append(signal)
            affected.extend(aff)

        # --- Signal 3: Emotionally escalating sequences ---
        escalation_result = self._check_escalation(items)
        if escalation_result:
            sig_text, aff, signal = escalation_result
            evidence_signals.append(sig_text)
            typed_signals.append(signal)
            affected.extend(aff)

        if not evidence_signals:
            return None

        severity_map = {1: 0.40, 2: 0.60}
        severity = severity_map.get(len(evidence_signals), 0.75)

        # Adjust for clustering-only (slightly lower)
        if (
            len(typed_signals) == 1
            and typed_signals[0].type == SignalType.SEMANTIC_CLUSTERING
        ):
            severity = 0.35

        affected_items = sorted(set(affected))

        evidence = (
            "Carry-over and context effect risk detected from item sequencing. "
            "Signal(s): " + " | ".join(evidence_signals)
        )

        return [
            InstrumentViolation(
                principle=self.id,
                severity=round(severity, 2),
                evidence=evidence,
                affected_items=affected_items,
                signals=typed_signals
            )
        ]

    def evaluate(self, item: dict):
        raise NotImplementedError(
            "P010 is an instrument-level rule. "
            "Call evaluate_instrument(items) with the full item list."
        )

    # ------------------------------------------------------------------
    # PRIVATE CHECKERS
    # ------------------------------------------------------------------

    def _check_block_transitions(self, items: list) -> tuple | None:
        """
        Detect construct block boundaries and flag transition zones.

        For instruments with uniform block sizes, identifies the items
        at the boundary between blocks and flags them as carry-over risk.

        Returns:
            tuple: (evidence_string, list_of_affected_item_ids) or None
        """
        total = len(items)
        if total < self.BLOCK_SIZE * 2:
            return None

        # Detect block boundaries
        boundaries = []
        pos = self.BLOCK_SIZE
        while pos < total:
            boundaries.append(pos)
            pos += self.BLOCK_SIZE

        if not boundaries:
            return None

        # Collect transition zone item IDs
        transition_items = []
        for boundary in boundaries:
            # Last TRANSITION_ZONE_SIZE items of previous block
            for i in range(
                max(0, boundary - self.TRANSITION_ZONE_SIZE), boundary
            ):
                transition_items.append(items[i]["item_id"])
            # First TRANSITION_ZONE_SIZE items of next block
            for i in range(
                boundary, min(total, boundary + self.TRANSITION_ZONE_SIZE)
            ):
                transition_items.append(items[i]["item_id"])

        block_count = len(boundaries)
        evidence = (
            f"block transition contamination risk at {block_count} "
            f"construct block boundaries — respondents carry prior "
            f"cognitive frame into new construct domain, inflating "
            f"early ratings in each new block. "
            f"Transition zones: items {transition_items}"
        )

        signal = Signal(
            type=SignalType.BLOCK_TRANSITION_CONTAMINATION,
            description=(
                f"block transition contamination at {block_count} "
                f"construct block boundaries"
            ),
            terms=[],
            confidence=0.75,
            metadata={
                "block_count": block_count,
                "transition_items": transition_items,
                "block_size": self.BLOCK_SIZE,
            }
        )

        return evidence, transition_items, signal

    def _check_semantic_clustering(self, items: list) -> tuple | None:
        """
        Detect adjacent items with high lexical overlap.

        High overlap between consecutive items creates response momentum
        where respondents replicate prior responses without re-evaluating.

        Returns:
            tuple: (evidence_string, list_of_affected_item_ids) or None
        """
        high_overlap_pairs = []

        for i in range(len(items) - 1):
            item_a = items[i]
            item_b = items[i + 1]

            overlap = self._compute_overlap(
                item_a["text"], item_b["text"]
            )

            if overlap >= self.OVERLAP_THRESHOLD:
                high_overlap_pairs.append((
                    item_a["item_id"],
                    item_b["item_id"],
                    round(overlap, 2)
                ))

        if not high_overlap_pairs:
            return None

        affected = []
        for a, b, _ in high_overlap_pairs:
            affected.extend([a, b])

        pair_desc = ", ".join(
            f"items {a}-{b} ({o:.0%} overlap)"
            for a, b, o in high_overlap_pairs[:5]  # cap at 5 for readability
        )
        if len(high_overlap_pairs) > 5:
            pair_desc += f" (and {len(high_overlap_pairs) - 5} more)"

        evidence = (
            f"within-block semantic clustering detected — "
            f"{len(high_overlap_pairs)} adjacent item pair(s) share "
            f">={self.OVERLAP_THRESHOLD:.0%} content word overlap, "
            f"increasing straight-lining risk. Pairs: {pair_desc}"
        )

        signal = Signal(
            type=SignalType.SEMANTIC_CLUSTERING,
            description=(
                f"{len(high_overlap_pairs)} adjacent item pair(s) with "
                f">={self.OVERLAP_THRESHOLD:.0%} content word overlap"
            ),
            terms=[],
            confidence=0.70,
            metadata={
                "pair_count": len(high_overlap_pairs),
                "overlap_threshold": self.OVERLAP_THRESHOLD,
            }
        )

        return evidence, affected, signal

    def _check_escalation(self, items: list) -> tuple | None:
        """
        Detect emotionally escalating sequences within construct blocks.

        An escalating sequence is one where items move from lower to higher
        intensity tiers of emotional/coercive vocabulary within a block,
        anchoring later responses at inflated intensity levels.

        Returns:
            tuple: (evidence_string, list_of_affected_item_ids) or None
        """
        escalation_zones = []

        # Check within each block
        total = len(items)
        block_starts = list(range(0, total, self.BLOCK_SIZE))

        for start in block_starts:
            block = items[start:start + self.BLOCK_SIZE]
            tier_sequence = []

            for item in block:
                text = item["text"].lower()
                tier = self._get_escalation_tier(text)
                tier_sequence.append((item["item_id"], tier))

            # Detect upward escalation: tier increases by 2+ within block
            tiers_only = [t for _, t in tier_sequence if t is not None]
            if len(tiers_only) >= 2:
                min_tier = min(tiers_only)
                max_tier = max(tiers_only)
                if max_tier - min_tier >= 2:
                    affected_ids = [
                        iid for iid, t in tier_sequence
                        if t is not None
                    ]
                    escalation_zones.append((
                        affected_ids,
                        min_tier,
                        max_tier
                    ))

        if not escalation_zones:
            return None

        affected = []
        for ids, _, _ in escalation_zones:
            affected.extend(ids)

        evidence = (
            f"emotionally escalating sequence(s) detected in "
            f"{len(escalation_zones)} construct block(s) — "
            f"items escalate from mild authority to coercive vocabulary, "
            f"anchoring respondent frame at elevated intensity and "
            f"inflating subsequent ratings within the block"
        )

        signal = Signal(
            type=SignalType.ESCALATING_SEQUENCE,
            description=(
                f"emotionally escalating sequence(s) in "
                f"{len(escalation_zones)} construct block(s)"
            ),
            terms=[],
            confidence=0.70,
            metadata={
                "escalation_zone_count": len(escalation_zones)
            }
        )

        return evidence, affected, signal

    def _compute_overlap(self, text_a: str, text_b: str) -> float:
        """
        Compute content word overlap ratio between two item texts.

        Jaccard similarity on content word sets (stop words excluded).

        Returns:
            float: Overlap ratio between 0.0 and 1.0
        """
        words_a = set(
            w.lower() for w in re.findall(r"\b\w+\b", text_a)
            if w.lower() not in self.STOP_WORDS
        )
        words_b = set(
            w.lower() for w in re.findall(r"\b\w+\b", text_b)
            if w.lower() not in self.STOP_WORDS
        )

        if not words_a or not words_b:
            return 0.0

        intersection = words_a & words_b
        union = words_a | words_b
        return len(intersection) / len(union)

    def _get_escalation_tier(self, text: str) -> int | None:
        """
        Return the highest escalation tier matched in item text.

        Returns tier index (0-3) or None if no escalation term found.
        """
        highest = None
        for tier_idx, tier_words in enumerate(self.ESCALATION_TIERS):
            for word in tier_words:
                if re.search(rf"\b{re.escape(word)}\b", text):
                    if highest is None or tier_idx > highest:
                        highest = tier_idx
        return highest