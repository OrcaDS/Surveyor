"""
app/diagnostics/diagnostic_aggregator.py

Converts raw EvaluationResults into structured diagnostic reports.

RESPONSIBILITIES:
    1. Build a ItemDiagnostic object for every survey item
    2. Build an InstrumentDiagnostic summarizing instrument-level findings
    3. Compute per-item composite severity scores
    4. Flag high-priority items (multiple violations, high severity)
    5. Return a SurveyDiagnostic containing everything

DESIGN NOTE:
    The aggregator does NOT add new detection logic.
    It only organizes and enriches what the registry already produced.
    All violations flow downward from the registry unchanged —
    the aggregator adds structure and priority signals on top.

USAGE:
    from app.diagnostics.diagnostic_aggregator import DiagnosticAggregator

    aggregator = DiagnosticAggregator(survey_data, evaluation_results)
    diagnostic = aggregator.aggregate()

    diagnostic.items              # list of ItemDiagnostic
    diagnostic.instrument         # InstrumentDiagnostic
    diagnostic.high_priority_items # items flagged for urgent review
"""

from dataclasses import dataclass, field
from typing import Optional
from app.parser.survey_parser import SurveyData
from app.principles.registry import EvaluationResults


# ----------------------------------------------------------------------
# DATA CONTAINERS
# ----------------------------------------------------------------------

@dataclass
class ItemDiagnostic:
    """
    Full diagnostic report for a single survey item.

    Attributes:
        item_id (int):              The item number.
        text (str):                 The full item text.
        word_count (int):           Word count of the item.
        violations (list):          All Violation objects for this item.
        violation_count (int):      Number of violations.
        rules_fired (list):         List of rule IDs that fired.
        max_severity (float):       Highest single violation severity.
        composite_severity (float): Weighted aggregate severity score.
        priority (str):             "HIGH", "MEDIUM", or "LOW"
        is_high_priority (bool):    True if item needs urgent attention.
    """
    item_id: int
    text: str
    word_count: int
    violations: list
    violation_count: int
    rules_fired: list
    max_severity: float
    composite_severity: float
    priority: str
    is_high_priority: bool

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "text": self.text,
            "word_count": self.word_count,
            "violation_count": self.violation_count,
            "rules_fired": self.rules_fired,
            "max_severity": self.max_severity,
            "composite_severity": self.composite_severity,
            "priority": self.priority,
            "is_high_priority": self.is_high_priority,
            "violations": [v.to_dict() for v in self.violations]
        }


@dataclass
class InstrumentDiagnostic:
    """
    Instrument-level diagnostic summary.

    Attributes:
        total_items (int):              Total items in instrument.
        items_with_violations (int):    Items with at least one violation.
        clean_items (int):              Items with no violations.
        total_item_violations (int):    Sum of all item-level violations.
        instrument_findings (list):     InstrumentViolation objects.
        instrument_finding_count (int): Number of instrument-level findings.
        high_priority_count (int):      Items flagged HIGH priority.
        medium_priority_count (int):    Items flagged MEDIUM priority.
        low_priority_count (int):       Items flagged LOW priority.
        rule_summary (dict):            rule_id -> violation count.
        instrument_validity_risk (str): "HIGH", "MODERATE", or "LOW"
    """
    total_items: int
    items_with_violations: int
    clean_items: int
    total_item_violations: int
    instrument_findings: list
    instrument_finding_count: int
    high_priority_count: int
    medium_priority_count: int
    low_priority_count: int
    rule_summary: dict
    instrument_validity_risk: str

    def to_dict(self) -> dict:
        return {
            "total_items": self.total_items,
            "items_with_violations": self.items_with_violations,
            "clean_items": self.clean_items,
            "total_item_violations": self.total_item_violations,
            "instrument_finding_count": self.instrument_finding_count,
            "high_priority_count": self.high_priority_count,
            "medium_priority_count": self.medium_priority_count,
            "low_priority_count": self.low_priority_count,
            "rule_summary": self.rule_summary,
            "instrument_validity_risk": self.instrument_validity_risk,
            "instrument_findings": [
                f.to_dict() for f in self.instrument_findings
            ]
        }


@dataclass
class SurveyDiagnostic:
    """
    Top-level container for the full survey diagnostic report.

    Attributes:
        survey_metadata (dict):         From SurveyParser metadata.
        instrument (InstrumentDiagnostic): Instrument-level summary.
        items (list[ItemDiagnostic]):   Per-item diagnostics, all items.
        high_priority_items (list):     Subset: HIGH priority items only.
    """
    survey_metadata: dict
    instrument: InstrumentDiagnostic
    items: list
    high_priority_items: list

    def __repr__(self):
        return (
            f"SurveyDiagnostic("
            f"total_items={self.instrument.total_items}, "
            f"violations={self.instrument.total_item_violations}, "
            f"high_priority={self.instrument.high_priority_count}, "
            f"validity_risk={self.instrument.instrument_validity_risk})"
        )

    def to_dict(self) -> dict:
        return {
            "survey_metadata": self.survey_metadata,
            "instrument": self.instrument.to_dict(),
            "items": [item.to_dict() for item in self.items]
        }


# ----------------------------------------------------------------------
# AGGREGATOR
# ----------------------------------------------------------------------

class DiagnosticAggregator:
    """
    Converts EvaluationResults into a structured SurveyDiagnostic.

    Usage:
        aggregator = DiagnosticAggregator(survey_data, evaluation_results)
        diagnostic = aggregator.aggregate()
    """

    # Priority thresholds
    HIGH_PRIORITY_VIOLATIONS = 3      # 3+ rules fired on same item
    HIGH_PRIORITY_SEVERITY = 0.65     # OR max severity >= 0.65
    MEDIUM_PRIORITY_VIOLATIONS = 2    # 2 rules fired
    MEDIUM_PRIORITY_SEVERITY = 0.40   # OR max severity >= 0.40

    # Instrument validity risk thresholds
    HIGH_RISK_VIOLATION_RATIO = 0.60  # 60%+ items have violations
    MODERATE_RISK_VIOLATION_RATIO = 0.35

    def __init__(self, survey_data: SurveyData, results: EvaluationResults):
        """
        Args:
            survey_data (SurveyData):       Output from SurveyParser.
            results (EvaluationResults):    Output from PrincipleRegistry.
        """
        self.survey_data = survey_data
        self.results = results

    def aggregate(self) -> SurveyDiagnostic:
        """
        Run the full aggregation pipeline.

        Returns:
            SurveyDiagnostic: Complete structured diagnostic report.
        """
        item_diagnostics = [
            self._build_item_diagnostic(item)
            for item in self.survey_data.items
        ]

        instrument_diagnostic = self._build_instrument_diagnostic(
            item_diagnostics
        )

        high_priority = [
            d for d in item_diagnostics if d.is_high_priority
        ]

        return SurveyDiagnostic(
            survey_metadata=self.survey_data.metadata,
            instrument=instrument_diagnostic,
            items=item_diagnostics,
            high_priority_items=high_priority
        )

    # ------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------

    def _build_item_diagnostic(self, item: dict) -> ItemDiagnostic:
        """
        Build a full ItemDiagnostic for a single parsed item.

        Args:
            item (dict): One item dict from SurveyParser.

        Returns:
            ItemDiagnostic: Structured diagnostic for this item.
        """
        item_id = item["item_id"]
        violations = self.results.violations_for_item(item_id)
        violation_count = len(violations)
        rules_fired = [v.principle for v in violations]

        max_severity = (
            max(v.severity for v in violations)
            if violations else 0.0
        )

        composite_severity = self._compute_composite_severity(violations)
        priority = self._compute_priority(violation_count, max_severity)
        is_high_priority = priority == "HIGH"

        return ItemDiagnostic(
            item_id=item_id,
            text=item["text"],
            word_count=item["word_count"],
            violations=violations,
            violation_count=violation_count,
            rules_fired=rules_fired,
            max_severity=round(max_severity, 2),
            composite_severity=round(composite_severity, 2),
            priority=priority,
            is_high_priority=is_high_priority
        )

    def _compute_composite_severity(self, violations: list) -> float:
        """
        Compute a composite severity score from multiple violations.

        FORMULA:
            Takes the maximum severity as the base, then adds a
            diminishing contribution from each additional violation.
            This prevents the score from exceeding 1.0 while still
            reflecting that multiple violations compound the problem.

            composite = max_sev + sum(other_sev * 0.15)
            capped at 1.0

        WHY NOT AVERAGE:
            Averaging would make a single severe violation look better
            if paired with minor ones. We want severity to compound,
            not dilute.

        Args:
            violations (list): List of Violation objects for one item.

        Returns:
            float: Composite severity score between 0.0 and 1.0.
        """
        if not violations:
            return 0.0

        severities = sorted(
            [v.severity for v in violations], reverse=True
        )
        composite = severities[0]

        for additional_sev in severities[1:]:
            composite += additional_sev * 0.15

        return min(composite, 1.0)

    def _compute_priority(
        self, violation_count: int, max_severity: float
    ) -> str:
        """
        Assign a priority level to an item based on violation count
        and maximum severity.

        Priority rules (either condition triggers the level):
            HIGH:   violation_count >= 3 OR max_severity >= 0.65
            MEDIUM: violation_count >= 2 OR max_severity >= 0.40
            LOW:    any violations below MEDIUM threshold
            CLEAN:  no violations

        Returns:
            str: "HIGH", "MEDIUM", "LOW", or "CLEAN"
        """
        if violation_count == 0:
            return "CLEAN"

        if (violation_count >= self.HIGH_PRIORITY_VIOLATIONS or
                max_severity >= self.HIGH_PRIORITY_SEVERITY):
            return "HIGH"

        if (violation_count >= self.MEDIUM_PRIORITY_VIOLATIONS or
                max_severity >= self.MEDIUM_PRIORITY_SEVERITY):
            return "MEDIUM"

        return "LOW"

    def _build_instrument_diagnostic(
        self, item_diagnostics: list
    ) -> InstrumentDiagnostic:
        """
        Build the instrument-level diagnostic summary.

        Args:
            item_diagnostics (list): All ItemDiagnostic objects.

        Returns:
            InstrumentDiagnostic: Instrument-level summary.
        """
        total = len(item_diagnostics)
        items_with_violations = sum(
            1 for d in item_diagnostics if d.violation_count > 0
        )
        clean_items = total - items_with_violations

        high_count = sum(
            1 for d in item_diagnostics if d.priority == "HIGH"
        )
        medium_count = sum(
            1 for d in item_diagnostics if d.priority == "MEDIUM"
        )
        low_count = sum(
            1 for d in item_diagnostics if d.priority == "LOW"
        )

        violation_ratio = items_with_violations / total if total > 0 else 0

        if violation_ratio >= self.HIGH_RISK_VIOLATION_RATIO:
            validity_risk = "HIGH"
        elif violation_ratio >= self.MODERATE_RISK_VIOLATION_RATIO:
            validity_risk = "MODERATE"
        else:
            validity_risk = "LOW"

        return InstrumentDiagnostic(
            total_items=total,
            items_with_violations=items_with_violations,
            clean_items=clean_items,
            total_item_violations=self.results.total_item_violations(),
            instrument_findings=self.results.instrument_violations,
            instrument_finding_count=self.results.total_instrument_violations(),
            high_priority_count=high_count,
            medium_priority_count=medium_count,
            low_priority_count=low_count,
            rule_summary=self.results.summary,
            instrument_validity_risk=validity_risk
        )