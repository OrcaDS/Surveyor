"""
app/principles/base_rule.py

Abstract base class for all principle rules + data containers.

DESIGN CONTRACT:
    Every principle rule must:
        1. Inherit from BaseRule
        2. Define a class-level `id` string (e.g. "P001")
        3. Define a class-level `description` string (one sentence)
        4. Implement ONE of:
               evaluate(item)             -> Violation | None
               evaluate_instrument(items) -> list[InstrumentViolation] | None

    ITEM-LEVEL RULES (P001-P005, P007-P017, P019, P021-P022, P024):
        evaluate() receives one parsed item dict from SurveyParser.
        Returns a Violation if the principle is breached, or None if not.
        Rules do not talk to each other.
        Rules do not store state.
        Rules do not know about other items in the survey.

    INSTRUMENT-LEVEL RULES (P006, P010, P018, P020, P023, P025):
        evaluate_instrument() receives the full list of parsed item dicts.
        Returns a list of InstrumentViolation objects or None if clean.
        These rules evaluate patterns across the full item set,
        not individual items in isolation.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


# ----------------------------------------------------------------------
# VIOLATION — item-level data container
# ----------------------------------------------------------------------

@dataclass
class Violation:
    """
    Represents a single principle breach on a single survey item.

    Attributes:
        principle (str):   The rule ID that fired. e.g. "P002"
        severity  (float): How serious the violation is. 0.0 (minor) -> 1.0 (critical)
        evidence  (str):   Plain English explanation of what triggered the rule.
                           This is what appears in the audit report.
    """
    principle: str
    severity: float
    evidence: str

    def __post_init__(self):
        if not (0.0 <= self.severity <= 1.0):
            raise ValueError(
                f"Severity must be between 0.0 and 1.0, got {self.severity}"
            )
        if not self.principle.strip():
            raise ValueError("Principle ID cannot be empty.")
        if not self.evidence.strip():
            raise ValueError("Evidence cannot be empty.")

    def to_dict(self) -> dict:
        return {
            "principle": self.principle,
            "severity": self.severity,
            "evidence": self.evidence
        }


# ----------------------------------------------------------------------
# INSTRUMENT VIOLATION — instrument-level data container
# ----------------------------------------------------------------------

@dataclass
class InstrumentViolation:
    """
    Represents a principle breach detected at the instrument level —
    a pattern across multiple items, not a single item problem.

    Attributes:
        principle   (str):       The rule ID that fired.
        severity    (float):     Instrument-level severity. 0.0 -> 1.0
        evidence    (str):       Plain English explanation of the pattern found.
        affected_items (list):   item_id values involved, if applicable.
                                 Empty list means the whole instrument is affected.
    """
    principle: str
    severity: float
    evidence: str
    affected_items: list

    def __post_init__(self):
        if not (0.0 <= self.severity <= 1.0):
            raise ValueError(
                f"Severity must be between 0.0 and 1.0, got {self.severity}"
            )
        if not self.principle.strip():
            raise ValueError("Principle ID cannot be empty.")
        if not self.evidence.strip():
            raise ValueError("Evidence cannot be empty.")

    def to_dict(self) -> dict:
        return {
            "principle": self.principle,
            "severity": self.severity,
            "evidence": self.evidence,
            "affected_items": self.affected_items
        }


# ----------------------------------------------------------------------
# BASE RULE — abstract interface
# ----------------------------------------------------------------------

class BaseRule(ABC):
    """
    Abstract base class that all principle rules must inherit from.

    Item-level rules implement evaluate(item).
    Instrument-level rules implement evaluate_instrument(items).

    Subclasses must implement exactly one of these two methods.
    The default implementations raise NotImplementedError so that
    the registry knows which interface each rule uses.
    """

    id: str = NotImplemented
    description: str = NotImplemented

    def evaluate(self, item: dict) -> Optional[Violation]:
        """
        Evaluate a single parsed survey item against this rule.

        Override this for item-level rules.
        Do not override if this is an instrument-level rule.

        Args:
            item (dict): One item dict from SurveyParser.

        Returns:
            Violation if the rule is breached, None if not.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} is an instrument-level rule. "
            f"Call evaluate_instrument(items) instead of evaluate(item)."
        )

    def evaluate_instrument(self, items: list) -> Optional[list]:
        """
        Evaluate the full instrument (all items) against this rule.

        Override this for instrument-level rules.
        Do not override if this is an item-level rule.

        Args:
            items (list): Full list of item dicts from SurveyParser.

        Returns:
            list[InstrumentViolation] if violations found, None if clean.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} is an item-level rule. "
            f"Call evaluate(item) instead of evaluate_instrument(items)."
        )

    def is_instrument_level(self) -> bool:
        """
        Returns True if this rule operates at the instrument level.
        The registry uses this to decide which interface to call.

        Item-level rules:      override evaluate()
        Instrument-level rules: override evaluate_instrument() AND
                                set this method to return True.
        """
        return False

    def _get_text(self, item: dict) -> str:
        """
        Convenience method: safely extract item text.
        Subclasses should use this instead of item["text"] directly.
        """
        return item.get("text", "").strip()

    def __repr__(self):
        level = "instrument" if self.is_instrument_level() else "item"
        return f"<Rule {self.id} [{level}-level]: {self.description}>"