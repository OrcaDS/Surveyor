"""
test_rules.py

Manual test runner for any principle rule.
Run from project root: python test_rules.py
"""

from app.parser.txt_loader import TxtLoader
from app.parser.text_cleaner import TextCleaner
from app.parser.survey_parser import SurveyParser
from app.principles.p001 import P001
from app.principles.p002 import P002
from app.principles.p003 import P003
from app.principles.p004 import P004
from app.principles.p005 import P005

raw = TxtLoader('data/raw_surveys/survey_001.txt').load()
cleaned = TextCleaner(raw).clean()
survey = SurveyParser(cleaned).parse()

rules = [P001(), P002(), P003(), P004(), P005()]

for rule in rules:
    print(f"{'='*60}")
    print(f"  {rule.id} — {rule.description}")
    print(f"{'='*60}")
    violations = 0
    for item in survey.items:
        result = rule.evaluate(item)
        if result is not None:
            violations += 1
            print(f"\nItem {item['item_id']}: {item['text'][:70]}...")
            print(f"  Severity : {result.severity}")
            print(f"  Evidence : {result.evidence}")
    print(f"\nTotal violations: {violations}/75\n")