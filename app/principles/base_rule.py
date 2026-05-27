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

    INSTRUMENT-LEVEL RULES (P006, P008-P013, P020, P023-P025):
        evaluate_instrument() receives the full list of parsed item dicts.
        Returns a list of InstrumentViolation objects or None if clean.
        These rules evaluate patterns across the full item set.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


# ----------------------------------------------------------------------
# VIOLATION — item-level data container
# ----------------------------------------------------------------------

@dataclass
class Violation:
    """
    Represents a single principle breach on a single survey item.

    Attributes:
        principle (str):    The rule ID that fired. e.g. "P002"
        severity  (float):  How serious the violation is. 0.0 -> 1.0
        evidence  (str):    Plain English explanation. Appears in report.
        signals   (list):   Typed Signal objects that produced this violation.
                            Empty list for rules not yet refactored to
                            typed signals. Populated after Stage 2 refactor.
    """
    principle: str
    severity: float
    evidence: str
    signals: list = field(default_factory=list)

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
            "signals": [s.to_dict() for s in self.signals],
        }

    def signal_types(self) -> list:
        """Return list of SignalType values for this violation."""
        return [s.type for s in self.signals]

    def has_signal(self, signal_type) -> bool:
        """Check if a specific SignalType is present."""
        return signal_type in self.signal_types()

    def mean_confidence(self) -> float:
        """Mean confidence across all signals. Returns 0.0 if no signals."""
        if not self.signals:
            return 0.0
        return sum(s.confidence for s in self.signals) / len(self.signals)


# ----------------------------------------------------------------------
# INSTRUMENT VIOLATION — instrument-level data container
# ----------------------------------------------------------------------

@dataclass
class InstrumentViolation:
    """
    Represents a principle breach detected at the instrument level.

    Attributes:
        principle      (str):   The rule ID that fired.
        severity       (float): Instrument-level severity. 0.0 -> 1.0
        evidence       (str):   Plain English explanation.
        affected_items (list):  item_id values involved.
        signals        (list):  Typed Signal objects. Populated in Stage 2.
    """
    principle: str
    severity: float
    evidence: str
    affected_items: list
    signals: list = field(default_factory=list)

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
            "affected_items": self.affected_items,
            "signals": [s.to_dict() for s in self.signals],
        }


# ----------------------------------------------------------------------
# BASE RULE — abstract interface
# ----------------------------------------------------------------------

class BaseRule(ABC):
    """
    Abstract base class that all principle rules must inherit from.

    Item-level rules implement evaluate(item).
    Instrument-level rules implement evaluate_instrument(items).
    """

    id: str = NotImplemented
    description: str = NotImplemented

    def evaluate(self, item: dict) -> Optional[Violation]:
        """
        Evaluate a single parsed survey item against this rule.
        Override for item-level rules.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} is an instrument-level rule. "
            f"Call evaluate_instrument(items) instead."
        )

    def evaluate_instrument(self, items: list) -> Optional[list]:
        """
        Evaluate the full instrument against this rule.
        Override for instrument-level rules.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} is an item-level rule. "
            f"Call evaluate(item) instead."
        )

    def is_instrument_level(self) -> bool:
        """
        Returns True if this rule operates at the instrument level.
        Override to return True in instrument-level rules.
        """
        return False

    def _get_text(self, item: dict) -> str:
        """Safely extract item text."""
        return item.get("text", "").strip()

    def __repr__(self):
        level = "instrument" if self.is_instrument_level() else "item"
        return f"<Rule {self.id} [{level}-level]: {self.description}>"