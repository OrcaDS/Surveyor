"""
app/reporting/report_builder.py

Generates human-readable and machine-readable reports from SurveyDiagnostic.

RESPONSIBILITIES:
    1. Build a plain text audit report for researchers
    2. Build a machine-readable JSON report for APIs
    3. Save reports to data/outputs/

REPORT STRUCTURE (plain text):
    Section 1 — Instrument Overview
    Section 2 — Instrument-Level Findings
    Section 3 — High Priority Items
    Section 4 — Full Item Diagnostics
    Section 5 — Recommendations

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

    Usage:
        builder = ReportBuilder(diagnostic)
        builder.save_text_report("data/outputs/report.txt")
        builder.save_json_report("data/outputs/report.json")
    """

    # Principle descriptions for human-readable evidence headers
    PRINCIPLE_LABELS = {
        "P001": "CASM Response Process Failure",
        "P002": "Double-Barreled Question",
        "P003": "Undefined/Ambiguous Terms",
        "P004": "Recall Period Calibration",
        "P005": "Social Desirability Bias",
        "P006": "Acquiescence Bias",
        "P007": "Satisficing Risk",
        "P008": "Scale Anchor Calibration",
        "P009": "Response Option Order Effects",
        "P010": "Context/Carry-Over Effects",
        "P011": "Middle Category and DK Option",
        "P012": "Exhaustive/Mutually Exclusive Options",
        "P013": "Scale Direction Consistency",
        "P014": "Open vs. Closed Question Trade-offs",
        "P015": "Negative/Double-Negative Wording",
        "P016": "Leading and Loaded Wording",
        "P017": "Recall-Enabling Strategies",
        "P018": "Construct Validity",
        "P019": "Response Task Specification",
        "P020": "Survey Length and Response Fatigue",
        "P021": "Aural vs. Visual Mode Differences",
        "P022": "Visual Layout Effects",
        "P023": "Behavior Coding Signal",
        "P024": "Funnel Principle",
        "P025": "Composite Quality Score",
    }

    def __init__(self, diagnostic: SurveyDiagnostic):
        """
        Args:
            diagnostic (SurveyDiagnostic): Output from DiagnosticAggregator.
        """
        self.diagnostic = diagnostic
        self.generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ------------------------------------------------------------------
    # PUBLIC METHODS
    # ------------------------------------------------------------------

    def build_text_report(self) -> str:
        """
        Build the full plain text audit report as a string.

        Returns:
            str: Complete formatted report.
        """
        sections = [
            self._header(),
            self._section_1_overview(),
            self._section_2_instrument_findings(),
            self._section_3_high_priority_items(),
            self._section_4_full_item_diagnostics(),
            self._section_5_recommendations(),
            self._footer(),
        ]
        return "\n\n".join(sections)

    def build_json_report(self) -> dict:
        """
        Build the machine-readable JSON report as a dict.

        Returns:
            dict: Complete structured report.
        """
        return {
            "generated_at": self.generated_at,
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
        """
        Build and save the plain text report to disk.

        Args:
            path (str): Output file path. e.g. "data/outputs/report.txt"
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        report = self.build_text_report()
        with open(path, "w", encoding="utf-8") as f:
            f.write(report)
        print(f"Text report saved: {path}")

    def save_json_report(self, path: str) -> None:
        """
        Build and save the JSON report to disk.

        Args:
            path (str): Output file path. e.g. "data/outputs/report.json"
        """
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
        return (
            f"{'='*70}\n"
            f"  SURVEYOR AI — SURVEY VALIDITY AUDIT REPORT\n"
            f"{'='*70}\n"
            f"  Generated : {self.generated_at}\n"
            f"  Items     : {inst.total_items}\n"
            f"  Rules     : {len(inst.rule_summary)}\n"
            f"  Risk Level: {inst.instrument_validity_risk}\n"
            f"{'='*70}"
        )

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
            f"Total violations     : {inst.total_item_violations}",
            "",
            f"Priority breakdown:",
            f"  HIGH   : {inst.high_priority_count} items",
            f"  MEDIUM : {inst.medium_priority_count} items",
            f"  LOW    : {inst.low_priority_count} items",
            f"  CLEAN  : {inst.clean_items} items",
            "",
            f"INSTRUMENT VALIDITY RISK: {inst.instrument_validity_risk}",
            "",
            "Rule violation summary:",
        ]

        for rule_id, count in sorted(inst.rule_summary.items()):
            label = self.PRINCIPLE_LABELS.get(rule_id, rule_id)
            lines.append(f"  {rule_id} ({label}): {count}")

        return "\n".join(lines)

    def _section_2_instrument_findings(self) -> str:
        inst = self.diagnostic.instrument
        lines = [
            "SECTION 2 — INSTRUMENT-LEVEL FINDINGS",
            "-" * 40,
        ]

        if not inst.instrument_findings:
            lines.append("No instrument-level findings.")
            return "\n".join(lines)

        for i, finding in enumerate(inst.instrument_findings, 1):
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
                f"  Evidence : {finding.evidence}",
                "",
            ]

        return "\n".join(lines)

    def _section_3_high_priority_items(self) -> str:
        lines = [
            "SECTION 3 — HIGH PRIORITY ITEMS (require immediate attention)",
            "-" * 40,
        ]

        if not self.diagnostic.high_priority_items:
            lines.append("No high priority items detected.")
            return "\n".join(lines)

        for d in self.diagnostic.high_priority_items:
            lines += [
                f"Item {d.item_id:>2} | composite={d.composite_severity:.2f} "
                f"| max={d.max_severity:.2f} "
                f"| rules fired: {', '.join(d.rules_fired)}",
                f"  Text: {d.text[:90]}{'...' if len(d.text) > 90 else ''}",
            ]
            for v in d.violations:
                label = self.PRINCIPLE_LABELS.get(v.principle, v.principle)
                lines.append(
                    f"  [{v.principle}] sev={v.severity:.2f} "
                    f"{label}: {v.evidence[:80]}..."
                )
            lines.append("")

        return "\n".join(lines)

    def _section_4_full_item_diagnostics(self) -> str:
        lines = [
            "SECTION 4 — FULL ITEM DIAGNOSTICS",
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
                    f"  Text: {d.text[:80]}{'...' if len(d.text) > 80 else ''}",
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

    def _section_5_recommendations(self) -> str:
        inst = self.diagnostic.instrument
        lines = [
            "SECTION 5 — RECOMMENDATIONS",
            "-" * 40,
        ]

        # Instrument-level recommendations
        inst_rec = []

        if any(f.principle == "P006" for f in inst.instrument_findings):
            inst_rec.append(
                "1. ADD REVERSE-SCORED ITEMS: All 75 items are positively "
                "worded. Add at least 15-20 reverse-scored items (20-25% "
                "of instrument) to detect and correct acquiescence bias."
            )

        if any(f.principle == "P020" for f in inst.instrument_findings):
            inst_rec.append(
                "2. REDUCE INSTRUMENT LENGTH: At 75 items the instrument "
                "exceeds recommended length for professional respondents. "
                "Consider reducing to 50-60 items by removing redundant "
                "or low-discriminating items after pilot testing."
            )

        if any(f.principle == "P008" for f in inst.instrument_findings):
            inst_rec.append(
                "3. IMPROVE SCALE ANCHORS: Replace vague frequency labels "
                "(Often, Sometimes, Rarely) with numerically anchored "
                "alternatives or behaviorally defined anchors. "
                "e.g. '5 - Always (100% of the time)' or use an "
                "agreement scale (Strongly Agree to Strongly Disagree) "
                "which is better matched to self-report attitude items."
            )

        if inst_rec:
            lines.append("INSTRUMENT-LEVEL:")
            lines += inst_rec
            lines.append("")

        # Item-level recommendations
        lines.append("ITEM-LEVEL (top priority rewrites):")

        top_items = sorted(
            self.diagnostic.high_priority_items,
            key=lambda d: d.composite_severity,
            reverse=True
        )[:5]

        for d in top_items:
            lines += [
                f"Item {d.item_id} (composite severity: "
                f"{d.composite_severity:.2f}):",
                f"  Current: {d.text[:90]}",
                f"  Issues : {', '.join(d.rules_fired)}",
                f"  Action : Rewrite to address "
                f"{self.PRINCIPLE_LABELS.get(d.rules_fired[0], d.rules_fired[0])}",
                "",
            ]

        lines += [
            "GENERAL RECOMMENDATIONS:",
            "- Conduct cognitive interviews with 5-10 representative "
            "respondents before full deployment",
            "- Pilot test with a small sample to assess item "
            "discrimination and scale reliability (Cronbach alpha)",
            "- Consider splitting the instrument into subscales "
            "administered separately to reduce fatigue",
            "- Review all HIGH priority items with a survey methodology "
            "expert before finalizing",
        ]

        return "\n".join(lines)

    def _footer(self) -> str:
        return (
            f"{'='*70}\n"
            f"  END OF REPORT — Surveyor AI\n"
            f"  This report is a theory-inspired diagnostic, not a\n"
            f"  validated psychometric assessment. All findings should\n"
            f"  be reviewed by a qualified survey methodology expert.\n"
            f"{'='*70}"
        )