"""
app/principles/base_rule.py

Abstract base class for all principle rules + Violation data container.

DESIGN CONTRACT:
    Every principle rule must:
        1. Inherit from BaseRule
        2. Define a class-level `id` string (e.g. "P001")
        3. Define a class-level `description` string (one sentence)
        4. Implement evaluate(item) -> Violation | None

    evaluate() receives one parsed item dict from SurveyParser.
    It returns a Violation if the principle is breached, or None if not.

    Nothing else. Rules do not talk to each other.
    Rules do not store state.
    Rules do not know about other items in the survey.
    Rules only look at the single item they are given.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


# ----------------------------------------------------------------------
# VIOLATION — data container
# ----------------------------------------------------------------------

@dataclass
class Violation:
    """
    Represents a single principle breach on a single survey item.

    Attributes:
        principle (str):  The rule ID that fired. e.g. "P002"
        severity  (float): How serious the violation is. 0.0 (minor) → 1.0 (critical)
        evidence  (str):  Plain English explanation of what triggered the rule.
                          This is what appears in the audit report.

    Example:
        Violation(
            principle="P002",
            severity=0.85,
            evidence="Item contains two distinct ideas: 'punish' and 'reward'"
        )
    """
    principle: str
    severity: float
    evidence: str

    def __post_init__(self):
        """Validate fields immediately on creation."""
        if not (0.0 <= self.severity <= 1.0):
            raise ValueError(
                f"Severity must be between 0.0 and 1.0, got {self.severity}"
            )
        if not self.principle.strip():
            raise ValueError("Principle ID cannot be empty.")
        if not self.evidence.strip():
            raise ValueError("Evidence cannot be empty.")

    def to_dict(self) -> dict:
        """Serialize to dictionary for JSON output."""
        return {
            "principle": self.principle,
            "severity": self.severity,
            "evidence": self.evidence
        }


# ----------------------------------------------------------------------
# BASE RULE — abstract interface
# ----------------------------------------------------------------------

class BaseRule(ABC):
    """
    Abstract base class that all principle rules must inherit from.

    Class-level attributes (must be defined in every subclass):
        id          (str): Short rule identifier. e.g. "P001"
        description (str): One-sentence summary of what this rule checks.

    Usage (in registry):
        rule = P001()
        result = rule.evaluate(item)
        if result is not None:
            violations.append(result)
    """

    id: str = NotImplemented
    description: str = NotImplemented

    @abstractmethod
    def evaluate(self, item: dict) -> Violation | None:
        """
        Evaluate a single parsed survey item against this rule.

        Args:
            item (dict): One item dict from SurveyParser. Contains:
                         item_id, text, scale, word_count, is_question, construct

        Returns:
            Violation: If the rule is breached.
            None:      If the item passes this rule cleanly.
        """
        pass

    def _get_text(self, item: dict) -> str:
        """
        Convenience method: safely extract item text.
        Subclasses should use this instead of item["text"] directly.
        """
        return item.get("text", "").strip()

    def __repr__(self):
        return f"<Rule {self.id}: {self.description}>"