from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


CONFIDENCE_HEADERS = [
    "rank",
    "candidate_id",
    "candidate_name",
    "candidate_type",
    "pattern_score",
    "pattern_strength_band",
    "pattern_evidence",
    "data_quality_score",
    "data_quality_band",
    "data_quality_notes",
    "orbit_context_score",
    "orbit_context_band",
    "orbit_context_notes",
    "sentry_evidence_score",
    "sentry_evidence_band",
    "sentry_evidence_notes",
    "evidence_completeness_index",
    "evidence_completeness_band",
    "uncertainty_flags",
    "interpretation",
]


def _read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return default


def _band(score: float) -> str:
    if score >= 85:
        return "very_high"
    if score >= 70:
        return "high"
    if score >= 50:
        return "moderate"
    if score >= 30:
        return "low"
    return "very_low"


def _pattern_score(row: Dict[str, str]) -> float:
    return max(0.0, min(100.0, _safe_float(row.get("score"), 0.0)))


def _data_quality(raw_dir: Path, source_report: str, provenance: Dict[str, Any]) -> tuple[float, str, List[str]]:
    score = 100.0
    notes: List[str] = []

    source = source_report.strip()
    if not source:
        score -= 25
        notes.append("candidate source report not identified")

    stale_names = {
        str(item.get("path", ""))
        for item in provenance.get("raw_sources", [])
        if item.get("stale") is True
    }
    if stale_names:
        score -= min(35.0, 10.0 * len(stale_names))
        notes.append(f"{len(stale_names)} raw source file(s) exceed freshness threshold")

    raw_files = [p for p in raw_dir.glob("*.json") if p.is_file()] if raw_dir.exists() else []
    if not raw_files:
        score -= 35
        notes.append("no raw JSON source files found")
    else:
        notes.append(f"{len(raw_files)} raw JSON source file(s) available")

    score = max(0.0, min(100.0, score))
    if not notes:
        notes.append("no obvious source-quality limitation detected")
    return score, _band(score), notes


def _orbit_context(row: Dict[str, str]) -> tuple[float, str, List[str]]:
    score = 0.0
    notes: List[str] = []

    status = (row.get("orbit_context_status") or "").strip().lower()
    if status in {"ok", "matched", "success", "available"}:
        score += 40
        notes.append("orbit-context lookup available")
    elif status:
        notes.append(f"orbit-context status: {status}")
    else:
        notes.append("orbit-context status unavailable")

    if (row.get("orbit_class_code") or row.get("orbit_class_name") or "").strip():
        score += 15
        notes.append("orbit class available")
    if (row.get("moid_au") or "").strip():
        score += 20
        notes.append("MOID available")
    if (row.get("estimated_diameter_km") or "").strip():
        score += 10
        notes.append("diameter context available")
    if str(row.get("is_neo", "")).strip() != "":
        score += 7.5
    if str(row.get("is_pha", "")).strip() != "":
        score += 7.5

    score = max(0.0, min(100.0, score))
    return score, _band(score), notes


def _sentry_context(row: Dict[str, str]) -> tuple[float, str, List[str]]:
    status = (row.get("sentry_match_status") or "").strip().lower()
    probability = (row.get("sentry_impact_probability") or "").strip()
    notes: List[str] = []

    if not status:
        return 15.0, _band(15.0), ["Sentry cross-check status unavailable"]

    if status in {"match", "matched", "yes", "listed", "found"}:
        score = 100.0
        notes.append("candidate matched a Sentry record")
        if probability:
            notes.append("Sentry impact-probability field available")
        return score, _band(score), notes

    if status in {"no_match", "not_found", "none", "no", "not listed"}:
        score = 80.0
        notes.append("candidate was cross-checked and no Sentry match was found")
        return score, _band(score), notes

    score = 45.0
    notes.append(f"Sentry cross-check status: {status}")
    return score, _band(score), notes


def _load_provenance(path: Path) -> Dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        pass
    return {}


def build_confidence_audit(project_root: Path) -> Path:
    reports = project_root / "reports"
    evidence_dir = reports / "01_EVIDENCE_REVIEW"
    orbit_dir = reports / "03_ORBIT_CONTEXT"
    technical_dir = reports / "99_TECHNICAL_LOGS"
    start_dir = reports / "00_START_HERE"

    candidates = _read_csv(evidence_dir / "watchlist_explained.csv")
    orbit_rows = _read_csv(orbit_dir / "candidate_orbit_review.csv")
    orbit_by_id = {row.get("candidate_id", ""): row for row in orbit_rows}
    provenance = _load_provenance(technical_dir / "run_provenance.json")

    rows: List[Dict[str, Any]] = []
    for candidate in candidates:
        candidate_id = candidate.get("candidate_id", "")
        orbit = orbit_by_id.get(candidate_id, {})
        pattern = _pattern_score(candidate)
        data_score, data_band, data_notes = _data_quality(
            project_root / "data" / "raw",
            candidate.get("source_report", ""),
            provenance,
        )
        orbit_score, orbit_band, orbit_notes = _orbit_context(orbit)
        sentry_score, sentry_band, sentry_notes = _sentry_context(orbit)

        completeness = round(
            (0.35 * pattern) +
            (0.25 * data_score) +
            (0.25 * orbit_score) +
            (0.15 * sentry_score),
            2,
        )

        flags: List[str] = []
        if data_score < 70:
            flags.append("source_quality_limit")
        if orbit_score < 50:
            flags.append("orbit_context_incomplete")
        if not (orbit.get("sentry_match_status") or "").strip():
            flags.append("sentry_status_unavailable")
        if pattern < 50:
            flags.append("weak_pattern_score")

        rows.append({
            "rank": candidate.get("rank", ""),
            "candidate_id": candidate_id,
            "candidate_name": candidate.get("candidate_name", ""),
            "candidate_type": candidate.get("candidate_type", ""),
            "pattern_score": round(pattern, 2),
            "pattern_strength_band": _band(pattern),
            "pattern_evidence": candidate.get("supporting_evidence", "") or candidate.get("reason", ""),
            "data_quality_score": round(data_score, 2),
            "data_quality_band": data_band,
            "data_quality_notes": "; ".join(data_notes),
            "orbit_context_score": round(orbit_score, 2),
            "orbit_context_band": orbit_band,
            "orbit_context_notes": "; ".join(orbit_notes),
            "sentry_evidence_score": round(sentry_score, 2),
            "sentry_evidence_band": sentry_band,
            "sentry_evidence_notes": "; ".join(sentry_notes),
            "evidence_completeness_index": completeness,
            "evidence_completeness_band": _band(completeness),
            "uncertainty_flags": "; ".join(flags) if flags else "none_obvious",
            "interpretation": (
                "Evidence-completeness index only. It summarizes how well this candidate is supported and contextualized "
                "inside IuPetra; it is not an impact probability, hazard score, or official risk metric."
            ),
        })

    evidence_dir.mkdir(parents=True, exist_ok=True)
    output = evidence_dir / "candidate_confidence_audit.csv"
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CONFIDENCE_HEADERS)
        writer.writeheader()
        writer.writerows(rows)

    start_dir.mkdir(parents=True, exist_ok=True)
    guide = start_dir / "SCIENTIFIC_CONFIDENCE_README.txt"
    guide.write_text(
        "IuPetra Scientific Confidence Layer\n"
        "=================================\n\n"
        f"Generated: {datetime.now(timezone.utc).isoformat()}\n"
        f"Candidates audited: {len(rows)}\n\n"
        "The candidate_confidence_audit.csv report separates four different concepts:\n"
        "1. Pattern strength - the existing IuPetra candidate score.\n"
        "2. Data quality - source availability/freshness and report traceability.\n"
        "3. Orbit context - whether orbital classification, MOID, size, NEO/PHA context were available.\n"
        "4. Sentry evidence - whether a Sentry cross-check was available and what it reported.\n\n"
        "The evidence-completeness index is NOT an impact probability, hazard score, or official NASA/JPL metric.\n"
        "It only indicates how complete the evidence packet is for human review.\n\n"
        "Audit report:\n"
        "  reports/01_EVIDENCE_REVIEW/candidate_confidence_audit.csv\n",
        encoding="utf-8",
    )
    return output
