# IuPetra

**IuPetra v1.3.1.1** is a local asteroid, close-approach, fireball, and orbital-context investigation tool built around public NASA/JPL data.

It pulls public datasets, normalizes them into local CSV files, looks for repeat activity and time-window patterns, enriches candidate objects with orbital context, cross-checks Sentry data, and generates a browsable local report workspace with an HTML dashboard.

> IuPetra is an anomaly-review and research-assistance tool. Its watchlist/activity scores are internal pattern-finding heuristics, **not official impact-risk metrics or predictions**.

## What it analyzes

IuPetra currently works with:

- CNEOS/JPL fireball data
- JPL close-approach data
- CNEOS Sentry risk-table data
- JPL Small-Body Database (SBDB) orbital context

The analysis pipeline produces, among other outputs:

- yearly and monthly fireball summaries
- largest-energy fireball lists
- closest and fastest close approaches
- yearly activity index
- repeating close-approach objects
- high-energy fireball windows
- close-approach clustering windows
- ranked watchlist candidates
- plain-English evidence review
- research questions for flagged candidates
- object orbital context
- Sentry cross-checks
- candidate orbit review
- top-candidate packet
- HTML dashboard and report viewers

## Quick Start — Windows

IuPetra uses the Python standard library and currently has no third-party package requirements.

1. Install Python 3.10 or newer.
2. Clone/download the repository.
3. Double-click:

```text
Launch_IuPetra.bat
```

The launcher runs the data pull and report pipeline, then opens:

```text
reports/00_START_HERE/IuPetra_START_HERE.html
```

## Command Line

Run the application directly:

```powershell
python iupetra.py
```

Before running, verify the local environment and settings:

```powershell
python scripts/doctor.py
```

To also test connectivity to the NASA/JPL endpoints:

```powershell
python scripts/doctor.py --network
```

## Workspace

```text
data/
  raw/                 original JSON API pulls
  clean/               normalized CSV datasets

reports/
  00_START_HERE/       dashboard, report index, candidate packet
  01_EVIDENCE_REVIEW/  explained watchlist + research questions
  02_PATTERN_FINDER/   temporal/repeat/anomaly reports
  03_ORBIT_CONTEXT/    SBDB and Sentry context
  04_SUMMARIES/        yearly/monthly/top-object summaries
  99_TECHNICAL_LOGS/   run manifest and error log
  HTML_VIEWERS/        generated browser viewers
```

Runtime datasets and generated reports are ignored by Git by default so local investigations do not accidentally become repository content.

## Configuration

No-code controls live in:

```text
settings.json
```

Current controls include:

- fireball retrieval limit
- close-approach date range
- maximum close-approach distance
- close-approach retrieval limit
- high-energy fireball threshold
- clustering/window lengths
- repeat-object minimum count
- watchlist score threshold
- top candidate packet size
- SBDB enrichment limit

The committed defaults currently examine close approaches from **2000-01-01 through 2035-01-01** within **0.05 AU**. These are analysis settings, not a statement about an object's risk. 

## Failure behavior

Network pulls are run as individual steps. If an API request fails, IuPetra logs the error and continues building whatever reports it can from available local data rather than terminating the entire run.

Technical errors are written to:

```text
reports/99_TECHNICAL_LOGS/error_log.txt
```

## Development

Run the local verification suite without calling external APIs:

```powershell
python -m py_compile iupetra.py scripts/doctor.py tests/test_core.py
python scripts/doctor.py
python -m unittest discover -s tests -v
```

GitHub Actions runs the same basic checks on Windows and Linux with supported Python versions.

## Scientific interpretation

IuPetra intentionally separates **pattern detection** from **risk determination**.

A high activity/watchlist score means the software found something worth reviewing under its configured heuristic rules. It does **not** establish:

- an impending impact
- a causal relationship between unrelated events
- a periodic asteroid threat cycle
- a validated physical mechanism
- a replacement for NASA/JPL orbital solutions or official risk assessment

The proper use of a flagged candidate is to inspect the underlying source records, orbital context, uncertainty, Sentry status, and independent astronomical evidence.

## Data authority

For official small-body and impact-risk information, defer to NASA/JPL/CNEOS source systems. IuPetra is designed to make public data easier to explore and compare locally, not to supersede those systems.

## Status

IuPetra is active alpha/research software. Output formats, scoring, and investigation workflows may evolve as the evidence-review system improves.
