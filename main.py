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
from app.api.pipeline import run_pipeline
from app.reporting.report_builder import ReportBuilder

SURVEY_PATH = "data/raw_surveys/survey_001.txt"
TEXT_REPORT_PATH = "data/outputs/report.txt"
JSON_REPORT_PATH = "data/outputs/report.json"


def run_audit(survey_path: str) -> None:
    print("Surveyor AI — Survey Validity Audit Engine")
    print("=" * 50)

    # --- Load from disk ---
    print(f"[1/3] Loading: {survey_path}")
    raw_text = TxtLoader(survey_path).load()

    # --- Run shared pipeline ---
    print("[2/3] Running audit pipeline...")
    diagnostic = run_pipeline(raw_text)
    inst = diagnostic.instrument
    print(f"      {inst.total_items} items evaluated.")
    print(f"      {inst.total_item_violations} item violations found.")
    print(f"      Validity risk: {inst.instrument_validity_risk} | "
          f"HIGH priority items: {inst.high_priority_count}")

    # --- Save reports ---
    print("[3/3] Generating reports...")
    builder = ReportBuilder(diagnostic)
    builder.save_text_report(TEXT_REPORT_PATH)
    builder.save_json_report(JSON_REPORT_PATH)

    print(f"\nDone. Reports saved to data/outputs/")
    print(f"  Text : {TEXT_REPORT_PATH}")
    print(f"  JSON : {JSON_REPORT_PATH}")


if __name__ == "__main__":
    run_audit(SURVEY_PATH)