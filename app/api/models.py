"""
app/api/models.py

Pydantic request and response models for the Surveyor AI API.

DESIGN NOTE:
    Request: multipart file upload only.
    Response: wraps the full ReportBuilder JSON output with
    an added 'success' flag and optional error message.
    We do not redefine the full report schema here — the report
    dict is passed through as-is under 'report'.
"""

from pydantic import BaseModel
from typing import Optional


class AuditResponse(BaseModel):
    """
    Response envelope for POST /audit.

    Attributes:
        success (bool):         True if audit completed without error.
        error (str | None):     Error message if success is False.
        report (dict | None):   Full diagnostic report if success is True.
    """
    success: bool
    error: Optional[str] = None
    report: Optional[dict] = None