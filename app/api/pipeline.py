"""
app/api/pipeline.py

Shared audit pipeline for both CLI and API entry points.

RESPONSIBILITIES:
    Accept raw survey text, run the full audit pipeline,
    and return a SurveyDiagnostic object.

DESIGN NOTE:
    Returns SurveyDiagnostic, not a dict. Callers decide
    how to serialize it:
        CLI   -> ReportBuilder.save_text_report + save_json_report
        API   -> ReportBuilder.build_json_report
    This keeps the pipeline contract clean and avoids
    duplicating serialization logic across entry points.
"""

from app.parser.raw_text_loader import RawTextLoader
from app.parser.text_cleaner import TextCleaner
from app.parser.survey_parser import SurveyParser
from app.principles.registry import build_default_registry
from app.diagnostics.diagnostic_aggregator import DiagnosticAggregator
from app.diagnostics.diagnostic_aggregator import SurveyDiagnostic


def run_pipeline(raw_text: str) -> SurveyDiagnostic:
    """
    Run the full survey audit pipeline on raw text content.

    Args:
        raw_text (str): Raw survey text content.

    Returns:
        SurveyDiagnostic: Full structured diagnostic object.

    Raises:
        ValueError: If the content is empty or unparseable.
    """
    raw = RawTextLoader(raw_text).load()
    cleaned = TextCleaner(raw).clean()
    survey = SurveyParser(cleaned).parse()

    registry = build_default_registry()
    results = registry.evaluate(survey.items)

    aggregator = DiagnosticAggregator(survey, results)
    return aggregator.aggregate()