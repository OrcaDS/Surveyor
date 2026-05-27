"""
app/principles/signals.py

Typed signal system for the Surveyor AI principle engine.

PURPOSE:
    Separates OBSERVATION (what was detected) from JUDGMENT (how bad it is).

    Rules produce Signal objects describing what they found.
    Violations are generated from signals.
    The scoring engine weights signals by type — not by free-form strings.

    This enables:
        - Cross-principle interaction detection
        - Signal-type-specific weighting in P025
        - Dashboard filtering by signal category
        - Analytics on which signal types dominate an instrument
        - Future: calibrated weights from expert rating data

SIGNAL CATEGORIES:
    Each SignalType belongs to a category:
        WORDING     — how the item is written
        STRUCTURE   — how the item is structured
        SCALE       — how the response scale is designed
        INSTRUMENT  — instrument-level patterns
        META        — aggregated signals from other rules

CONFIDENCE:
    Each Signal carries a confidence score (0.0-1.0) representing
    how certain the detector is that this is a real problem.
    Confidence is separate from severity:
        confidence = how certain is the detection?
        severity   = how bad is it if true?

    High confidence + high severity = strong finding
    Low confidence + high severity  = flag for expert review
    High confidence + low severity  = minor but certain finding
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


# ----------------------------------------------------------------------
# SIGNAL TYPE ENUM
# ----------------------------------------------------------------------

class SignalType(Enum):
    """
    All possible signal types produced by principle rules.

    Grouped by category for analytics and weighting.
    """

    # ------------------------------------------------------------------
    # WORDING signals — how the item text is written
    # ------------------------------------------------------------------

    # P001
    ABSTRACT_CONCEPT = "abstract_concept"
    VAGUE_FREQUENCY_ADVERB = "vague_frequency_adverb"
    UNMEASURABLE_JUDGMENT = "unmeasurable_judgment"

    # P002
    DUAL_VERB_PHRASE = "dual_verb_phrase"
    EVALUATIVE_PAIR = "evaluative_pair"
    MULTI_PROPOSITION_CONNECTOR = "multi_proposition_connector"

    # P003
    UNDEFINED_ROLE_TERM = "undefined_role_term"
    UNDEFINED_BEHAVIORAL_TERM = "undefined_behavioral_term"
    UNDEFINED_EVALUATIVE_TERM = "undefined_evaluative_term"
    UNDEFINED_SCOPE_TERM = "undefined_scope_term"

    # P005
    AGGRANDIZING_STEM = "aggrandizing_stem"
    VIRTUOUS_ATTRIBUTION = "virtuous_attribution"
    COMPETENCE_PRESUPPOSITION = "competence_presupposition"

    # P015
    MAIN_CLAUSE_NEGATION = "main_clause_negation"
    DOUBLE_NEGATION = "double_negation"
    NEGATED_PREFIX_TERM = "negated_prefix_term"

    # P016
    POSITIVE_VALENCE = "positive_valence"
    NEGATIVE_VALENCE = "negative_valence"
    PRESUPPOSITION_MARKER = "presupposition_marker"
    INSTITUTIONAL_AUTHORITY = "institutional_authority"

    # ------------------------------------------------------------------
    # STRUCTURE signals — how the item is constructed
    # ------------------------------------------------------------------

    # P004
    UNANCHORED_RECALL = "unanchored_recall"
    LONG_RECALL_WINDOW = "long_recall_window"

    # P007
    HIGH_WORD_COUNT = "high_word_count"
    ELEVATED_WORD_COUNT = "elevated_word_count"
    HIGH_CLAUSE_DENSITY = "high_clause_density"
    INTEGRATION_DEMAND = "integration_demand"

    # P014
    OPEN_CONSTRUCT_ON_CLOSED_FORMAT = "open_construct_on_closed_format"
    ATTITUDE_ON_FREQUENCY_SCALE = "attitude_on_frequency_scale"

    # P017
    MISSING_RECALL_STRATEGY = "missing_recall_strategy"

    # P019
    AMBIGUOUS_INSTRUCTION = "ambiguous_instruction"
    MISSING_UNIT = "missing_unit"
    UNCLEAR_BRANCHING = "unclear_branching"

    # P021
    AURAL_LENGTH_RISK = "aural_length_risk"
    VISUAL_FORMAT_DEPENDENCY = "visual_format_dependency"

    # P022
    GRID_FORMAT = "grid_format"
    EMPHASIS_ARTIFACT = "emphasis_artifact"

    # P024
    FUNNEL_VIOLATION = "funnel_violation"

    # ------------------------------------------------------------------
    # SCALE signals — response scale design problems
    # ------------------------------------------------------------------

    # P008
    VAGUE_QUANTIFIER_LABEL = "vague_quantifier_label"
    ASYMMETRIC_DISTRIBUTION = "asymmetric_distribution"
    MISSING_ENDPOINT = "missing_endpoint"

    # P009
    NON_SEQUENTIAL_ORDER = "non_sequential_order"
    PRIMACY_RISK = "primacy_risk"

    # P011
    MISSING_MIDPOINT = "missing_midpoint"
    MISSING_DK_OPTION = "missing_dk_option"

    # P012
    OVERLAPPING_OPTIONS = "overlapping_options"
    SUBSET_CONTAINMENT = "subset_containment"
    COVERAGE_GAP = "coverage_gap"

    # P013
    MIXED_SCALE_TYPES = "mixed_scale_types"
    UNDOCUMENTED_REVERSE = "undocumented_reverse"

    # ------------------------------------------------------------------
    # INSTRUMENT signals — patterns across the full instrument
    # ------------------------------------------------------------------

    # P006
    ALL_POSITIVE_POLARITY = "all_positive_polarity"
    HIGH_POSITIVE_POLARITY = "high_positive_polarity"

    # P010
    BLOCK_TRANSITION_CONTAMINATION = "block_transition_contamination"
    SEMANTIC_CLUSTERING = "semantic_clustering"
    ESCALATING_SEQUENCE = "escalating_sequence"

    # P020
    HIGH_ITEM_COUNT = "high_item_count"
    ELEVATED_ITEM_COUNT = "elevated_item_count"
    HIGH_COMPLETION_TIME = "high_completion_time"
    ELEVATED_COMPLETION_TIME = "elevated_completion_time"
    DENSITY_INCREASE = "density_increase"

    # ------------------------------------------------------------------
    # META signals — aggregated from other rules
    # ------------------------------------------------------------------

    # P023
    HIGH_RULE_COOCCURRENCE = "high_rule_cooccurrence"
    SYSTEMIC_RULE_PATTERN = "systemic_rule_pattern"

    # P025
    COMPOSITE_SCORE = "composite_score"


# ----------------------------------------------------------------------
# SIGNAL CATEGORIES — for analytics and weighting
# ----------------------------------------------------------------------

SIGNAL_CATEGORIES = {
    "WORDING": [
        SignalType.ABSTRACT_CONCEPT, SignalType.VAGUE_FREQUENCY_ADVERB,
        SignalType.UNMEASURABLE_JUDGMENT, SignalType.DUAL_VERB_PHRASE,
        SignalType.EVALUATIVE_PAIR, SignalType.MULTI_PROPOSITION_CONNECTOR,
        SignalType.UNDEFINED_ROLE_TERM, SignalType.UNDEFINED_BEHAVIORAL_TERM,
        SignalType.UNDEFINED_EVALUATIVE_TERM, SignalType.UNDEFINED_SCOPE_TERM,
        SignalType.AGGRANDIZING_STEM, SignalType.VIRTUOUS_ATTRIBUTION,
        SignalType.COMPETENCE_PRESUPPOSITION, SignalType.MAIN_CLAUSE_NEGATION,
        SignalType.DOUBLE_NEGATION, SignalType.NEGATED_PREFIX_TERM,
        SignalType.POSITIVE_VALENCE, SignalType.NEGATIVE_VALENCE,
        SignalType.PRESUPPOSITION_MARKER, SignalType.INSTITUTIONAL_AUTHORITY,
    ],
    "STRUCTURE": [
        SignalType.UNANCHORED_RECALL, SignalType.LONG_RECALL_WINDOW,
        SignalType.HIGH_WORD_COUNT, SignalType.ELEVATED_WORD_COUNT,
        SignalType.HIGH_CLAUSE_DENSITY, SignalType.INTEGRATION_DEMAND,
        SignalType.OPEN_CONSTRUCT_ON_CLOSED_FORMAT,
        SignalType.ATTITUDE_ON_FREQUENCY_SCALE,
        SignalType.MISSING_RECALL_STRATEGY, SignalType.AMBIGUOUS_INSTRUCTION,
        SignalType.MISSING_UNIT, SignalType.UNCLEAR_BRANCHING,
        SignalType.AURAL_LENGTH_RISK, SignalType.VISUAL_FORMAT_DEPENDENCY,
        SignalType.GRID_FORMAT, SignalType.EMPHASIS_ARTIFACT,
        SignalType.FUNNEL_VIOLATION,
    ],
    "SCALE": [
        SignalType.VAGUE_QUANTIFIER_LABEL, SignalType.ASYMMETRIC_DISTRIBUTION,
        SignalType.MISSING_ENDPOINT, SignalType.NON_SEQUENTIAL_ORDER,
        SignalType.PRIMACY_RISK, SignalType.MISSING_MIDPOINT,
        SignalType.MISSING_DK_OPTION, SignalType.OVERLAPPING_OPTIONS,
        SignalType.SUBSET_CONTAINMENT, SignalType.COVERAGE_GAP,
        SignalType.MIXED_SCALE_TYPES, SignalType.UNDOCUMENTED_REVERSE,
    ],
    "INSTRUMENT": [
        SignalType.ALL_POSITIVE_POLARITY, SignalType.HIGH_POSITIVE_POLARITY,
        SignalType.BLOCK_TRANSITION_CONTAMINATION,
        SignalType.SEMANTIC_CLUSTERING, SignalType.ESCALATING_SEQUENCE,
        SignalType.HIGH_ITEM_COUNT, SignalType.ELEVATED_ITEM_COUNT,
        SignalType.HIGH_COMPLETION_TIME, SignalType.ELEVATED_COMPLETION_TIME,
        SignalType.DENSITY_INCREASE,
    ],
    "META": [
        SignalType.HIGH_RULE_COOCCURRENCE, SignalType.SYSTEMIC_RULE_PATTERN,
        SignalType.COMPOSITE_SCORE,
    ],
}


def get_category(signal_type: SignalType) -> str:
    """Return the category name for a given SignalType."""
    for category, types in SIGNAL_CATEGORIES.items():
        if signal_type in types:
            return category
    return "UNKNOWN"


# ----------------------------------------------------------------------
# SIGNAL DATACLASS
# ----------------------------------------------------------------------

@dataclass
class Signal:
    """
    A single typed detection signal from a principle rule.

    Attributes:
        type (SignalType):      What kind of signal this is.
        description (str):      Human-readable description of what was found.
        terms (list):           Specific terms or phrases that triggered this.
                                Empty list if not term-based.
        confidence (float):     How certain the detector is. 0.0-1.0.
                                Separate from severity — confidence is about
                                detection certainty, severity is about impact.
        metadata (dict):        Optional additional data (word counts, etc.)
    """
    type: SignalType
    description: str
    terms: list = field(default_factory=list)
    confidence: float = 0.80
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, "
                f"got {self.confidence}"
            )

    def to_dict(self) -> dict:
        return {
            "type": self.type.value,
            "category": get_category(self.type),
            "description": self.description,
            "terms": self.terms,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }

    def __repr__(self):
        return (
            f"Signal(type={self.type.value}, "
            f"confidence={self.confidence}, "
            f"terms={self.terms})"
        )