IuPetra v1.3 - Stability + Dashboard
========================================

Start here if you are trying to understand the run.

Recommended reading order:

Before changing code:
Edit settings.json in the main IuPetra folder to adjust limits, thresholds, date range, and scoring sensitivity.

1. IuPetra_START_HERE.html
   Visual dashboard and navigation hub.

2. top_candidate_packet.txt
   Human-readable summary of the strongest candidates and why they were flagged.

3. REPORT_INDEX.csv
   Map of every important report and where it lives.

../01_EVIDENCE_REVIEW/watchlist_explained.csv
   Spreadsheet version of candidate explanations.

../03_ORBIT_CONTEXT/candidate_orbit_review.csv
   Shows whether watchlist objects have orbit context, NEO/PHA flags, MOID, and Sentry status.

../01_EVIDENCE_REVIEW/research_questions.csv
   Next research questions for investigating candidates without jumping to conclusions.

Folder guide:

settings.json
  No-code controls for thresholds, limits, dates, and watchlist sensitivity.

data/raw
  Original API JSON payloads and SBDB object context JSON lookups.

data/clean
  Clean normalized CSV tables.

reports/00_START_HERE
  Most important human-facing outputs.

reports/01_EVIDENCE_REVIEW
  Explanation layer: why a candidate was flagged, limitations, and next checks.

reports/02_PATTERN_FINDER
  Pattern reports: clusters, windows, repeated objects, and watchlist generation.

reports/03_ORBIT_CONTEXT
  Object enrichment reports from JPL SBDB and Sentry crosscheck.

reports/04_SUMMARIES
  General yearly/monthly summaries and top-N lists.

reports/99_TECHNICAL_LOGS
  Run manifest and technical configuration details.

Important caution:
IuPetra is an investigation and anomaly-review tool. It does not issue official impact-risk predictions.
Official hazard assessment should always be checked against NASA/JPL CNEOS Sentry and other official monitoring systems.
