"""
tests/test_parser.py

Test suite for the full parser pipeline:
    TxtLoader → TextCleaner → SurveyParser → SurveyData

HOW TO RUN:
    From your project root:
        python -m pytest tests/test_parser.py -v

WHAT THIS COVERS:
    - TxtLoader raises correct errors
    - TextCleaner fixes broken lines, fused items, extracts scale
    - SurveyParser produces correct item count, metadata, item structure
    - Full pipeline test against the real survey file
"""

import pytest
import os
import tempfile

from app.parser.txt_loader import TxtLoader
from app.parser.text_cleaner import TextCleaner
from app.parser.survey_parser import SurveyParser


# ----------------------------------------------------------------------
# FIXTURES
# Reusable test data shared across multiple tests
# ----------------------------------------------------------------------

@pytest.fixture
def real_survey_path():
    """Path to the real survey file."""
    return "data/raw_surveys/survey_001.txt"


@pytest.fixture
def minimal_survey_txt():
    """
    A minimal synthetic survey written directly in the test.
    Does not depend on any file on disk.
    Useful for testing specific behaviors in isolation.
    """
    return """5 - Always (A)
4 - Often (O)
3 - Sometimes (S)
2 - Rarely (R)
1 - Never (N)

1. I communicate clearly with my team.
2. I ensure that all policies are followed
and implemented correctly.
3. I can motivate my people through rewards and
recognition in the organization.
"""


@pytest.fixture
def fused_item_txt():
    """
    Synthetic survey with a fused item (missing line break between items).
    Tests the specific _fix_fused_items behavior.
    """
    return """5 - Always (A)
4 - Often (O)
3 - Sometimes (S)
2 - Rarely (R)
1 - Never (N)

1. I communicate clearly with my team.
2. I affirm that the anticipation of a reward can encourage personnel to work hard to achieve reward3. I understand that I can motivate personnel by providing incentives.
4. I ensure that all policies are followed.
"""


# ----------------------------------------------------------------------
# TxtLoader TESTS
# ----------------------------------------------------------------------

class TestTxtLoader:

    def test_raises_file_not_found(self):
        """Loading a nonexistent file must raise FileNotFoundError."""
        loader = TxtLoader("data/raw_surveys/nonexistent_file.txt")
        with pytest.raises(FileNotFoundError):
            loader.load()

    def test_raises_value_error_on_empty_file(self, tmp_path):
        """Loading an empty file must raise ValueError."""
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")
        loader = TxtLoader(str(empty_file))
        with pytest.raises(ValueError):
            loader.load()

    def test_loads_real_survey(self, real_survey_path):
        """Loading the real survey file must return a non-empty string."""
        raw = TxtLoader(real_survey_path).load()
        assert isinstance(raw, str)
        assert len(raw) > 0

    def test_returns_string(self, tmp_path):
        """load() must always return a str."""
        f = tmp_path / "survey.txt"
        f.write_text("1. I do something important.")
        raw = TxtLoader(str(f)).load()
        assert isinstance(raw, str)


# ----------------------------------------------------------------------
# TextCleaner TESTS
# ----------------------------------------------------------------------

class TestTextCleaner:

    def test_extracts_scale_header(self, minimal_survey_txt):
        """Scale header must be extracted and not appear in items."""
        cleaned = TextCleaner(minimal_survey_txt).clean()
        assert cleaned.scale_header is not None
        assert "Always" in cleaned.scale_header
        assert "Never" in cleaned.scale_header

    def test_scale_not_in_items(self, minimal_survey_txt):
        """Scale lines must not appear as survey items."""
        cleaned = TextCleaner(minimal_survey_txt).clean()
        for item in cleaned.items:
            assert "Always" not in item
            assert "Never" not in item

    def test_rejoins_broken_lines(self, minimal_survey_txt):
        """Multi-line items must be joined into single strings."""
        cleaned = TextCleaner(minimal_survey_txt).clean()
        # Item 2 is broken across two lines in the fixture
        item_2 = next(i for i in cleaned.items if i.startswith("2."))
        assert "\n" not in item_2
        assert "followed and implemented correctly" in item_2

    def test_fixes_fused_items(self, fused_item_txt):
        """Fused items (reward3.) must be split into separate items."""
        cleaned = TextCleaner(fused_item_txt).clean()
        assert len(cleaned.items) == 4

    def test_correct_item_count_minimal(self, minimal_survey_txt):
        """Minimal survey must produce exactly 3 items."""
        cleaned = TextCleaner(minimal_survey_txt).clean()
        assert len(cleaned.items) == 3

    def test_correct_item_count_real(self, real_survey_path):
        """Real survey must produce exactly 75 items."""
        raw = TxtLoader(real_survey_path).load()
        cleaned = TextCleaner(raw).clean()
        assert len(cleaned.items) == 75

    def test_items_are_strings(self, minimal_survey_txt):
        """All items must be strings."""
        cleaned = TextCleaner(minimal_survey_txt).clean()
        for item in cleaned.items:
            assert isinstance(item, str)


# ----------------------------------------------------------------------
# SurveyParser TESTS
# ----------------------------------------------------------------------

class TestSurveyParser:

    def _parse(self, raw_text: str):
        """Helper: run full pipeline on a raw text string."""
        cleaned = TextCleaner(raw_text).clean()
        return SurveyParser(cleaned).parse()

    def test_total_items_real_survey(self, real_survey_path):
        """Real survey must parse to exactly 75 items."""
        raw = TxtLoader(real_survey_path).load()
        survey = self._parse(raw)
        assert survey.metadata["total_items"] == 75

    def test_zero_parse_warnings(self, real_survey_path):
        """Real survey must produce zero parse warnings."""
        raw = TxtLoader(real_survey_path).load()
        survey = self._parse(raw)
        assert survey.metadata["parse_warnings"] == 0

    def test_scale_points_correct(self, real_survey_path):
        """Scale must have exactly 5 points."""
        raw = TxtLoader(real_survey_path).load()
        survey = self._parse(raw)
        assert survey.metadata["scale"]["points"] == 5

    def test_scale_labels_correct(self, real_survey_path):
        """Scale labels must match the source file exactly."""
        raw = TxtLoader(real_survey_path).load()
        survey = self._parse(raw)
        labels = survey.metadata["scale"]["labels"]
        assert labels["5"] == "Always"
        assert labels["1"] == "Never"

    def test_item_structure(self, real_survey_path):
        """Every item must have the required keys."""
        raw = TxtLoader(real_survey_path).load()
        survey = self._parse(raw)
        required_keys = {"item_id", "text", "scale", "word_count", "is_question", "construct"}
        for item in survey.items:
            assert required_keys.issubset(item.keys())

    def test_item_ids_are_sequential(self, real_survey_path):
        """Item IDs must be sequential from 1 to 75."""
        raw = TxtLoader(real_survey_path).load()
        survey = self._parse(raw)
        ids = [item["item_id"] for item in survey.items]
        assert ids == list(range(1, 76))

    def test_construct_is_null(self, real_survey_path):
        """All constructs must be None at parser stage."""
        raw = TxtLoader(real_survey_path).load()
        survey = self._parse(raw)
        for item in survey.items:
            assert item["construct"] is None

    def test_all_items_are_statements(self, real_survey_path):
        """All 75 items in this survey are statements, not questions."""
        raw = TxtLoader(real_survey_path).load()
        survey = self._parse(raw)
        assert survey.metadata["question_count"] == 0
        assert survey.metadata["statement_count"] == 75

    def test_item_1_text(self, real_survey_path):
        """Item 1 text must match expected content."""
        raw = TxtLoader(real_survey_path).load()
        survey = self._parse(raw)
        assert survey.items[0]["item_id"] == 1
        assert "punish" in survey.items[0]["text"]

    def test_item_26_not_fused(self, real_survey_path):
        """Item 26 and 27 must be separate — fused item bug check."""
        raw = TxtLoader(real_survey_path).load()
        survey = self._parse(raw)
        item_26 = survey.items[25]
        item_27 = survey.items[26]
        assert item_26["item_id"] == 26
        assert item_27["item_id"] == 27
        assert "achieve reward" in item_26["text"]
        assert item_27["text"].startswith("I understand")

    def test_word_count_is_positive(self, real_survey_path):
        """Every item must have a positive word count."""
        raw = TxtLoader(real_survey_path).load()
        survey = self._parse(raw)
        for item in survey.items:
            assert item["word_count"] > 0