"""
test_rules.py

Manual test runner for all principle rules.
Handles both item-level and instrument-level rules automatically.
Run from project root: python test_rules.py
"""

from app.parser.txt_loader import TxtLoader
from app.parser.text_cleaner import TextCleaner
from app.parser.survey_parser import SurveyParser
from app.principles.p015 import P015
from app.principles.p016 import P016
from app.principles.p020 import P020



raw = TxtLoader('data/raw_surveys/survey_001.txt').load()
cleaned = TextCleaner(raw).clean()
survey = SurveyParser(cleaned).parse()
items = survey.items

rules = [P015(), P016(), P020()]

for rule in rules:
    print(f"{'='*60}")
    print(f"  {rule.id} — {rule.description}")
    print(f"{'='*60}")

    if rule.is_instrument_level():
        # Instrument-level rules get the full item list
        results = rule.evaluate_instrument(items)
        if not results:
            print("\n  No violations detected.\n")
        else:
            for result in results:
                print(f"\n  Severity : {result.severity}")
                print(f"  Evidence : {result.evidence}")
                affected = result.affected_items
                if len(affected) > 10:
                    print(f"  Affected : All {len(affected)} items")
                else:
                    print(f"  Affected : {affected}")
            print(f"\nTotal instrument-level findings: {len(results)}\n")
    else:
        # Item-level rules evaluate one item at a time
        violations = 0
        for item in items:
            result = rule.evaluate(item)
            if result is not None:
                violations += 1
                print(f"\nItem {item['item_id']}: {item['text'][:70]}...")
                print(f"  Severity : {result.severity}")
                print(f"  Evidence : {result.evidence}")
        print(f"\nTotal violations: {violations}/75\n")