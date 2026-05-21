"""
app/parser/text_cleaner.py

Cleans raw survey text before it reaches the parser.

RESPONSIBILITIES (in execution order):
  1. Extract scale header as metadata
  2. Rejoin broken lines into whole sentences
  3. Handle hyphen-split compounds across lines
  4. Detect and fix fused items (e.g. "...reward27. I understand")
  5. Normalize whitespace
  6. Return clean item list + metadata separately

WHY THIS IS SEPARATE FROM THE PARSER:
  The parser's job is to understand structure.
  The cleaner's job is to make the text readable enough for the parser to do that.
  Mixing both responsibilities into one class creates a fragile, untestable mess.
"""

import re
from typing import Optional


class TextCleaner:
    """
    Accepts raw text from any loader and returns a CleanedSurvey object
    containing normalized question strings and extracted metadata.

    Usage:
        cleaner = TextCleaner(raw_text)
        cleaned = cleaner.clean()

        cleaned.items        # list of clean question strings
        cleaned.scale_header # raw scale definition block, if found
    """

    # Matches a scale header line like "5 - Always (A)" or "1 - Never (N)"
    SCALE_LINE_PATTERN = re.compile(
        r"^\s*\d\s*[-–]\s*\w+.*$", re.MULTILINE
    )

    # Matches the start of a new numbered item: "27." or "27 ."
    ITEM_START_PATTERN = re.compile(r"(?<!\d)(\d{1,2})\.\s+")

    # Matches fused items: a word immediately followed by a number+period
    # e.g. "reward27." or "personnel31."
    FUSED_ITEM_PATTERN = re.compile(r"([a-zA-Z])(\d{1,2})\.\s+")

    def __init__(self, raw_text: str):
        """
        Args:
            raw_text (str): Raw string output from any BaseLoader subclass.
        """
        self.raw_text = raw_text

    def clean(self) -> "CleanedSurvey":
        """
        Run the full cleaning pipeline in order.

        Returns:
            CleanedSurvey: Dataclass containing cleaned items and metadata.
        """
        text = self.raw_text

        # Step 1 — Pull out scale header before touching anything else
        scale_header, text = self._extract_scale_header(text)

        # Step 2 — Fix hyphen-split compounds BEFORE rejoining lines
        # (must come before line rejoining or the hyphen context is lost)
        text = self._fix_hyphen_splits(text)

        # Step 3 — Fix fused items BEFORE rejoining lines
        # (must come before rejoining or the fusion becomes invisible)
        text = self._fix_fused_items(text)

        # Step 4 — Rejoin broken lines into whole sentences
        text = self._rejoin_broken_lines(text)

        # Step 5 — Normalize whitespace throughout
        text = self._normalize_whitespace(text)

        # Step 6 — Split into individual items
        items = self._split_into_items(text)

        return CleanedSurvey(items=items, scale_header=scale_header)

    # ------------------------------------------------------------------
    # PRIVATE METHODS — each handles exactly one cleaning responsibility
    # ------------------------------------------------------------------

    def _extract_scale_header(self, text: str) -> tuple[str, str]:
        """
        Detect and remove the scale definition block from the top of the survey.

        A scale block looks like:
            5 - Always (A)
            4 - Often (O)
            3 - Sometimes (S)
            2 - Rarely (R)
            1 - Never (N)

        Returns:
            tuple: (scale_header_string, remaining_text)
        """
        lines = text.splitlines()
        scale_lines = []
        non_scale_lines = []
        in_scale_block = False

        for line in lines:
            if self.SCALE_LINE_PATTERN.match(line):
                scale_lines.append(line.strip())
                in_scale_block = True
            else:
                # Once we exit the scale block, everything else is survey body
                non_scale_lines.append(line)

        scale_header = "\n".join(scale_lines) if scale_lines else None
        remaining_text = "\n".join(non_scale_lines)

        return scale_header, remaining_text

    def _fix_hyphen_splits(self, text: str) -> str:
        """
        Rejoin words that were split across lines with a hyphen.

        Example:
            "non-\nteaching" → "non-teaching"
            "co-\noperation" → "co-operation"

        The pattern matches: word-chars + hyphen + newline + word-chars
        """
        return re.sub(r"(\w+)-\n(\w+)", r"\1-\2", text)

    def _fix_fused_items(self, text: str) -> str:
        """
        Insert a newline between fused items.

        Example:
            "...hard to achieve reward27. I understand..."
            →
            "...hard to achieve reward\n27. I understand..."

        This handles the case where a missing line break causes two items
        to run together with no separator.
        """
        return self.FUSED_ITEM_PATTERN.sub(r"\1\n\2. ", text)

    def _rejoin_broken_lines(self, text: str) -> str:
        """
        Rejoin lines that are broken mid-sentence due to column wrapping.

        LOGIC:
        A line break is a REAL boundary if the next line starts with a number+period
        (new item) or the current line ends with a period (sentence end).
        Otherwise, it is a soft wrap and should be joined with a space.

        We process line by line and decide whether to join or preserve each break.
        """
        lines = text.splitlines()
        result = []
        buffer = ""

        for line in lines:
            stripped = line.strip()

            if not stripped:
                # Blank line — flush buffer and preserve the break
                if buffer:
                    result.append(buffer)
                    buffer = ""
                result.append("")
                continue

            # Does this line start a new numbered item?
            starts_new_item = bool(self.ITEM_START_PATTERN.match(stripped))

            if starts_new_item:
                # Flush whatever was in the buffer first
                if buffer:
                    result.append(buffer)
                buffer = stripped
            else:
                if buffer:
                    # Does the buffer line end with a sentence terminator?
                    if buffer.endswith((".", "?", "!")):
                        result.append(buffer)
                        buffer = stripped
                    else:
                        # Soft wrap — join with a space
                        buffer += " " + stripped
                else:
                    buffer = stripped

        # Don't forget the last item in the buffer
        if buffer:
            result.append(buffer)

        return "\n".join(result)

    def _normalize_whitespace(self, text: str) -> str:
        """
        Clean up spacing artifacts:
        - Collapse multiple spaces into one
        - Collapse 3+ consecutive newlines into two
        - Strip leading/trailing whitespace from each line
        """
        # Collapse multiple spaces
        text = re.sub(r" {2,}", " ", text)

        # Strip each line
        lines = [line.strip() for line in text.splitlines()]
        text = "\n".join(lines)

        # Collapse excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text)

        return text.strip()

    def _split_into_items(self, text: str) -> list[str]:
        """
        Split the cleaned text into individual question strings.

        Each item starts with a number followed by a period and a space.
        We use re.split with a capture group to preserve the item number
        in the output string.

        Returns:
            list[str]: Each element is one complete survey item,
                       e.g. "1. I am in the position to punish..."
        """
        # Split on item boundaries, keeping the number+period as part of the item
        parts = re.split(r"(?=(?<!\d)\d{1,2}\.\s)", text)

        items = []
        for part in parts:
            cleaned = part.strip()
            if cleaned and self.ITEM_START_PATTERN.match(cleaned):
                items.append(cleaned)

        return items


# ----------------------------------------------------------------------
# DATA CONTAINER
# ----------------------------------------------------------------------

class CleanedSurvey:
    """
    Simple container for the output of TextCleaner.clean().

    Attributes:
        items (list[str]):       Cleaned, rejoined survey question strings.
        scale_header (str|None): The raw scale definition block, or None
                                 if no scale header was detected.
    """

    def __init__(self, items: list[str], scale_header: Optional[str]):
        self.items = items
        self.scale_header = scale_header

    def __repr__(self):
        return (
            f"CleanedSurvey("
            f"items={len(self.items)}, "
            f"scale_header={'present' if self.scale_header else 'none'})"
        )