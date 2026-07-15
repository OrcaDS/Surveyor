# Surveyor AI

Surveyor AI is an interpretable survey quality assessment engine that evaluates questionnaires against established principles from survey methodology and psychometrics. Rather than generating survey questions, Surveyor AI analyzes an existing survey instrument and produces a structured diagnostic report highlighting potential threats to measurement validity, respondent burden, and questionnaire design quality.

The project is built around deterministic, evidence-based rules derived from the survey research literature. Each finding is accompanied by structured diagnostic signals, confidence estimates, severity scores, and supporting evidence to promote transparency and auditability.

---

## Features

* Rule-based survey auditing grounded in survey methodology literature
* Instrument-level and item-level diagnostic analysis
* Structured diagnostic signals with confidence estimates
* Composite validity scoring
* Human-readable audit reports
* JSON output for downstream applications
* Extensible rule architecture for new psychometric principles
* FastAPI-ready pipeline architecture

---

## Current Principles

Surveyor AI currently evaluates questionnaires using multiple principles derived from the works of:

* Don A. Dillman
* Floyd J. Fowler Jr.
* Tourangeau, Rips & Rasinski
* Krosnick
* Schwarz & Sudman

Examples of implemented checks include:

* CASM response process diagnostics
* Double-barreled questions
* Undefined or ambiguous terminology
* Recall period calibration
* Social desirability bias
* Acquiescence bias
* Satisficing risk
* Scale anchor calibration
* Context and carry-over effects
* Middle category and Don't Know options
* Scale direction consistency
* Negative wording
* Leading and loaded wording
* Survey length and response fatigue
* Funnel principle (general before specific)

---

## Project Architecture

```
Survey
        │
        ▼
Raw Text Loader
        │
        ▼
Survey Parser
        │
        ▼
Principle Engine
(P001 – P024)
        │
        ▼
Diagnostic Signals
        │
        ▼
Scoring Engine
        │
        ▼
Report Generator
```

The architecture intentionally separates parsing, rule evaluation, scoring, and reporting so that each component remains modular and independently testable.

---

## Diagnostic Philosophy

Surveyor AI does **not** attempt to determine whether a survey is "correct."

Instead, it identifies observable indicators associated with known survey design risks.

Each rule produces:

* Severity
* Evidence
* Structured diagnostic signals
* Confidence estimate
* Supporting metadata

The engine reports **risk indicators**, not confirmed measurement errors.

All findings should be reviewed by domain experts before modifying an instrument.

---

## Repository Structure

```
app/
├── api/
├── parser/
├── principles/
├── scoring/
├── reporting/
├── diagnostics/
├── utils/
└── semantic/          # Planned

tests/
docs/
data/
```

---

## Example Output

```
Item 11
Composite Risk: 0.43

Triggered Rules:
- P003 Undefined Terms
- P005 Social Desirability Bias
- P016 Leading / Loaded Wording

Evidence:
"I have the authority to..."

Signals:
- Undefined role terminology
- Competence presupposition
- Leading wording
```

---

## Running the Project

Clone the repository:

```bash
git clone https://github.com/yourusername/surveyor-ai.git
cd surveyor-ai
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it:

Windows

```bash
venv\Scripts\activate
```

Linux / macOS

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Run the test suite:

```bash
pytest
```

---

## Roadmap

### Completed

* Deterministic survey parser
* Rule engine (P001–P024)
* Structured diagnostic signal framework
* Composite scoring engine
* Report generation

### In Progress

* FastAPI service
* JSON API
* Frontend integration

### Planned

* Semantic similarity layer
* Embedding-based construct detection
* Cross-rule interaction modeling
* Confidence calibration
* Hybrid symbolic + semantic inference engine

---

## Design Goals

Surveyor AI prioritizes:

* Interpretability
* Transparency
* Auditability
* Modular architecture
* Research-grounded methodology

Every diagnostic produced by the engine should be traceable back to an explicit survey design principle rather than opaque statistical inference.

---

## Disclaimer

Surveyor AI is intended as a decision-support system for researchers, survey designers, and practitioners. The engine identifies potential questionnaire quality issues based on established survey methodology but does not replace expert judgment or formal psychometric validation procedures.
