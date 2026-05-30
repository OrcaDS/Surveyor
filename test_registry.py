"""
test_registry.py

End-to-end test of the full principle registry.
Run from project root: python test_registry.py
"""

from app.parser.txt_loader import TxtLoader
from app.parser.text_cleaner import TextCleaner
from app.parser.survey_parser import SurveyParser
from app.principles.registry import build_default_registry

# --- Parse survey ---
raw = TxtLoader('data/raw_surveys/survey_001.txt').load()
cleaned = TextCleaner(raw).clean()
survey = SurveyParser(cleaned).parse()

# --- Run registry ---
registry = build_default_registry()
results = registry.evaluate(survey.items)

# --- Summary ---
print("=" * 60)
print("  REGISTRY EVALUATION SUMMARY")
print("=" * 60)
print(f"  Rules registered : {registry.rule_count()}")
print(f"  Items evaluated  : {survey.metadata['total_items']}")
print(f"  Item violations  : {results.total_item_violations()}")
print(f"  Instrument findings: {results.total_instrument_violations()}")
print(f"  Rule errors      : {len(results.rule_errors)}")
print()

# --- Per-rule breakdown ---
print("Per-rule violation counts:")
for rule_id, count in results.summary.items():
    print(f"  {rule_id}: {count}")
print()

# --- Top 10 highest severity items ---
print("Top 10 highest severity items:")
for item_id, max_sev in results.highest_severity_items(10):
    violations = results.violations_for_item(item_id)
    rules_fired = [v.principle for v in violations]
    print(f"  Item {item_id:>2}: max severity {max_sev:.2f} | rules: {rules_fired}")
print()

# --- Instrument-level findings ---
print("Instrument-level findings:")
for finding in results.instrument_violations:
    print(f"  {finding.principle}: severity {finding.severity}")
    print(f"  {finding.evidence[:100]}...")
    print()

# --- Any errors? ---
if results.rule_errors:
    print("RULE ERRORS:")
    for rule_id, error in results.rule_errors:
        print(f"  {rule_id}: {error}")