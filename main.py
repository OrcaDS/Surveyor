"""
main.py

Surveyor AI — Survey Validity Audit Engine
Entry point for the full pipeline.

USAGE:
    python main.py

    By default runs against data/raw_surveys/survey_001.txt
    and saves reports to data/outputs/
"""

from app.parser.txt_loader import TxtLoader
from app.parser.text_cleaner import TextCleaner
from app.parser.survey_parser import SurveyParser
from app.principles.registry import build_default_registry
from app.diagnostics.diagnostic_aggregator import DiagnosticAggregator
from app.reporting.report_builder import ReportBuilder

SURVEY_PATH = "data/raw_surveys/survey_003.txt"
TEXT_REPORT_PATH = "data/outputs/report.txt"
JSON_REPORT_PATH = "data/outputs/report.json"


def run_audit(survey_path: str) -> None:
    print(f"Surveyor AI — Survey Validity Audit Engine")
    print(f"{'='*50}")

    # --- Stage 1: Parse ---
    print(f"[1/4] Parsing: {survey_path}")
    raw = TxtLoader(survey_path).load()
    cleaned = TextCleaner(raw).clean()
    survey = SurveyParser(cleaned).parse()
    print(f"      {survey.metadata['total_items']} items parsed.")

    # --- Stage 2: Evaluate ---
    print(f"[2/4] Evaluating principles...")
    registry = build_default_registry()
    results = registry.evaluate(survey.items)
    print(f"      {registry.rule_count()} rules run. "
          f"{results.total_item_violations()} violations found.")

    # --- Stage 3: Aggregate ---
    print(f"[3/4] Aggregating diagnostics...")
    aggregator = DiagnosticAggregator(survey, results)
    diagnostic = aggregator.aggregate()
    inst = diagnostic.instrument
    print(f"      Validity risk: {inst.instrument_validity_risk} | "
          f"HIGH priority items: {inst.high_priority_count}")

    # --- Stage 4: Report ---
    print(f"[4/4] Generating reports...")
    builder = ReportBuilder(diagnostic)
    builder.save_text_report(TEXT_REPORT_PATH)
    builder.save_json_report(JSON_REPORT_PATH)

    print(f"\nDone. Reports saved to data/outputs/")
    print(f"  Text : {TEXT_REPORT_PATH}")
    print(f"  JSON : {JSON_REPORT_PATH}")


if __name__ == "__main__":
    run_audit(SURVEY_PATH)