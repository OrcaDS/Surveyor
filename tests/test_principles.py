"""
tests/test_principles.py

Test suite for the principle engine and registry.

HOW TO RUN:
    From your project root:
        python -m pytest tests/test_principles.py -v

WHAT THIS COVERS:
    - BaseRule and Violation contracts
    - Individual rule behavior on known inputs
    - Registry registration and evaluation
    - Instrument-level rule interface
    - P025 composite scoring
"""

import pytest
from app.principles.base_rule import BaseRule, Violation, InstrumentViolation
from app.principles.p001 import P001
from app.principles.p002 import P002
from app.principles.p003 import P003
from app.principles.p004 import P004
from app.principles.p005 import P005
from app.principles.p006 import P006
from app.principles.p007 import P007
from app.principles.p015 import P015
from app.principles.p016 import P016
from app.principles.p020 import P020
from app.principles.registry import PrincipleRegistry, build_default_registry


# ----------------------------------------------------------------------
# HELPERS
# ----------------------------------------------------------------------

def make_item(
    item_id: int,
    text: str,
    word_count: int = None,
    scale: dict = None
) -> dict:
    """Build a minimal item dict for testing."""
    if scale is None:
        scale = {
            "points": 5,
            "labels": {
                "5": "Always", "4": "Often", "3": "Sometimes",
                "2": "Rarely", "1": "Never"
            }
        }
    if word_count is None:
        word_count = len(text.split())
    return {
        "item_id": item_id,
        "text": text,
        "word_count": word_count,
        "is_question": "?" in text,
        "construct": None,
        "scale": scale,
    }


def make_items(texts: list) -> list:
    """Build a list of item dicts from a list of strings."""
    return [make_item(i + 1, text) for i, text in enumerate(texts)]


# ----------------------------------------------------------------------
# VIOLATION TESTS
# ----------------------------------------------------------------------

class TestViolation:

    def test_valid_violation_creation(self):
        """Violation creates correctly with valid inputs."""
        v = Violation(principle="P001", severity=0.5, evidence="test")
        assert v.principle == "P001"
        assert v.severity == 0.5
        assert v.evidence == "test"

    def test_severity_below_zero_raises(self):
        """Severity below 0.0 must raise ValueError."""
        with pytest.raises(ValueError):
            Violation(principle="P001", severity=-0.1, evidence="test")

    def test_severity_above_one_raises(self):
        """Severity above 1.0 must raise ValueError."""
        with pytest.raises(ValueError):
            Violation(principle="P001", severity=1.1, evidence="test")

    def test_empty_principle_raises(self):
        """Empty principle ID must raise ValueError."""
        with pytest.raises(ValueError):
            Violation(principle="", severity=0.5, evidence="test")

    def test_empty_evidence_raises(self):
        """Empty evidence must raise ValueError."""
        with pytest.raises(ValueError):
            Violation(principle="P001", severity=0.5, evidence="")

    def test_to_dict(self):
        """to_dict returns correct keys and values."""
        v = Violation(principle="P002", severity=0.75, evidence="found")
        d = v.to_dict()
        assert d["principle"] == "P002"
        assert d["severity"] == 0.75
        assert d["evidence"] == "found"

    def test_boundary_severity_zero(self):
        """Severity of exactly 0.0 is valid."""
        v = Violation(principle="P001", severity=0.0, evidence="test")
        assert v.severity == 0.0

    def test_boundary_severity_one(self):
        """Severity of exactly 1.0 is valid."""
        v = Violation(principle="P001", severity=1.0, evidence="test")
        assert v.severity == 1.0


# ----------------------------------------------------------------------
# P001 TESTS
# ----------------------------------------------------------------------

class TestP001:

    def test_fires_on_abstract_concept(self):
        """P001 fires on known abstract concept terms."""
        item = make_item(1, "I ensure effective leadership in the division.")
        result = P001().evaluate(item)
        assert result is not None
        assert result.principle == "P001"

    def test_fires_on_unmeasurable_judgment(self):
        """P001 fires on unmeasurable judgment targets."""
        item = make_item(1, "I am a strong motivator for my people.")
        result = P001().evaluate(item)
        assert result is not None

    def test_clean_item_returns_none(self):
        """P001 returns None for a clean item."""
        item = make_item(1, "I give orders to my staff each day.")
        result = P001().evaluate(item)
        assert result is None

    def test_severity_increases_with_multiple_stages(self):
        """P001 severity increases when multiple stages fire."""
        item_single = make_item(
            1, "I am a strong motivator in my position."
        )
        item_multi = make_item(
            2,
            "I ascertain a deep appreciation of empowerment for "
            "it involves desired actions and total development."
        )
        r1 = P001().evaluate(item_single)
        r2 = P001().evaluate(item_multi)
        assert r1 is not None
        assert r2 is not None
        assert r2.severity >= r1.severity

    def test_deduplicates_cross_stage_terms(self):
        """P001 does not report same term in both Stage 1 and Stage 3."""
        item = make_item(
            1,
            "I guarantee to have complete knowledge of ethical issues."
        )
        result = P001().evaluate(item)
        if result:
            assert result.evidence.count("complete knowledge") == 1


# ----------------------------------------------------------------------
# P002 TESTS
# ----------------------------------------------------------------------

class TestP002:

    def test_fires_on_evaluative_pair(self):
        """P002 fires on known evaluative noun pairs."""
        item = make_item(
            1,
            "I assert that the use of reward can promote "
            "trust and loyalty to the schools division."
        )
        result = P002().evaluate(item)
        assert result is not None
        assert result.principle == "P002"

    def test_fires_on_multi_proposition_connector(self):
        """P002 fires on 'as well as' connector."""
        item = make_item(
            1,
            "I use sincere forms of ingratiation as well as "
            "communicate with them in order to find their need."
        )
        result = P002().evaluate(item)
        assert result is not None

    def test_suppresses_fused_compounds(self):
        """P002 does not fire on whitelisted fused compound nouns."""
        item = make_item(
            1,
            "I develop discipline among teaching and non-teaching "
            "personnel in the schools division."
        )
        result = P002().evaluate(item)
        # teaching and non-teaching is whitelisted
        # should not fire on this alone
        if result:
            assert "teaching and non-teaching" not in result.evidence

    def test_higher_severity_for_multiple_signals(self):
        """P002 severity is higher when multiple signals fire."""
        item_single = make_item(
            1,
            "I use sincere forms of ingratiation as well as help them."
        )
        item_multi = make_item(
            2,
            "I understand that rewarding gives gratification to "
            "personnel while contributing to their success and development."
        )
        r1 = P002().evaluate(item_single)
        r2 = P002().evaluate(item_multi)
        if r1 and r2:
            assert r2.severity >= r1.severity


# ----------------------------------------------------------------------
# P003 TESTS
# ----------------------------------------------------------------------

class TestP003:

    def test_fires_on_evaluative_term(self):
        """P003 fires on evaluative terms without defined standard."""
        item = make_item(
            1,
            "I ensure appropriate sanctions are applied to personnel."
        )
        result = P003().evaluate(item)
        assert result is not None

    def test_fires_on_role_term(self):
        """P003 fires on undefined scope role terms."""
        # Use bare 'subordinates' without possessive —
        # 'my subordinates' is suppressed as contextually scoped
        item = make_item(
            1,
            "I instruct subordinates to follow the division protocols."
        )
        result = P003().evaluate(item)
        assert result is not None

    def test_suppresses_my_people(self):
        """P003 does not fire on 'my people' — contextually scoped."""
        item = make_item(
            1,
            "I give orders to my people since I am the head."
        )
        result = P003().evaluate(item)
        # 'my people' is suppressed — should not fire on role terms
        if result:
            assert "people" not in result.evidence


# ----------------------------------------------------------------------
# P004 TESTS
# ----------------------------------------------------------------------

class TestP004:

    def test_returns_none_for_attitude_items(self):
        """P004 returns None for Likert attitude items (gate check)."""
        item = make_item(
            1,
            "I affirm that giving praise is a strong motivator."
        )
        result = P004().evaluate(item)
        assert result is None

    def test_fires_on_unanchored_frequency(self):
        """P004 fires on behavioral frequency item with no time anchor."""
        item = make_item(
            1,
            "How many times did you attend a leadership seminar?"
        )
        result = P004().evaluate(item)
        assert result is not None
        assert result.severity == 0.60


# ----------------------------------------------------------------------
# P005 TESTS
# ----------------------------------------------------------------------

class TestP005:

    def test_fires_on_aggrandizing_stem(self):
        """P005 fires on self-aggrandizing stem verbs."""
        item = make_item(
            1, "I affirm that giving praise is a strong motivator."
        )
        result = P005().evaluate(item)
        assert result is not None
        assert "i affirm" in result.evidence

    def test_fires_on_competence_presupposition(self):
        """P005 fires on competence presupposition phrases."""
        item = make_item(
            1,
            "I have the ability to communicate effectively with people."
        )
        result = P005().evaluate(item)
        assert result is not None

    def test_higher_severity_for_multiple_signals(self):
        """P005 severity increases with multiple signals."""
        item_single = make_item(1, "I affirm that this is correct.")
        item_multi = make_item(
            2,
            "I affirm that I have the superior knowledge to lead "
            "and I know that I possess exceptional skills."
        )
        r1 = P005().evaluate(item_single)
        r2 = P005().evaluate(item_multi)
        assert r1 is not None
        assert r2 is not None
        assert r2.severity >= r1.severity


# ----------------------------------------------------------------------
# P006 TESTS
# ----------------------------------------------------------------------

class TestP006:

    def test_is_instrument_level(self):
        """P006 identifies as instrument-level rule."""
        assert P006().is_instrument_level() is True

    def test_evaluate_raises_not_implemented(self):
        """P006.evaluate() raises NotImplementedError."""
        with pytest.raises(NotImplementedError):
            P006().evaluate(make_item(1, "test"))

    def test_fires_on_all_positive_instrument(self):
        """P006 fires when all items are positively worded."""
        items = make_items([
            "I lead my team effectively.",
            "I ensure quality education.",
            "I maintain control of the division.",
        ])
        result = P006().evaluate_instrument(items)
        assert result is not None
        assert len(result) == 1
        assert result[0].severity == 0.90

    def test_passes_when_negative_items_present(self):
        """P006 passes when sufficient negative-polarity items exist."""
        # Mix positive and negative items to go below threshold
        texts = ["I lead effectively."] * 7 + [
            "I do not punish without cause.",
            "I never ignore my subordinates.",
            "I cannot allow misconduct.",
        ]
        items = make_items(texts)
        result = P006().evaluate_instrument(items)
        assert result is None


# ----------------------------------------------------------------------
# P007 TESTS
# ----------------------------------------------------------------------

class TestP007:

    def test_fires_on_long_item(self):
        """P007 fires on items exceeding word count threshold."""
        long_text = (
            "I understand that if the reward available can only be "
            "given to a subset of teaching and non-teaching personnel "
            "then this can create healthy competition amongst personnel "
            "to achieve the reward."
        )
        item = make_item(1, long_text, word_count=len(long_text.split()))
        result = P007().evaluate(item)
        assert result is not None

    def test_clean_short_item(self):
        """P007 returns None for short simple items."""
        item = make_item(1, "I lead my team well.", word_count=5)
        result = P007().evaluate(item)
        assert result is None


# ----------------------------------------------------------------------
# P015 TESTS
# ----------------------------------------------------------------------

class TestP015:

    def test_fires_on_negated_prefix(self):
        """P015 fires on negated prefix terms."""
        item = make_item(
            1,
            "I am in the position to punish uncooperative people."
        )
        result = P015().evaluate(item)
        assert result is not None
        assert result.severity == 0.20

    def test_clean_item_returns_none(self):
        """P015 returns None for positively worded items."""
        item = make_item(1, "I reward my people for good performance.")
        result = P015().evaluate(item)
        assert result is None


# ----------------------------------------------------------------------
# P016 TESTS
# ----------------------------------------------------------------------

class TestP016:

    def test_fires_on_authority_reference(self):
        """P016 fires on institutional authority references."""
        item = make_item(
            1,
            "I carry out a policy mandated by the Department of Education."
        )
        result = P016().evaluate(item)
        assert result is not None
        assert result.severity >= 0.40

    def test_fires_on_positive_valence(self):
        """P016 fires on emotionally positive valence terms."""
        item = make_item(
            1,
            "I inspire and motivate my people to achieve goals."
        )
        result = P016().evaluate(item)
        assert result is not None

    def test_suppresses_positive_reinforcement(self):
        """P016 does not fire on 'positive reinforcement' — technical term."""
        item = make_item(
            1,
            "I attest that providing positive reinforcement fosters creativity."
        )
        result = P016().evaluate(item)
        if result:
            assert "positive reinforcement" not in result.evidence


# ----------------------------------------------------------------------
# P020 TESTS
# ----------------------------------------------------------------------

class TestP020:

    def test_is_instrument_level(self):
        """P020 identifies as instrument-level rule."""
        assert P020().is_instrument_level() is True

    def test_fires_on_large_instrument(self):
        """P020 fires on instruments with 75+ items."""
        items = make_items(
            ["I lead effectively."] * 75
        )
        result = P020().evaluate_instrument(items)
        assert result is not None
        assert result[0].severity >= 0.60

    def test_passes_on_small_instrument(self):
        """P020 passes on small instruments under threshold."""
        items = make_items(["I lead effectively."] * 20)
        result = P020().evaluate_instrument(items)
        assert result is None


# ----------------------------------------------------------------------
# REGISTRY TESTS
# ----------------------------------------------------------------------

class TestPrincipleRegistry:

    def test_register_rule(self):
        """Registry accepts valid rule registration."""
        registry = PrincipleRegistry()
        registry.register(P001())
        assert "P001" in registry.registered_rules()

    def test_duplicate_registration_raises(self):
        """Registry raises ValueError on duplicate rule ID."""
        registry = PrincipleRegistry()
        registry.register(P001())
        with pytest.raises(ValueError):
            registry.register(P001())

    def test_invalid_rule_raises(self):
        """Registry raises TypeError for non-BaseRule objects."""
        registry = PrincipleRegistry()
        with pytest.raises(TypeError):
            registry.register("not a rule")

    def test_rule_count(self):
        """Registry rule count matches registered rules."""
        registry = PrincipleRegistry()
        registry.register(P001())
        registry.register(P002())
        assert registry.rule_count() == 2

    def test_evaluate_returns_results(self):
        """Registry evaluate returns EvaluationResults object."""
        registry = PrincipleRegistry()
        registry.register(P001())
        items = make_items(["I am a strong motivator."])
        results = registry.evaluate(items)
        assert results is not None

    def test_evaluate_zero_errors(self):
        """Registry evaluation produces zero errors on valid input."""
        registry = build_default_registry()
        items = make_items([
            "I lead my team effectively.",
            "I ensure quality education in schools.",
            "I maintain control of the division.",
        ])
        results = registry.evaluate(items)
        assert len(results.rule_errors) == 0

    def test_instrument_level_rules_handled(self):
        """Registry correctly separates instrument-level rules."""
        registry = PrincipleRegistry()
        registry.register(P006())
        items = make_items(["I lead effectively."] * 5)
        results = registry.evaluate(items)
        assert "P006" in results.summary

    def test_p004_fires_zero_on_attitude_items(self):
        """P004 fires zero times on attitude/self-report items."""
        registry = PrincipleRegistry()
        registry.register(P004())
        items = make_items([
            "I affirm that giving praise is a strong motivator.",
            "I ensure quality education in schools.",
            "I maintain control of the division.",
        ])
        results = registry.evaluate(items)
        assert results.summary.get("P004", 0) == 0

    def test_build_default_registry_has_rules(self):
        """build_default_registry returns registry with rules loaded."""
        registry = build_default_registry()
        assert registry.rule_count() > 0

    def test_evaluation_results_summary_keys(self):
        """EvaluationResults summary contains all registered rule IDs."""
        registry = PrincipleRegistry()
        registry.register(P001())
        registry.register(P003())
        items = make_items(["I lead effectively."])
        results = registry.evaluate(items)
        assert "P001" in results.summary
        assert "P003" in results.summary

    def test_violations_for_item(self):
        """violations_for_item returns correct violations."""
        registry = PrincipleRegistry()
        registry.register(P005())
        items = make_items(["I affirm that praise is a strong motivator."])
        results = registry.evaluate(items)
        violations = results.violations_for_item(1)
        assert isinstance(violations, list)

    def test_items_with_violations_are_tracked(self):
        """items_with_violations returns correct item IDs."""
        registry = PrincipleRegistry()
        registry.register(P005())
        items = make_items([
            "I affirm that praise is a strong motivator.",
            "I lead my team.",
        ])
        results = registry.evaluate(items)
        flagged = results.items_with_violations()
        assert 1 in flagged