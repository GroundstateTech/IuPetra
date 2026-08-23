# Changelog

All notable IuPetra changes should be recorded here.

## [Unreleased]

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
