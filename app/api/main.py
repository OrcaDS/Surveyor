"""
app/api/main.py

Surveyor AI — FastAPI application.

ENDPOINTS:
    GET  /health        Health check.
    POST /audit         Submit a survey file for audit.

USAGE:
    uvicorn app.api.main:app --reload

DESIGN NOTES:
    - Accepts plain text (.txt) file uploads via multipart form.
    - Returns the full diagnostic JSON report.
    - All pipeline errors are caught and returned as structured
      error responses — never as unhandled 500s.
    - File size is capped at 1MB. Surveys above this size are
      likely malformed or not survey files.
"""

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.api.models import AuditResponse
from app.api.pipeline import run_pipeline

app = FastAPI(
    title="Surveyor AI",
    description=(
        "Survey validity audit engine. Detects methodological problems "
        "in survey instruments using a 25-principle rule engine grounded "
        "in survey methodology literature."
    ),
    version="0.2.0",
)

# CORS — permissive for development. Tighten for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# File size cap: 1MB
MAX_FILE_SIZE = 1 * 1024 * 1024


@app.get("/health")
def health_check():
    """Confirm the API is running."""
    return {"status": "ok", "engine": "Surveyor AI", "version": "0.2.0"}


@app.post("/audit", response_model=AuditResponse)
async def audit_survey(file: UploadFile = File(...)):
    """
    Submit a survey file for audit.

    Accepts a plain text (.txt) file upload.
    Returns the full diagnostic report as JSON.

    Raises:
        400: If the file is not a .txt file, is empty, or exceeds 1MB.
        422: If the file content cannot be parsed as a survey.
        500: If an unexpected pipeline error occurs.
    """
    # --- Validate file type ---
    if not file.filename.endswith(".txt"):
        raise HTTPException(
            status_code=400,
            detail="Only .txt files are supported at this time."
        )

    # --- Read and size-check ---
    content_bytes = await file.read()

    if len(content_bytes) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=(
                f"File exceeds maximum size of 1MB. "
                f"Received: {len(content_bytes) / 1024:.1f}KB."
            )
        )

    if not content_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    # --- Decode ---
    try:
        raw_text = content_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail=(
                "File encoding error. "
                "Ensure the file is saved as UTF-8 plain text."
            )
        )

    # --- Run pipeline ---
    try:
        from app.reporting.report_builder import ReportBuilder
        diagnostic = run_pipeline(raw_text)
        builder = ReportBuilder(diagnostic)
        report = builder.build_json_report()
        return AuditResponse(success=True, report=report)

    except ValueError as e:
        # Parser-level failures — bad input, not server error
        raise HTTPException(status_code=422, detail=str(e))

    except Exception as e:
        # Unexpected failures — log and return structured error
        raise HTTPException(
            status_code=500,
            detail=f"Audit pipeline error: {type(e).__name__}: {str(e)}"
        )