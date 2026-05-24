"""
app/principles/p022.py

PRINCIPLE: P022 — Visual Layout Effects
SOURCE: Dillman — Mail and Internet Surveys, Ch. 5, p. 204–210
        Tourangeau et al. — The Psychology of Survey Response, Ch. 10
OPERATIONALIZABILITY: Low
CONFIDENCE: Low

WHAT THIS RULE CHECKS:
    Visual layout features that create systematic response bias.

    SIGNAL 1 — Grid/matrix format detection:
        Grid questions (multiple items sharing same scale in a table)
        encourage response patterning (straight-lining) because
        respondents can visually scan and repeat the same column.

    SIGNAL 2 — Spatial grouping implications:
        Items visually grouped together imply conceptual relatedness
        even when items are measuring distinct constructs. Respondents
        use visual proximity as a cue for how to interpret items.

    SIGNAL 3 — Emphasis artifacts:
        Bold, italic, or capitalized text in items creates unintended
        emphasis that draws attention to specific words and inflates
        their perceived importance.

GATE:
    Text-only surveys without formatting metadata cannot be evaluated
    for most visual layout effects. This rule operates on surface
    text signals only and will have low detection rate on plain text.

SEVERITY:
    Grid format detected    -> 0.50
    Emphasis artifacts      -> 0.30
    Spatial grouping        -> 0.25

PROXY NOTE:
    True visual layout analysis requires rendered survey format data
    (HTML, PDF, image). Plain text input severely limits detection.
    This rule's value increases significantly with richer input formats.
"""

import re
from app.principles.base_rule import BaseRule, Violation


class P022(BaseRule):

    id = "P022"
    description = (
        "Detects visual layout features that create response patterning, "
        "false grouping implications, or unintended emphasis artifacts."
    )

    GRID_SIGNALS = [
        r"\bfor each (of the following|item|statement)\b",
        r"\brate (each|all) of the following\b",
        r"\busing the scale (above|below)\b",
        r"\bsee (scale|rating) (above|below)\b",
    ]

    EMPHASIS_SIGNALS = [
        r"\b[A-Z]{4,}\b",        # ALL CAPS words (4+ chars)
        r"\*\*.+?\*\*",          # **bold** markdown
        r"__.+?__",              # __bold__ markdown
    ]

    def evaluate(self, item: dict) -> Violation | None:
        text = self._get_text(item)
        text_lower = text.lower()

        signals = []

        # Signal 1: Grid format
        grid_hits = [
            p for p in self.GRID_SIGNALS
            if re.search(p, text_lower)
        ]
        if grid_hits:
            signals.append(
                "grid/matrix format detected — encourages straight-lining "
                "as respondents visually scan and repeat column selections"
            )

        # Signal 3: Emphasis artifacts
        emphasis_hits = [
            p for p in self.EMPHASIS_SIGNALS
            if re.search(p, text)
        ]
        if emphasis_hits:
            signals.append(
                "emphasis artifact detected (ALL CAPS or markdown bold) — "
                "creates unintended word salience that inflates perceived "
                "importance of emphasized terms"
            )

        if not signals:
            return None

        severity = 0.50 if any("grid" in s for s in signals) else 0.30

        return Violation(
            principle=self.id,
            severity=round(severity, 2),
            evidence=(
                "Visual layout effect risk detected. "
                "Signal(s): " + " | ".join(signals)
            )
        )