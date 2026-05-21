"""
app/parser/txt_loader.py

Concrete loader for plain-text (.txt) survey files.

This is the only loader we build for MVP.
PDF and DOCX loaders will follow the exact same structure later.
"""

from app.parser.base_loader import BaseLoader


class TxtLoader(BaseLoader):
    """
    Loads a .txt survey file and returns its content as a plain string.

    Usage:
        loader = TxtLoader("data/raw_surveys/survey_001.txt")
        raw_text = loader.load()
    """

    def load(self) -> str:
        """
        Read the .txt file and return its full content.

        Returns:
            str: Raw text content of the survey file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file is empty.
        """
        # Use the shared validation from BaseLoader before doing anything
        self._validate_path()

        with open(self.file_path, "r", encoding="utf-8") as f:
            content = f.read()

        if not content.strip():
            raise ValueError(
                f"Survey file is empty: '{self.file_path}'\n"
                f"Check that the file contains survey content."
            )

        return content