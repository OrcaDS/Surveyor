"""
app/reporting/report_builder.py

Generates human-readable and machine-readable reports from SurveyDiagnostic.

RESPONSIBILITIES:
    1. Build a plain text audit report for researchers
    2. Build a machine-readable JSON report for APIs
    3. Save reports to data/outputs/

REPORT STRUCTURE (plain text):
    Header     — Verdict and score upfront
    Section 1  — Instrument Overview
    Section 2  — Validity Score Breakdown (P025)
    Section 3  — Instrument-Level Findings
    Section 4  — High Priority Items
    Section 5  — Full Item Diagnostics
    Section 6  — Recommendations

USAGE:
    from app.reporting.report_builder import ReportBuilder

    builder = ReportBuilder(diagnostic)
    builder.save_text_report("data/outputs/report.txt")
    builder.save_json_report("data/outputs/report.json")
"""

import json
import os
from datetime import datetime
from app.diagnostics.diagnostic_aggregator import SurveyDiagnostic


class ReportBuilder:
    """
    Builds audit reports from a SurveyDiagnostic object.
    """

    PRINCIPLE_LABELS = {
        "P001": "CASM Response Process Failure",
        "P002": "Double-Barreled Question",
        "P003": "Undefined/Ambiguous Terms",
        "P004": "Recall Period Calibration",
        "P005": "Social Desirability Bias Risk",
        "P006": "Acquiescence Bias Risk",
        "P007": "Satisficing Risk",
        "P008": "Scale Anchor Calibration",
        "P009": "Response Option Order Effects",
        "P010": "Context/Carry-Over Effects",
        "P011": "Middle Category and DK Option",
        "P012": "Exhaustive/Mutually Exclusive Options",
        "P013": "Scale Direction Consistency",
        "P014": "Open vs. Closed Question Trade-offs",
        "P015": "Negative/Double-Negative Wording",
        "P016": "Leading and Loaded Wording Risk",
        "P017": "Recall-Enabling Strategies",
        "P018": "Construct Validity",
        "P019": "Response Task Specification",
        "P020": "Survey Length and Response Fatigue",
        "P021": "Aural vs. Visual Mode Differences",
        "P022": "Visual Layout Effects",
        "P023": "Behavior Coding Signal",
        "P024": "Funnel Principle",
        "P025": "Composite Validity Score",
    }

    # Classification labels and descriptions
    CLASSIFICATION_DESCRIPTIONS = {
        "INVALID": (
            "The instrument has significant methodological problems that "
            "are likely to produce unreliable or invalid data. "
            "Major revision is required before deployment."
        ),
        "NEEDS REVISION": (
            "The instrument has moderate methodological problems that "
            "may affect data quality. Revision of flagged items and "
            "instrument-level issues is recommended before deployment."
        ),
        "VALID": (
            "The instrument has few detected methodological problems. "
            "Minor revisions may still be warranted. Cognitive interviewing "
            "is recommended before full deployment."
        ),
    }

    def __init__(self, diagnostic: SurveyDiagnostic):
        self.diagnostic = diagnostic
        self.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._p025_finding = self._extract_p025()

    def _extract_p025(self):
        """Extract P025 finding from instrument violations if present."""
        for finding in self.diagnostic.instrument.instrument_findings:
            if finding.principle == "P025":
                return finding
        return None

    def _get_classification(self) -> tuple:
        """Return (score, classification) from P025 or fallback."""
        if self._p025_finding:
            score = self._p025_finding.severity
            # Re-derive classification from score
            if score >= 0.70:
                classification = "INVALID"
            elif score >= 0.40:
                classification = "NEEDS REVISION"
            else:
                classification = "VALID"
            return score, classification
        return None, "UNKNOWN"

    # ------------------------------------------------------------------
    # PUBLIC METHODS
    # ------------------------------------------------------------------

    def build_text_report(self) -> str:
        sections = [
            self._header(),
            self._section_1_overview(),
            self._section_2_validity_score(),
            self._section_3_instrument_findings(),
            self._section_4_high_priority_items(),
            self._section_5_full_item_diagnostics(),
            self._section_6_recommendations(),
            self._footer(),
        ]
        return "\n\n".join(sections)

    def build_json_report(self) -> dict:
        score, classification = self._get_classification()
        return {
            "generated_at": self.generated_at,
            "validity_score": score,
            "classification": classification,
            "survey_metadata": self.diagnostic.survey_metadata,
            "instrument_summary": self.diagnostic.instrument.to_dict(),
            "high_priority_items": [
                d.to_dict() for d in self.diagnostic.high_priority_items
            ],
            "all_items": [
                d.to_dict() for d in self.diagnostic.items
            ]
        }

    def save_text_report(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        report = self.build_text_report()
        with open(path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Text report saved: {path}")

    def save_json_report(self, path: str) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        report = self.build_json_report()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"JSON report saved: {path}")

    # ------------------------------------------------------------------
    # PRIVATE SECTION BUILDERS
    # ------------------------------------------------------------------

    def _header(self) -> str:
        inst = self.diagnostic.instrument
        score, classification = self._get_classification()

        score_display = f"{score:.3f}" if score is not None else "N/A"
        score_bar = self._score_bar(score) if score is not None else ""

        return (
            f"{'='*70}\n"
            f"  SURVEYOR AI — SURVEY VALIDITY AUDIT REPORT\n"
            f"{'='*70}\n"
            f"  Generated      : {self.generated_at}\n"
            f"  Items evaluated: {inst.total_items}\n"
            f"  Rules applied  : {len(inst.rule_summary)}\n"
            f"\n"
            f"  ┌─────────────────────────────────────────────────┐\n"
            f"  │  VALIDITY SCORE  : {score_display:<10}                  │\n"
            f"  │  CLASSIFICATION  : {classification:<28}  │\n"
            f"  │  RISK LEVEL      : {inst.instrument_validity_risk:<28}  │\n"
            f"  │  {score_bar:<47}  │\n"
            f"  └─────────────────────────────────────────────────┘\n"
            f"\n"
            f"  DISCLAIMER: This report is a theory-inspired heuristic\n"
            f"  diagnostic. Findings indicate RISK, not confirmed bias.\n"
            f"  All outputs should be reviewed by a qualified expert.\n"
            f"{'='*70}"
        )

    def _score_bar(self, score: float) -> str:
        """Visual score bar. Higher score = more problems."""
        filled = int(score * 20)
        empty = 20 - filled
        return f"Risk: [{'█' * filled}{'░' * empty}] {score:.0%}"

    def _section_1_overview(self) -> str:
        inst = self.diagnostic.instrument
        meta = self.diagnostic.survey_metadata
        scale = meta.get("scale", {})
        scale_desc = (
            f"{scale.get('points', '?')}-point scale "
            f"({' / '.join(scale.get('labels', {}).values())})"
            if scale else "Not detected"
        )

        violation_pct = (
            inst.items_with_violations / inst.total_items * 100
            if inst.total_items > 0 else 0
        )

        lines = [
            "SECTION 1 — INSTRUMENT OVERVIEW",
            "-" * 40,
            f"Total items          : {inst.total_items}",
            f"Scale                : {scale_desc}",
            f"Avg word count/item  : {meta.get('avg_word_count', 'N/A')}",
            f"Question items       : {meta.get('question_count', 0)}",
            f"Statement items      : {meta.get('statement_count', 0)}",
            "",
            f"Items with violations: {inst.items_with_violations} "
            f"({violation_pct:.1f}%)",
            f"Clean items          : {inst.clean_items}",
            f"Total item violations: {inst.total_item_violations}",
            f"Instrument findings  : {inst.instrument_finding_count}",
            "",
            f"Priority breakdown:",
            f"  HIGH   : {inst.high_priority_count} items",
            f"  MEDIUM : {inst.medium_priority_count} items",
            f"  LOW    : {inst.low_priority_count} items",
            f"  CLEAN  : {inst.clean_items} items",
            "",
            "Rule violation counts:",
        ]

        for rule_id, count in sorted(inst.rule_summary.items()):
            if rule_id in ("P023", "P025"):
                continue  # these are meta-rules, shown separately
            label = self.PRINCIPLE_LABELS.get(rule_id, rule_id)
            bar = "█" * min(count, 30)
            lines.append(f"  {rule_id} ({label}): {count} {bar}")

        return "\n".join(lines)

    def _section_2_validity_score(self) -> str:
        score, classification = self._get_classification()
        description = self.CLASSIFICATION_DESCRIPTIONS.get(
            classification, ""
        )

        lines = [
            "SECTION 2 — VALIDITY SCORE BREAKDOWN (P025)",
            "-" * 40,
        ]

        if not self._p025_finding:
            lines.append("P025 composite score not available.")
            return "\n".join(lines)

        lines += [
            f"Composite Validity Score : {score:.3f} / 1.000",
            f"Classification           : {classification}",
            f"",
            f"Interpretation:",
            f"  {description}",
            f"",
            f"Score components (higher = more problems detected):",
            f"  Component 1 (40% weight) — High-severity item ratio",
            f"    Items with any violation above severity 0.50.",
            f"    Ensures minor flags don't inflate the score.",
            f"",
            f"  Component 2 (35% weight) — Mean composite severity",
            f"    Average severity across all items (clean items = 0.0).",
            f"    Reflects overall burden of problems per item.",
            f"",
            f"  Component 3 (25% weight) — Instrument finding severity",
            f"    Weighted mean of instrument-level finding severities.",
            f"    Weighted by finding count — more findings compound.",
            f"",
            f"Classification thresholds:",
            f"  VALID          : score < 0.40",
            f"  NEEDS REVISION : 0.40 <= score < 0.70",
            f"  INVALID        : score >= 0.70",
            f"",
            f"IMPORTANT: This score is a heuristic risk index, not a",
            f"validated psychometric measure. Severity weights are",
            f"principled but not empirically calibrated. Interpret",
            f"alongside the full diagnostic report.",
        ]

        return "\n".join(lines)

    def _section_3_instrument_findings(self) -> str:
        inst = self.diagnostic.instrument
        lines = [
            "SECTION 3 — INSTRUMENT-LEVEL FINDINGS",
            "-" * 40,
        ]

        # Exclude P025 — it has its own section
        findings = [
            f for f in inst.instrument_findings
            if f.principle != "P025"
        ]

        if not findings:
            lines.append("No instrument-level findings.")
            return "\n".join(lines)

        # Sort by severity descending
        findings = sorted(findings, key=lambda f: f.severity, reverse=True)

        for i, finding in enumerate(findings, 1):
            label = self.PRINCIPLE_LABELS.get(
                finding.principle, finding.principle
            )
            affected_desc = (
                f"All {len(finding.affected_items)} items"
                if len(finding.affected_items) > 10
                else str(finding.affected_items)
            )
            lines += [
                f"Finding {i}: {finding.principle} — {label}",
                f"  Severity : {finding.severity}",
                f"  Affected : {affected_desc}",
                f"  Evidence : {finding.evidence[:200]}"
                f"{'...' if len(finding.evidence) > 200 else ''}",
                "",
            ]

        return "\n".join(lines)

    def _section_4_high_priority_items(self) -> str:
        lines = [
            "SECTION 4 — HIGH PRIORITY ITEMS (require immediate attention)",
            "-" * 40,
            "NOTE: Findings indicate RISK signals, not confirmed bias.",
            "      Verify all flagged items through expert review.",
            "",
        ]

        if not self.diagnostic.high_priority_items:
            lines.append("No high priority items detected.")
            return "\n".join(lines)

        for d in self.diagnostic.high_priority_items:
            lines += [
                f"Item {d.item_id:>2} | composite={d.composite_severity:.2f} "
                f"| max={d.max_severity:.2f} "
                f"| rules fired: {', '.join(d.rules_fired)}",
                f"  Text: {d.text[:90]}"
                f"{'...' if len(d.text) > 90 else ''}",
            ]
            for v in d.violations:
                label = self.PRINCIPLE_LABELS.get(v.principle, v.principle)
                lines.append(
                    f"  [{v.principle}] sev={v.severity:.2f} "
                    f"{label}: {v.evidence[:80]}..."
                )
            lines.append("")

        return "\n".join(lines)

    def _section_5_full_item_diagnostics(self) -> str:
        lines = [
            "SECTION 5 — FULL ITEM DIAGNOSTICS",
            "-" * 40,
        ]

        for d in self.diagnostic.items:
            if d.violation_count == 0:
                lines.append(
                    f"Item {d.item_id:>2} | CLEAN | "
                    f"{d.text[:60]}{'...' if len(d.text) > 60 else ''}"
                )
            else:
                lines += [
                    f"Item {d.item_id:>2} | {d.priority:<6} | "
                    f"composite={d.composite_severity:.2f} | "
                    f"violations={d.violation_count}",
                    f"  Text: {d.text[:80]}"
                    f"{'...' if len(d.text) > 80 else ''}",
                ]
                for v in d.violations:
                    label = self.PRINCIPLE_LABELS.get(
                        v.principle, v.principle
                    )
                    lines.append(
                        f"  [{v.principle}] {label} "
                        f"(sev={v.severity:.2f})"
                    )
                lines.append("")

        return "\n".join(lines)

    def _section_6_recommendations(self) -> str:
        inst = self.diagnostic.instrument
        _, classification = self._get_classification()

        lines = [
            "SECTION 6 — RECOMMENDATIONS",
            "-" * 40,
        ]

        inst_rec = []
        rec_num = 1

        if any(f.principle == "P006" for f in inst.instrument_findings):
            inst_rec.append(
                f"{rec_num}. ADD REVERSE-SCORED ITEMS: All items are "
                f"positively worded. Add 15-20 reverse-scored items "
                f"(20-25% of instrument) to detect and correct "
                f"acquiescence bias risk."
            )
            rec_num += 1

        if any(f.principle == "P020" for f in inst.instrument_findings):
            inst_rec.append(
                f"{rec_num}. REDUCE INSTRUMENT LENGTH: At {inst.total_items} "
                f"items the instrument exceeds recommended length. "
                f"Consider reducing to 50-60 items after pilot testing."
            )
            rec_num += 1

        if any(f.principle == "P008" for f in inst.instrument_findings):
            inst_rec.append(
                f"{rec_num}. IMPROVE SCALE ANCHORS: Replace vague frequency "
                f"labels (Often, Sometimes, Rarely) with numerically "
                f"anchored alternatives or switch to an agreement scale "
                f"(Strongly Agree to Strongly Disagree) which better "
                f"matches self-report attitude items."
            )
            rec_num += 1

        if any(f.principle == "P024" for f in inst.instrument_findings):
            inst_rec.append(
                f"{rec_num}. REORDER ITEMS: Funnel principle violations "
                f"detected. Within each construct block, place general "
                f"construct items before specific behavioral items."
            )
            rec_num += 1

        if inst_rec:
            lines.append("INSTRUMENT-LEVEL:")
            lines += inst_rec
            lines.append("")

        lines.append("ITEM-LEVEL (top 5 priority rewrites):")

        top_items = sorted(
            self.diagnostic.high_priority_items,
            key=lambda d: d.composite_severity,
            reverse=True
        )[:5]

        for d in top_items:
            primary_rule = d.rules_fired[0] if d.rules_fired else "N/A"
            lines += [
                f"Item {d.item_id} (composite risk: {d.composite_severity:.2f}):",
                f"  Current : {d.text[:90]}",
                f"  Risk signals : {', '.join(d.rules_fired)}",
                f"  Primary action: Address "
                f"{self.PRINCIPLE_LABELS.get(primary_rule, primary_rule)}",
                "",
            ]

        lines += [
            "PROCESS RECOMMENDATIONS:",
            "- Conduct cognitive interviews with 5-10 representative",
            "  respondents before full deployment",
            "- Pilot test with a small sample to assess item",
            "  discrimination and scale reliability (Cronbach alpha)",
            "- Consider splitting into subscales administered separately",
            "  to reduce fatigue risk",
            "- Review all HIGH priority items with a survey methodology",
            "  expert before finalizing",
            "- Treat all findings as risk signals requiring expert",
            "  verification — not confirmed validity failures",
        ]

        return "\n".join(lines)

    def _footer(self) -> str:
        score, classification = self._get_classification()
        score_display = f"{score:.3f}" if score is not None else "N/A"

        return (
            f"{'='*70}\n"
            f"  END OF REPORT — Surveyor AI\n"
            f"  Final verdict: {classification} (score: {score_display})\n"
            f"\n"
            f"  LIMITATIONS:\n"
            f"  - Findings are heuristic risk signals, not confirmed bias\n"
            f"  - Severity weights are principled but not empirically\n"
            f"    calibrated against human expert ratings\n"
            f"  - Construct-aware evaluation not yet implemented\n"
            f"  - Score is not comparable across different rule sets\n"
            f"  - Not a substitute for expert review or cognitive testing\n"
            f"{'='*70}"
        )