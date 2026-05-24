"""
app/principles/p025.py

PRINCIPLE: P025 — Cognitive Testing as Quality Gate (Composite Scorer)
SOURCE: Fowler — Survey Research Methods, Ch. 8
        Presser et al. — Methods for Testing and Evaluating Survey Questions
OPERATIONALIZABILITY: High (as composite)
CONFIDENCE: Medium

WHAT THIS RULE PRODUCES:
    A single instrument validity score between 0.0 and 1.0 and a
    classification: VALID, NEEDS REVISION, or INVALID.

    This is NOT a new detection rule. It is the scoring aggregator —
    it synthesizes all violations from P001-P024 into a final verdict.

    The score represents INVALIDITY RISK:
        0.0 = no detected problems (fully valid by engine standards)
        1.0 = maximum detected problems (high invalidity risk)

    Classification thresholds:
        score >= 0.70 -> INVALID
        score >= 0.40 -> NEEDS REVISION
        score <  0.40 -> VALID

FORMULA (three components):

    COMPONENT 1 — High-severity item ratio (40% weight):
        Items with at least one violation above severity 0.50,
        divided by total items.
        Only high-severity violations count here — minor flags
        (severity 0.20-0.35) do not push an instrument toward INVALID.
        This prevents low-severity rule co-occurrence from overstating
        invalidity.

    COMPONENT 2 — Mean composite severity (35% weight):
        Mean composite severity across ALL items (including clean ones
        which contribute 0.0). This reflects the average burden of
        problems across the instrument.

    COMPONENT 3 — Instrument finding severity (25% weight):
        Weighted mean severity of instrument-level findings.
        Weighted by finding count to reflect that multiple instrument-
        level problems compound each other.

    COMBINED:
        raw_score = (
            0.40 * component_1 +
            0.35 * component_2 +
            0.25 * component_3
        )
        validity_score = min(raw_score, 1.0)

DESIGN DECISIONS:
    - Severity threshold of 0.50 for Component 1 is deliberate.
      Minor violations (P003 at 0.30, P015 at 0.20) are real findings
      but should not classify an instrument as INVALID.
    - Component weights (40/35/25) reflect that item-level problems
      are more actionable than instrument-level ones for rewriting,
      but instrument-level problems (acquiescence bias, fatigue) are
      more fundamental to validity.
    - Clean items (zero violations) contribute 0.0 to Component 2,
      which rewards instruments with clean items even when overall
      violation count is high.

LIMITATIONS:
    - Severity weights are heuristic, not empirically calibrated.
    - The score is not comparable across different rule sets —
      adding new rules will shift scores.
    - This score should be interpreted alongside the full diagnostic
      report, not in isolation.
    - Not a substitute for expert review or cognitive interviewing.
"""

from app.principles.base_rule import BaseRule, InstrumentViolation


class P025(BaseRule):

    id = "P025"
    description = (
        "Composite scorer: synthesizes all P001-P024 violations into "
        "a single validity score and VALID/NEEDS REVISION/INVALID verdict."
    )

    # Component weights — must sum to 1.0
    WEIGHT_ITEM_RATIO = 0.40
    WEIGHT_MEAN_SEVERITY = 0.35
    WEIGHT_INSTRUMENT = 0.25

    # Severity threshold for Component 1
    HIGH_SEVERITY_THRESHOLD = 0.50

    # Classification thresholds
    INVALID_THRESHOLD = 0.70
    NEEDS_REVISION_THRESHOLD = 0.40

    def is_instrument_level(self) -> bool:
        return True

    def evaluate_instrument(self, items: list) -> list | None:
        """
        Compute composite validity score from pre-injected violation data.

        Requires items to be enriched with:
            '_composite_severity' (float): per-item composite severity
            '_max_severity' (float):       per-item max violation severity
            '_instrument_findings' (list): instrument-level violations

        The registry injects this data before calling P025.

        Args:
            items (list): Enriched item dicts from registry.

        Returns:
            list[InstrumentViolation]: Single scoring finding.
        """
        if not items:
            return None

        total = len(items)

        # --- Component 1: High-severity item ratio ---
        high_severity_items = sum(
            1 for item in items
            if item.get("_max_severity", 0.0) >= self.HIGH_SEVERITY_THRESHOLD
        )
        component_1 = high_severity_items / total

        # --- Component 2: Mean composite severity ---
        composite_severities = [
            item.get("_composite_severity", 0.0)
            for item in items
        ]
        component_2 = (
            sum(composite_severities) / len(composite_severities)
            if composite_severities else 0.0
        )

        # --- Component 3: Instrument finding severity ---
        instrument_findings = items[0].get("_instrument_findings", [])
        if instrument_findings:
            finding_severities = [f.severity for f in instrument_findings]
            # Weight by count: more findings = compounding effect
            finding_count_weight = min(len(finding_severities) / 5.0, 1.0)
            component_3 = (
                sum(finding_severities) / len(finding_severities)
            ) * (0.7 + 0.3 * finding_count_weight)
        else:
            component_3 = 0.0

        # --- Combined score ---
        raw_score = (
            self.WEIGHT_ITEM_RATIO * component_1 +
            self.WEIGHT_MEAN_SEVERITY * component_2 +
            self.WEIGHT_INSTRUMENT * component_3
        )
        validity_score = min(round(raw_score, 3), 1.0)

        # --- Classification ---
        if validity_score >= self.INVALID_THRESHOLD:
            classification = "INVALID"
        elif validity_score >= self.NEEDS_REVISION_THRESHOLD:
            classification = "NEEDS REVISION"
        else:
            classification = "VALID"

        # --- Evidence ---
        evidence = (
            f"Composite validity score: {validity_score:.3f} — "
            f"Classification: {classification}. "
            f"Components: "
            f"high-severity item ratio={component_1:.2f} "
            f"(items with severity>={self.HIGH_SEVERITY_THRESHOLD}: "
            f"{high_severity_items}/{total}) | "
            f"mean composite severity={component_2:.3f} | "
            f"instrument finding severity={component_3:.3f} "
            f"({len(instrument_findings)} finding(s)). "
            f"Note: score represents invalidity risk (higher = more problems). "
            f"Weights: item ratio={self.WEIGHT_ITEM_RATIO}, "
            f"mean severity={self.WEIGHT_MEAN_SEVERITY}, "
            f"instrument={self.WEIGHT_INSTRUMENT}."
        )

        return [
            InstrumentViolation(
                principle=self.id,
                severity=round(validity_score, 2),
                evidence=evidence,
                affected_items=list(range(1, total + 1))
            )
        ]

    def evaluate(self, item: dict):
        raise NotImplementedError(
            "P025 is an instrument-level scoring rule. "
            "Call evaluate_instrument(items) with enriched item dicts."
        )