# Security and Research Integrity

IuPetra is open-source research-assistance software under GPL-3.0-or-later. It consumes public astronomical data and produces local analysis/report artifacts.

## Reporting security issues

Please avoid publishing exploit details, credentials, private network information, or sensitive local files in a public issue before maintainers have had a reasonable chance to assess the problem. Include the affected commit/version, environment, reproduction steps, impact, and a proposed mitigation when available.

## Secrets and local data

Do not commit API credentials, tokens, `.env` files, private keys, machine-specific secrets, downloaded runtime datasets, or generated investigation reports unless a dataset snapshot is intentionally reviewed and approved for redistribution. Runtime `data/raw`, `data/clean`, and `reports` content is ignored by default.

## Data authority and interpretation

IuPetra must preserve a clear boundary between exploratory heuristics and authoritative NASA/JPL/CNEOS risk information. A security or feature change must not silently alter provenance, source labeling, confidence language, or the distinction between internal pattern scores and official impact-risk metrics.

## Network behavior

External data retrieval should use documented public endpoints, bounded retries/timeouts, and explicit provenance. Avoid introducing hidden telemetry, tracking, or unreviewed third-party network calls.

## Supported security posture

Security and data-integrity fixes are prioritized on the current `main` branch. IuPetra remains active research software; users should independently verify consequential scientific conclusions against authoritative source systems.
