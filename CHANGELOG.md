# Changelog

All notable IuPetra changes should be recorded here.

## [Unreleased]

### Scientific confidence layer

- Added `candidate_confidence_audit.csv` as a separate post-run evidence-quality report.
- Separated candidate review into pattern strength, source/data quality, orbital context, and Sentry evidence.
- Added an evidence-completeness index that measures how complete a review packet is; it is explicitly not a hazard score or impact probability.
- Added uncertainty flags for weak pattern strength, stale/missing source data, incomplete orbital context, and unavailable Sentry status.
- Treated `not_applicable` orbital/Sentry context as a completed applicability determination rather than missing evidence.
- Matched the confidence layer to IuPetra's existing `matched_sentry` and `not_matched_in_fetched_sentry` status vocabulary.
- Added `SCIENTIFIC_CONFIDENCE_README.txt` to the start-here workspace.
- Added regression tests for complete and incomplete candidate evidence packets.
- Kept confidence generation non-fatal so the established analysis/report pipeline remains the authority for run success.

### Reliability engine pass

- Added a resilient NASA/JPL JSON fetch wrapper with bounded exponential backoff for transient failures.
- Added a compatibility runner (`run_iupetra.py`) that injects the reliable fetch primitive without modifying the existing scientific/report pipeline.
- Updated the Windows launcher to use the reliability runner and preserve the application's real exit code.
- Added `run_provenance.json` with SHA-256 checksums, file sizes, timestamps, run exit code, fetch policy, and raw-source freshness metadata.
- Added explicit stale-source diagnostics for raw local API files older than 24 hours; the label is informational and is not a scientific-validity judgment.
- Added regression tests for retry behavior, permanent HTTP failures, provenance generation, and the compatibility runner.
- Expanded CI syntax coverage to include the reliability layer and runner.

### GitHub foundation

- Added a repository `.gitignore` for generated data, reports, caches, and local environments.
- Added `scripts/doctor.py` for offline environment/settings validation and optional NASA/JPL connectivity checks.
- Added offline unit tests for the settings contract and core utility behavior.
- Added cross-platform GitHub Actions verification on Windows and Linux.
- Expanded README documentation, configuration notes, workspace layout, and scientific interpretation guidance.
- Clarified that activity/watchlist scores are pattern-finding heuristics and are not official impact-risk predictions.

## [1.3.1.1]

- Stability + dashboard build.
- Organized report workspace.
- Candidate watchlist and evidence-review reports.
- SBDB orbital-context enrichment.
- Sentry cross-check and candidate orbit review.
- Local HTML dashboard/viewers and technical run manifest.
