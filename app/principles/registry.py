"""
app/principles/registry.py

The Principle Registry — orchestrates all rule evaluation.

RESPONSIBILITIES:
    1. Hold all registered rules in order
    2. Detect whether each rule is item-level or instrument-level
    3. Run the correct interface for each rule type
    4. Collect and return all violations in a structured result

USAGE:
    from app.principles.registry import PrincipleRegistry

    registry = PrincipleRegistry()
    results = registry.evaluate(survey.items)

    results.item_violations      # dict: item_id -> list of Violations
    results.instrument_violations # list of InstrumentViolations
    results.summary              # dict: rule_id -> violation count

DESIGN NOTES:
    - Rules are evaluated in registration order (P001 first, P025 last)
    - Item-level rules run once per item
    - Instrument-level rules run once on the full item list
    - Errors in individual rules are caught and logged without
      stopping the rest of the evaluation — one bad rule should
      never crash the whole engine
"""

from dataclasses import dataclass, field
from typing import Optional
from app.principles.base_rule import BaseRule, Violation, InstrumentViolation


# ----------------------------------------------------------------------
# RESULTS CONTAINER
# ----------------------------------------------------------------------

@dataclass
class EvaluationResults:
    """
    Container for all violations produced by a full registry run.

    Attributes:
        item_violations (dict):
            Maps item_id (int) -> list of Violation objects.
            Only contains entries for items that had at least one violation.

        instrument_violations (list):
            List of InstrumentViolation objects from instrument-level rules.

        rule_errors (list):
            List of (rule_id, error_message) tuples for any rules that
            threw exceptions during evaluation. For diagnostics only.

        summary (dict):
            Maps rule_id -> number of violations it produced.
            Includes both item-level and instrument-level counts.
    """
    item_violations: dict = field(default_factory=dict)
    instrument_violations: list = field(default_factory=list)
    rule_errors: list = field(default_factory=list)
    summary: dict = field(default_factory=dict)

    def total_item_violations(self) -> int:
        """Total number of item-level violations across all rules and items."""
        return sum(len(v) for v in self.item_violations.values())

    def total_instrument_violations(self) -> int:
        """Total number of instrument-level findings."""
        return len(self.instrument_violations)

    def violations_for_item(self, item_id: int) -> list:
        """Return all violations for a specific item ID."""
        return self.item_violations.get(item_id, [])

    def items_with_violations(self) -> list:
        """Return sorted list of item IDs that have at least one violation."""
        return sorted(self.item_violations.keys())

    def highest_severity_items(self, top_n: int = 10) -> list:
        """
        Return the top N items ranked by their maximum single violation severity.

        Returns:
            list of (item_id, max_severity) tuples, sorted descending.
        """
        ranked = []
        for item_id, violations in self.item_violations.items():
            max_sev = max(v.severity for v in violations)
            ranked.append((item_id, max_sev))
        return sorted(ranked, key=lambda x: x[1], reverse=True)[:top_n]

    def __repr__(self):
        return (
            f"EvaluationResults("
            f"item_violations={self.total_item_violations()}, "
            f"instrument_violations={self.total_instrument_violations()}, "
            f"errors={len(self.rule_errors)})"
        )


# ----------------------------------------------------------------------
# REGISTRY
# ----------------------------------------------------------------------

class PrincipleRegistry:
    """
    Holds all registered principle rules and runs them against a survey.

    Rules are stored in registration order.
    Item-level and instrument-level rules are handled automatically
    based on each rule's is_instrument_level() return value.
    """

    def __init__(self):
        self._rules: list[BaseRule] = []

    def register(self, rule: BaseRule) -> None:
        """
        Register a rule with the registry.

        Args:
            rule (BaseRule): An instantiated rule object.

        Raises:
            TypeError: If rule does not inherit from BaseRule.
            ValueError: If a rule with the same ID is already registered.
        """
        if not isinstance(rule, BaseRule):
            raise TypeError(
                f"Expected a BaseRule instance, got {type(rule).__name__}. "
                f"All rules must inherit from BaseRule."
            )

        existing_ids = [r.id for r in self._rules]
        if rule.id in existing_ids:
            raise ValueError(
                f"Rule '{rule.id}' is already registered. "
                f"Each rule ID must be unique."
            )

        self._rules.append(rule)

    def evaluate(self, items: list) -> EvaluationResults:
        """
        Run all registered rules against the full item list.

        Item-level rules are run once per item.
        Instrument-level rules are run once on the full list.

        Args:
            items (list): Full list of item dicts from SurveyParser.

        Returns:
            EvaluationResults: Collected violations from all rules.
        """
        results = EvaluationResults()

        for rule in self._rules:
            if rule.is_instrument_level():
                self._run_instrument_rule(rule, items, results)
            else:
                self._run_item_rule(rule, items, results)

        return results

    def registered_rules(self) -> list:
        """Return list of registered rule IDs in order."""
        return [r.id for r in self._rules]

    def rule_count(self) -> int:
        """Return total number of registered rules."""
        return len(self._rules)

    # ------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------

    def _run_item_rule(
        self,
        rule: BaseRule,
        items: list,
        results: EvaluationResults
    ) -> None:
        """
        Run an item-level rule against each item individually.
        Catches exceptions per item without stopping evaluation.
        """
        violation_count = 0

        for item in items:
            item_id = item.get("item_id")
            try:
                violation = rule.evaluate(item)
                if violation is not None:
                    if item_id not in results.item_violations:
                        results.item_violations[item_id] = []
                    results.item_violations[item_id].append(violation)
                    violation_count += 1
            except Exception as e:
                results.rule_errors.append((
                    rule.id,
                    f"Error on item {item_id}: {type(e).__name__}: {e}"
                ))

        results.summary[rule.id] = violation_count

    def _run_instrument_rule(
        self,
        rule: BaseRule,
        items: list,
        results: EvaluationResults
    ) -> None:
        """
        Run an instrument-level rule against the full item list.
        Catches exceptions without stopping evaluation.
        """
        try:
            violations = rule.evaluate_instrument(items)
            if violations:
                results.instrument_violations.extend(violations)
                results.summary[rule.id] = len(violations)
            else:
                results.summary[rule.id] = 0
        except Exception as e:
            results.rule_errors.append((
                rule.id,
                f"Instrument-level error: {type(e).__name__}: {e}"
            ))
            results.summary[rule.id] = 0


# ----------------------------------------------------------------------
# FACTORY — builds the default registry with all implemented rules
# ----------------------------------------------------------------------

def build_default_registry() -> PrincipleRegistry:
    """
    Build and return a registry pre-loaded with all implemented rules
    in principle order (P001 first).

    When new rules are implemented, add them here in order.

    Returns:
        PrincipleRegistry: Ready to run against any SurveyData.
    """
    from app.principles.p001 import P001
    from app.principles.p002 import P002
    from app.principles.p003 import P003
    from app.principles.p004 import P004
    from app.principles.p005 import P005
    from app.principles.p006 import P006
    from app.principles.p007 import P007
    from app.principles.p008 import P008
    from app.principles.p015 import P015
    from app.principles.p016 import P016
    from app.principles.p020 import P020

    registry = PrincipleRegistry()
    registry.register(P001())
    registry.register(P002())
    registry.register(P003())
    registry.register(P004())
    registry.register(P005())
    registry.register(P006())
    registry.register(P007())
    registry.register(P008())
    registry.register(P015())
    registry.register(P016())
    registry.register(P020())

    return registry