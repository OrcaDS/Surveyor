"""
app/parser/base_loader.py

Abstract base class for all survey file loaders.

WHY THIS EXISTS:
  The parser should never care where text came from — a .txt file,
  a PDF, or a DOCX. Each loader's only job is to return clean raw text.
  By defining a shared interface here, we can swap or add loaders
  without touching any other module. This is the Strategy Pattern.

ADDING A NEW LOADER LATER:
  1. Create a new file (e.g., pdf_loader.py)
  2. Import BaseLoader and subclass it
  3. Implement the load() method
  4. Done. Nothing else changes.
"""

from abc import ABC, abstractmethod


class BaseLoader(ABC):
    """
    Abstract base class that all file loaders must inherit from.

    Every subclass must implement load(), which accepts a file path
    and returns the raw text content as a single string.
    """

    def __init__(self, file_path: str):
        """
        Args:
            file_path (str): Absolute or relative path to the survey file.
        """
        self.file_path = file_path

    @abstractmethod
    def load(self) -> str:
        """
        Read the file and return its content as a plain string.

        Returns:
            str: Raw text content of the survey file.

        Raises:
            FileNotFoundError: If the file does not exist at file_path.
            ValueError: If the file is empty or unreadable.
        """
        pass

    def _validate_path(self) -> None:
        """
        Shared utility: confirm the file exists before attempting to read.
        Subclasses can call this at the start of their load() method.

        Raises:
            FileNotFoundError: If self.file_path does not point to a real file.
        """
        import os
        if not os.path.exists(self.file_path):
            raise FileNotFoundError(
                f"Survey file not found: '{self.file_path}'\n"
                f"Check that the file exists in data/raw_surveys/"
            )
        if not os.path.isfile(self.file_path):
            raise ValueError(
                f"Path exists but is not a file: '{self.file_path}'"
            )
        