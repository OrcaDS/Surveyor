"""
app/parser/raw_text_loader.py

Concrete loader for raw text content passed directly as a string.

Used by the API layer to avoid writing uploaded content to disk.
Follows the same Strategy Pattern as TxtLoader but accepts content
in memory rather than reading from a file path.
"""

from app.parser.base_loader import BaseLoader


class RawTextLoader(BaseLoader):
    """
    Loads survey content from a string already in memory.

    Usage:
        loader = RawTextLoader(raw_text)
        content = loader.load()
    """

    def __init__(self, content: str):
        """
        Args:
            content (str): Raw survey text content.
        """
        self._content = content
        # BaseLoader expects file_path — pass a sentinel value.
        # _validate_path() is never called on this loader.
        super().__init__(file_path="<in-memory>")

    def load(self) -> str:
        """
        Return the content string directly.

        Returns:
            str: Raw text content.

        Raises:
            ValueError: If content is empty.
        """
        if not self._content.strip():
            raise ValueError(
                "Survey content is empty. "
                "Ensure the uploaded file contains survey text."
            )
        return self._content