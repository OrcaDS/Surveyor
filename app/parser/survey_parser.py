"""
app/parser/survey_parser.py

Converts a CleanedSurvey into a structured list of survey item dictionaries.

DESIGN RULE (do not violate):
    This layer produces FACTS only. Every field stored here must be
    directly derivable from the raw text without interpretation.
    Classification labels, construct names, and validity judgments
    belong to layers above this one. Never let interpretations flow downward.

INPUT:  CleanedSurvey (from text_cleaner.py)
OUTPUT: SurveyData (list of structured item dicts + survey-level metadata)
"""

import re
from app.parser.text_cleaner import CleanedSurvey


class SurveyParser:
    """
    Parses a CleanedSurvey into structured data.

    Usage:
        parser = SurveyParser(cleaned_survey)
        survey_data = parser.parse()

        survey_data.items     # list of item dicts
        survey_data.metadata  # survey-level facts
    """

    # Matches the number at the start of a cleaned item e.g. "14. I ensure..."
    ITEM_NUMBER_PATTERN = re.compile(r"^(\d{1,2})\.\s+(.+)$", re.DOTALL)

    # Matches scale header lines e.g. "5 - Always (A)"
    SCALE_LABEL_PATTERN = re.compile(
        r"(\d)\s*[-–]\s*(\w+(?:\s+\w+)?)\s*(?:\([A-Z]\))?"
    )

    def __init__(self, cleaned_survey: CleanedSurvey):
        """
        Args:
            cleaned_survey (CleanedSurvey): Output from TextCleaner.clean()
        """
        self.cleaned_survey = cleaned_survey

    def parse(self) -> "SurveyData":
        """
        Run the full parse pipeline.

        Returns:
            SurveyData: Container with structured items and survey metadata.
        """
        scale = self._parse_scale(self.cleaned_survey.scale_header)
        items = [self._parse_item(raw, scale) for raw in self.cleaned_survey.items]
        metadata = self._build_metadata(items, scale)

        return SurveyData(items=items, metadata=metadata)

    # ------------------------------------------------------------------
    # PRIVATE METHODS
    # ------------------------------------------------------------------

    def _parse_scale(self, scale_header: str) -> dict:
        """
        Extract scale facts directly from the scale header string.

        Stores only what the text literally says:
            - how many points
            - what label is attached to each point

        Does NOT name the scale type (e.g. "likert_5") — that is
        an interpretation and belongs to a higher layer.

        Args:
            scale_header (str | None): Raw scale block from CleanedSurvey.

        Returns:
            dict: Scale facts, or empty dict if no scale header found.
        """
        if not scale_header:
            return {}

        labels = {}
        for match in self.SCALE_LABEL_PATTERN.finditer(scale_header):
            point = match.group(1)   # "5"
            label = match.group(2).strip()  # "Always"
            labels[point] = label

        if not labels:
            return {}

        return {
            "points": len(labels),
            "labels": labels
        }

    def _parse_item(self, raw_item: str, scale: dict) -> dict:
        """
        Parse a single cleaned item string into a structured dictionary.

        Extracts only deterministic facts:
            - item_id:     the number prefix
            - text:        the statement without the number
            - scale:       passed through from survey-level scale
            - word_count:  derived directly from text
            - is_question: derived from presence of "?"
            - construct:   always None here (semantic layer's responsibility)

        Args:
            raw_item (str): A single cleaned item e.g. "1. I am in the position..."
            scale (dict):   The parsed scale dict from _parse_scale()

        Returns:
            dict: Structured item dictionary.
        """
        match = self.ITEM_NUMBER_PATTERN.match(raw_item.strip())

        if not match:
            # If somehow an item slipped through without a number, flag it
            return {
                "item_id": None,
                "text": raw_item.strip(),
                "scale": scale,
                "word_count": len(raw_item.split()),
                "is_question": "?" in raw_item,
                "construct": None,
                "parse_warning": "Item number not detected"
            }

        item_id = int(match.group(1))
        text = match.group(2).strip()

        return {
            "item_id": item_id,
            "text": text,
            "scale": scale,
            "word_count": len(text.split()),
            "is_question": "?" in text,
            "construct": None
        }

    def _build_metadata(self, items: list[dict], scale: dict) -> dict:
        """
        Build survey-level facts from the full item list.

        These are facts about the instrument as a whole, not individual items.

        Returns:
            dict: Survey-level metadata.
        """
        total = len(items)
        warnings = [i for i in items if "parse_warning" in i]
        question_count = sum(1 for i in items if i["is_question"])
        statement_count = total - question_count
        avg_word_count = (
            round(sum(i["word_count"] for i in items) / total, 2)
            if total > 0 else 0
        )

        return {
            "total_items": total,
            "scale": scale,
            "question_count": question_count,
            "statement_count": statement_count,
            "avg_word_count": avg_word_count,
            "parse_warnings": len(warnings)
        }


# ----------------------------------------------------------------------
# DATA CONTAINER
# ----------------------------------------------------------------------

class SurveyData:
    """
    Container for the output of SurveyParser.parse().

    Attributes:
        items (list[dict]):  One dict per survey item.
        metadata (dict):     Survey-level facts.
    """

    def __init__(self, items: list[dict], metadata: dict):
        self.items = items
        self.metadata = metadata

    def __repr__(self):
        return (
            f"SurveyData("
            f"total_items={self.metadata.get('total_items')}, "
            f"scale_points={self.metadata.get('scale', {}).get('points')}, "
            f"warnings={self.metadata.get('parse_warnings')})"
        )