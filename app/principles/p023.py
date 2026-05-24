"""
app/principles/p023.py

PRINCIPLE: P023 — Behavior Coding as Quality Signal
SOURCE: Fowler & Cannell — Behavior Coding as a Tool for Evaluating Survey
        Questions, in Schwarz & Sudman (eds.), 1996
        Presser et al. — Methods for Testing and Evaluating Survey Questions
OPERATIONALIZABILITY: High (as proxy)
CONFIDENCE: Medium

WHAT THIS RULE CHECKS:
    In real behavior coding, trained interviewers administer surveys
    and score specific behaviors (respondent confusion, requests for
    clarification, item skipping) as signals of problematic items.
    Items producing frequent behavior codes are flagged for redesign.

    This rule simulates behavior coding by treating RULE CO-OCCURRENCE
    as a proxy for behavioral signals:
        - Multiple rules firing on the same item ≈ multiple behavior codes
        - High co-occurrence ≈ high behavior coding frequency
        - Items with 3+ rules firing are high-priority rewrite candidates

    This is explicitly a META-RULE:
        - It adds NO new detection signals
        - It aggregates signals already produced by P001-P022
        - It produces a co-occurrence summary, not new violations

    TWO OUTPUTS:

    OUTPUT 1 — High co-occurrence item flags:
        Items where 3+ rules fired simultaneously.
        These are the instrument's highest-priority rewrite candidates.

    OUTPUT 2 — Systemic pattern detection:
        If a specific rule fires on more than 40% of items,
        this indicates a systemic instrument-level problem,
        not just isolated item issues.

DESIGN NOTE:
    P023 requires violation data from previous rules to work.
    It accesses this through a pre-computed violation_summary dict
    passed alongside the items list.
    See registry.py for how this is handled.

BOUNDARY WITH P025:
    P023 flags high co-occurrence items for attention.
    P025 produces a numeric validity score from all violations.
    P023 = which items need urgent rewriting?
    P025 = how valid is the instrument overall?

SEVERITY:
    Systemic pattern (rule > 40% items) + high co-occurrence -> 0.80
    High co-occurrence items only                            -> 0.65
    Systemic pattern only                                    -> 0.55
"""

from app.principles.base_rule import BaseRule, InstrumentViolation


class P023(BaseRule):

    id = "P023"
    description = (
        "Meta-rule: detects high rule co-occurrence as a proxy for "
        "behavior coding signals, flagging items needing urgent rewriting "
        "and systemic instrument-level quality problems."
    )

    # Minimum rules fired on same item to flag high co-occurrence
    CO_OCCURRENCE_THRESHOLD = 3

    # Fraction of items a rule must fire on to flag systemic problem
    SYSTEMIC_THRESHOLD = 0.40

    def is_instrument_level(self) -> bool:
        return True

    def evaluate_instrument(self, items: list) -> list | None:
        """
        Evaluate rule co-occurrence patterns across the instrument.

        NOTE: This rule requires violation_summary to be injected
        into each item dict under the key '_violations_count' and
        '_rules_fired' before calling. The registry handles this
        by passing pre-computed data.

        For standalone use, pass items with '_rules_fired' populated.

        Args:
            items (list): Item dicts, optionally enriched with
                         '_rules_fired' list per item.

        Returns:
            list[InstrumentViolation] if patterns detected, else None.
        """
        if not items:
            return None

        total = len(items)
        problems = []

        # --- Output 1: High co-occurrence items ---
        high_co_items = []
        rule_fire_counts = {}

        for item in items:
            rules_fired = item.get("_rules_fired", [])
            item_id = item.get("item_id")

            # Count per-rule fires for systemic detection
            for rule_id in rules_fired:
                rule_fire_counts[rule_id] = (
                    rule_fire_counts.get(rule_id, 0) + 1
                )

            # Flag high co-occurrence
            if len(rules_fired) >= self.CO_OCCURRENCE_THRESHOLD:
                high_co_items.append((item_id, len(rules_fired), rules_fired))

        # --- Output 2: Systemic patterns ---
        systemic_rules = [
            (rule_id, count)
            for rule_id, count in rule_fire_counts.items()
            if count / total >= self.SYSTEMIC_THRESHOLD
        ]

        if not high_co_items and not systemic_rules:
            return None

        findings = []

        if high_co_items:
            sorted_items = sorted(
                high_co_items, key=lambda x: x[1], reverse=True
            )
            top_items = sorted_items[:10]
            item_desc = ", ".join(
                f"item {iid} ({count} rules: {rules})"
                for iid, count, rules in top_items[:5]
            )
            if len(top_items) > 5:
                item_desc += f" (and {len(top_items) - 5} more)"

            findings.append((
                0.65,
                f"{len(high_co_items)} item(s) flagged with "
                f"{self.CO_OCCURRENCE_THRESHOLD}+ simultaneous rule violations "
                f"(behavior coding proxy: high problem frequency). "
                f"Top items: {item_desc}",
                [iid for iid, _, _ in sorted_items]
            ))

        if systemic_rules:
            rule_desc = ", ".join(
                f"{rid} ({count}/{total} items = "
                f"{count/total:.0%})"
                for rid, count in sorted(
                    systemic_rules, key=lambda x: x[1], reverse=True
                )
            )
            findings.append((
                0.55,
                f"systemic instrument-level problem detected — "
                f"rule(s) firing on >{self.SYSTEMIC_THRESHOLD:.0%} of items: "
                f"{rule_desc}. This indicates a design-level issue "
                f"requiring instrument-wide revision, not item-by-item fixes.",
                list(range(1, total + 1))
            ))

        if not findings:
            return None

        # Combine into single violation if both present
        if len(findings) == 2:
            severity = 0.80
            evidence = (
                "Behavior coding proxy signals detected. "
                "Finding 1: " + findings[0][1] + " | "
                "Finding 2: " + findings[1][1]
            )
            affected = sorted(set(
                findings[0][2] + findings[1][2]
            ))
        else:
            severity, evidence_part, affected = findings[0]
            evidence = "Behavior coding proxy signal detected. " + evidence_part

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
            "P023 is an instrument-level meta-rule. "
            "Call evaluate_instrument(items) with enriched item dicts."
        )