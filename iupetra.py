#!/usr/bin/env python3
"""
IuPetra v1.3.1.1 - Stability + Dashboard

Run:
    python iupetra.py

Creates:
    data/raw/
    data/clean/
    reports/

New in v1.3:
- object_orbit_context.csv
- sentry_crosscheck.csv
- candidate_orbit_review.csv
- Orbit/risk context for watchlist candidates
"""

from __future__ import annotations

import csv
import json
import re
import html
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


# ============================================================
# CONFIG
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parent
SETTINGS_PATH = PROJECT_ROOT / "settings.json"

DATA_RAW_DIR = PROJECT_ROOT / "data" / "raw"
DATA_CLEAN_DIR = PROJECT_ROOT / "data" / "clean"
REPORTS_DIR = PROJECT_ROOT / "reports"

# Organized workspace folders. v1.3 writes reports directly into these folders.
# Root reports/ is only a container, not a dumping ground.
IMPORTANT_REPORTS_DIR = REPORTS_DIR / "00_START_HERE"
EVIDENCE_REPORTS_DIR = REPORTS_DIR / "01_EVIDENCE_REVIEW"
PATTERN_REPORTS_DIR = REPORTS_DIR / "02_PATTERN_FINDER"
ORBIT_REPORTS_DIR = REPORTS_DIR / "03_ORBIT_CONTEXT"
SUMMARY_REPORTS_DIR = REPORTS_DIR / "04_SUMMARIES"
TECHNICAL_REPORTS_DIR = REPORTS_DIR / "99_TECHNICAL_LOGS"

# Standard report output paths.
PATH_TOP_CANDIDATE_PACKET = IMPORTANT_REPORTS_DIR / "top_candidate_packet.txt"
PATH_REPORT_INDEX = IMPORTANT_REPORTS_DIR / "REPORT_INDEX.csv"
PATH_START_HERE_README = IMPORTANT_REPORTS_DIR / "README_START_HERE.txt"

PATH_WATCHLIST_EXPLAINED = EVIDENCE_REPORTS_DIR / "watchlist_explained.csv"
PATH_RESEARCH_QUESTIONS = EVIDENCE_REPORTS_DIR / "research_questions.csv"

PATH_WATCHLIST_CANDIDATES = PATTERN_REPORTS_DIR / "watchlist_candidates.csv"
PATH_FIREBALL_MONTH_CLUSTERS = PATTERN_REPORTS_DIR / "fireball_month_clusters.csv"
PATH_REPEATING_CLOSE_APPROACH_OBJECTS = PATTERN_REPORTS_DIR / "repeating_close_approach_objects.csv"
PATH_HIGH_ENERGY_FIREBALL_WINDOWS = PATTERN_REPORTS_DIR / "high_energy_fireball_windows.csv"
PATH_CLOSE_APPROACH_WINDOWS = PATTERN_REPORTS_DIR / "close_approach_windows.csv"

PATH_OBJECT_ORBIT_CONTEXT = ORBIT_REPORTS_DIR / "object_orbit_context.csv"
PATH_SENTRY_CROSSCHECK = ORBIT_REPORTS_DIR / "sentry_crosscheck.csv"
PATH_CANDIDATE_ORBIT_REVIEW = ORBIT_REPORTS_DIR / "candidate_orbit_review.csv"

PATH_YEARLY_ACTIVITY_INDEX = SUMMARY_REPORTS_DIR / "yearly_activity_index.csv"
PATH_FIREBALL_YEARLY_SUMMARY = SUMMARY_REPORTS_DIR / "fireball_yearly_summary.csv"
PATH_FIREBALL_MONTHLY_SUMMARY = SUMMARY_REPORTS_DIR / "fireball_monthly_summary.csv"
PATH_LARGEST_FIREBALLS = SUMMARY_REPORTS_DIR / "largest_fireballs.csv"
PATH_CLOSE_APPROACH_YEARLY_SUMMARY = SUMMARY_REPORTS_DIR / "close_approach_yearly_summary.csv"
PATH_CLOSEST_APPROACHES = SUMMARY_REPORTS_DIR / "closest_approaches.csv"
PATH_FASTEST_CLOSE_APPROACHES = SUMMARY_REPORTS_DIR / "fastest_close_approaches.csv"
PATH_SENTRY_SUMMARY = SUMMARY_REPORTS_DIR / "sentry_summary.csv"

PATH_RUN_MANIFEST = TECHNICAL_REPORTS_DIR / "run_manifest.csv"
PATH_DASHBOARD_HTML = IMPORTANT_REPORTS_DIR / "IuPetra_START_HERE.html"
HTML_VIEWERS_DIR = REPORTS_DIR / "HTML_VIEWERS"
PATH_ERROR_LOG = TECHNICAL_REPORTS_DIR / "error_log.txt"


FIREBALL_API_URL = "https://ssd-api.jpl.nasa.gov/fireball.api"
CLOSE_APPROACH_API_URL = "https://ssd-api.jpl.nasa.gov/cad.api"
SENTRY_API_URL = "https://ssd-api.jpl.nasa.gov/sentry.api"
SBDB_API_URL = "https://ssd-api.jpl.nasa.gov/sbdb.api"

DEFAULT_SETTINGS = {
    "fireball_limit": 500,
    "close_approach_date_min": "2000-01-01",
    "close_approach_date_max": "2035-01-01",
    "close_approach_distance_max_au": "0.05",
    "close_approach_limit": 1000,
    "top_report_limit": 50,
    "high_energy_fireball_kt_threshold": 0.1,
    "high_energy_window_days": 14,
    "close_approach_window_days": 14,
    "close_approach_cluster_distance_au": 0.02,
    "repeat_object_min_count": 2,
    "watchlist_min_score": 40.0,
    "top_candidate_packet_limit": 10,
    "sbdb_enrichment_limit": 25,
}


def create_default_settings_file() -> None:
    if SETTINGS_PATH.exists():
        return

    SETTINGS_PATH.write_text(
        json.dumps(DEFAULT_SETTINGS, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_settings() -> Dict[str, Any]:
    create_default_settings_file()

    try:
        loaded = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"settings.json is not valid JSON: {exc}") from exc

    if not isinstance(loaded, dict):
        raise ValueError("settings.json must contain one JSON object.")

    settings = dict(DEFAULT_SETTINGS)
    settings.update(loaded)

    return settings


SETTINGS = load_settings()

FIREBALL_LIMIT = int(SETTINGS["fireball_limit"])

CLOSE_APPROACH_DATE_MIN = str(SETTINGS["close_approach_date_min"])
CLOSE_APPROACH_DATE_MAX = str(SETTINGS["close_approach_date_max"])

# Keep the string version for the NASA/JPL API.
CLOSE_APPROACH_DISTANCE_MAX_AU = str(SETTINGS["close_approach_distance_max_au"])

# Use the float version for math.
CLOSE_APPROACH_DISTANCE_MAX_AU_FLOAT = float(CLOSE_APPROACH_DISTANCE_MAX_AU)

CLOSE_APPROACH_LIMIT = int(SETTINGS["close_approach_limit"])

TOP_REPORT_LIMIT = int(SETTINGS["top_report_limit"])

HIGH_ENERGY_FIREBALL_KT_THRESHOLD = float(SETTINGS["high_energy_fireball_kt_threshold"])
HIGH_ENERGY_WINDOW_DAYS = int(SETTINGS["high_energy_window_days"])

CLOSE_APPROACH_WINDOW_DAYS = int(SETTINGS["close_approach_window_days"])
CLOSE_APPROACH_CLUSTER_DISTANCE_AU = float(SETTINGS["close_approach_cluster_distance_au"])

REPEAT_OBJECT_MIN_COUNT = int(SETTINGS["repeat_object_min_count"])

WATCHLIST_MIN_SCORE = float(SETTINGS["watchlist_min_score"])

TOP_CANDIDATE_PACKET_LIMIT = int(SETTINGS["top_candidate_packet_limit"])
SBDB_ENRICHMENT_LIMIT = int(SETTINGS["sbdb_enrichment_limit"])

# ============================================================
# EXACT CLEAN CSV HEADERS
# ============================================================

FIREBALL_HEADERS = [
    "event_id",
    "date_utc",
    "year",
    "month",
    "day",
    "latitude_deg",
    "longitude_deg",
    "altitude_km",
    "radiated_energy_1e10_j",
    "estimated_impact_energy_kt",
    "velocity_x_km_s",
    "velocity_y_km_s",
    "velocity_z_km_s",
    "data_source",
]

CLOSE_APPROACH_HEADERS = [
    "object_designation",
    "object_fullname",
    "orbit_id",
    "close_approach_datetime_tdb",
    "year",
    "julian_date_tdb",
    "distance_au",
    "distance_min_au",
    "distance_max_au",
    "velocity_relative_km_s",
    "velocity_infinity_km_s",
    "time_uncertainty_3sigma",
    "absolute_magnitude_h",
    "diameter_km",
    "diameter_sigma_km",
    "approach_body",
    "data_source",
]

SENTRY_HEADERS = [
    "object_id",
    "object_designation",
    "object_fullname",
    "year_range",
    "potential_impact_count",
    "cumulative_impact_probability",
    "palermo_scale_cumulative",
    "palermo_scale_maximum",
    "torino_scale_maximum",
    "absolute_magnitude_h",
    "estimated_diameter_km",
    "velocity_infinity_km_s",
    "last_observation_date",
    "last_observation_jd",
    "data_source",
]


# ============================================================
# REPORT HEADERS
# ============================================================

FIREBALL_YEARLY_SUMMARY_HEADERS = [
    "year",
    "fireball_event_count",
    "total_estimated_impact_energy_kt",
    "average_estimated_impact_energy_kt",
    "max_estimated_impact_energy_kt",
]

FIREBALL_MONTHLY_SUMMARY_HEADERS = [
    "year",
    "month",
    "fireball_event_count",
    "total_estimated_impact_energy_kt",
    "average_estimated_impact_energy_kt",
    "max_estimated_impact_energy_kt",
]

LARGEST_FIREBALLS_HEADERS = [
    "rank",
    "event_id",
    "date_utc",
    "year",
    "month",
    "day",
    "latitude_deg",
    "longitude_deg",
    "altitude_km",
    "radiated_energy_1e10_j",
    "estimated_impact_energy_kt",
]

CLOSE_APPROACH_YEARLY_SUMMARY_HEADERS = [
    "year",
    "close_approach_count",
    "minimum_distance_au",
    "maximum_velocity_relative_km_s",
]

CLOSEST_APPROACHES_HEADERS = [
    "rank",
    "object_designation",
    "object_fullname",
    "close_approach_datetime_tdb",
    "year",
    "distance_au",
    "distance_min_au",
    "distance_max_au",
    "velocity_relative_km_s",
    "absolute_magnitude_h",
    "diameter_km",
]

FASTEST_APPROACHES_HEADERS = [
    "rank",
    "object_designation",
    "object_fullname",
    "close_approach_datetime_tdb",
    "year",
    "distance_au",
    "velocity_relative_km_s",
    "velocity_infinity_km_s",
    "absolute_magnitude_h",
    "diameter_km",
]

SENTRY_SUMMARY_HEADERS = [
    "metric",
    "value",
]

YEARLY_ACTIVITY_INDEX_HEADERS = [
    "year",
    "fireball_event_count",
    "fireball_total_energy_kt",
    "close_approach_count",
    "closest_approach_distance_au",
    "fastest_approach_velocity_km_s",
    "activity_score",
    "activity_score_note",
]

FIREBALL_MONTH_CLUSTERS_HEADERS = [
    "month",
    "total_fireball_event_count",
    "total_estimated_impact_energy_kt",
    "average_energy_per_event_kt",
    "max_single_event_energy_kt",
    "active_year_count",
    "cluster_score",
    "cluster_note",
]

REPEATING_CLOSE_APPROACH_OBJECTS_HEADERS = [
    "rank",
    "object_designation",
    "object_fullname",
    "approach_count",
    "first_close_approach_datetime_tdb",
    "last_close_approach_datetime_tdb",
    "minimum_distance_au",
    "maximum_velocity_relative_km_s",
    "absolute_magnitude_h",
    "diameter_km",
    "repeat_score",
]

HIGH_ENERGY_FIREBALL_WINDOWS_HEADERS = [
    "window_id",
    "window_start_date",
    "window_end_date",
    "event_count",
    "total_estimated_impact_energy_kt",
    "max_estimated_impact_energy_kt",
    "event_ids",
    "dates_utc",
    "window_note",
]

CLOSE_APPROACH_WINDOWS_HEADERS = [
    "window_id",
    "window_start_date",
    "window_end_date",
    "close_approach_count",
    "closest_distance_au",
    "fastest_velocity_relative_km_s",
    "object_designations",
    "close_approach_datetimes_tdb",
    "window_note",
]

WATCHLIST_CANDIDATES_HEADERS = [
    "rank",
    "candidate_type",
    "candidate_id",
    "candidate_name",
    "primary_date_or_window",
    "score",
    "reason",
    "source_report",
]

WATCHLIST_EXPLAINED_HEADERS = [
    "rank",
    "candidate_type",
    "candidate_id",
    "candidate_name",
    "primary_date_or_window",
    "score",
    "confidence_level",
    "plain_english_summary",
    "supporting_evidence",
    "limitations",
    "next_check",
    "source_report",
]

RESEARCH_QUESTIONS_HEADERS = [
    "priority",
    "candidate_id",
    "candidate_type",
    "research_question",
    "why_it_matters",
    "suggested_next_data_source",
]


OBJECT_ORBIT_CONTEXT_HEADERS = [
    "lookup_rank",
    "object_designation",
    "lookup_status",
    "object_fullname",
    "spkid",
    "small_body_kind",
    "orbit_class_code",
    "orbit_class_name",
    "is_neo",
    "is_pha",
    "absolute_magnitude_h",
    "estimated_diameter_km",
    "moid_au",
    "perihelion_distance_au",
    "aphelion_distance_au",
    "semi_major_axis_au",
    "eccentricity",
    "inclination_deg",
    "orbital_period_days",
    "last_observation_date",
    "source_api",
    "lookup_error",
]

SENTRY_CROSSCHECK_HEADERS = [
    "candidate_id",
    "candidate_name",
    "candidate_type",
    "object_designation",
    "sentry_match_status",
    "sentry_object_fullname",
    "year_range",
    "potential_impact_count",
    "cumulative_impact_probability",
    "palermo_scale_cumulative",
    "palermo_scale_maximum",
    "torino_scale_maximum",
    "estimated_diameter_km",
    "crosscheck_note",
]

CANDIDATE_ORBIT_REVIEW_HEADERS = [
    "rank",
    "candidate_type",
    "candidate_id",
    "candidate_name",
    "primary_date_or_window",
    "score",
    "orbit_context_status",
    "orbit_class_code",
    "orbit_class_name",
    "is_neo",
    "is_pha",
    "moid_au",
    "estimated_diameter_km",
    "sentry_match_status",
    "sentry_year_range",
    "sentry_impact_probability",
    "review_note",
]

RUN_MANIFEST_HEADERS = [
    "field",
    "value",
]


# ============================================================
# UTILS
# ============================================================

def ensure_dirs() -> None:
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)
    DATA_CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    for folder in [
        IMPORTANT_REPORTS_DIR,
        EVIDENCE_REPORTS_DIR,
        PATTERN_REPORTS_DIR,
        ORBIT_REPORTS_DIR,
        SUMMARY_REPORTS_DIR,
        TECHNICAL_REPORTS_DIR,
        HTML_VIEWERS_DIR,
    ]:
        folder.mkdir(parents=True, exist_ok=True)


def fetch_json(url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 60) -> Dict[str, Any]:
    full_url = url

    if params:
        full_url = f"{url}?{urllib.parse.urlencode(params)}"

    request = urllib.request.Request(
        full_url,
        headers={"User-Agent": "IuPetra-v1.3.1"},
    )

    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def save_json(payload: Dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, indent=2, sort_keys=True)


def write_csv(rows: Iterable[Dict[str, Any]], headers: List[str], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()

        for data_row in rows:
            writer.writerow({header: data_row.get(header, "") for header in headers})


def read_csv(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []

    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def html_escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def local_link(path: Path) -> str:
    """Return a browser-friendly relative link from reports/00_START_HERE."""
    if path == SETTINGS_PATH:
        return "../../settings.json"

    try:
        return path.relative_to(IMPORTANT_REPORTS_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def count_rows(path: Path) -> int:
    return len(read_csv(path))


def get_first_csv_row(path: Path) -> Dict[str, str]:
    rows = read_csv(path)
    return rows[0] if rows else {}


def format_count(value: int) -> str:
    return f"{value:,}"


def clean_report_value(value: Any, fallback: str = "not available") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def top_candidate_line() -> str:
    top = get_first_csv_row(PATH_WATCHLIST_EXPLAINED)
    if not top:
        return "No watchlist candidates were generated in this run."

    name = clean_report_value(top.get("candidate_name"), "Unnamed candidate")
    score = clean_report_value(top.get("score"), "unscored")
    confidence = clean_report_value(top.get("confidence_level"), "unrated")
    return f"Top lead: {name} · score {score} · {confidence}."


def orbit_review_line() -> str:
    top = get_first_csv_row(PATH_CANDIDATE_ORBIT_REVIEW)
    if not top:
        return "No orbit-review rows were generated in this run."

    name = clean_report_value(top.get("candidate_name"), "Unnamed object")
    orbit_class = clean_report_value(top.get("orbit_class_name"), "orbit class not returned")
    sentry = clean_report_value(top.get("sentry_match_status"), "Sentry status not returned")
    return f"First orbit review: {name} · {orbit_class} · {sentry}."


def settings_summary_line() -> str:
    return (
        f"Fireballs: {FIREBALL_LIMIT:,} max · "
        f"close approaches: {CLOSE_APPROACH_DATE_MIN} to {CLOSE_APPROACH_DATE_MAX}, "
        f"within {CLOSE_APPROACH_DISTANCE_MAX_AU} au · "
        f"watchlist threshold: {WATCHLIST_MIN_SCORE:g}."
    )


def append_error_log(context: str, exc: Exception) -> None:
    """Write a compact error log without killing folder organization."""
    try:
        TECHNICAL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        with PATH_ERROR_LOG.open("a", encoding="utf-8") as file:
            file.write(f"[{timestamp}] {context}: {exc}\n")
    except Exception:
        # Last-resort fallback: never let error logging create a second failure.
        pass


def fetch_step(label: str, func) -> int:
    """Run a fetch step with clearer error reporting."""
    print(label)
    try:
        count = func()
        print(f"  saved {count} rows")
        return count
    except Exception as exc:
        append_error_log(label, exc)
        print(f"  ERROR: {exc}")
        print("  Continuing with available local files where possible.")
        return 0


def build_step(label: str, func) -> int:
    """Run a report step with clearer error reporting."""
    try:
        count = func()
        return count
    except Exception as exc:
        append_error_log(label, exc)
        print(f"  ERROR in {label}: {exc}")
        return 0


def html_escape(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def relative_link(path: Path) -> str:
    try:
        return path.relative_to(REPORTS_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def to_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def safe_round(value: Optional[float], places: int = 6) -> Any:
    if value is None:
        return ""

    return round(value, places)


def signed_coordinate(value: Any, direction: Any) -> str:
    number = to_float(value)

    if number is None:
        return ""

    direction_text = str(direction or "").upper().strip()

    if direction_text in {"S", "W"}:
        number = -abs(number)
    elif direction_text in {"N", "E"}:
        number = abs(number)

    return str(number)


def parse_year_from_date_text(value: Any) -> str:
    if not value:
        return ""

    match = re.match(r"^(\d{4})", str(value).strip())
    return match.group(1) if match else ""


def parse_month_day_from_fireball_date(value: Any) -> Tuple[str, str]:
    if not value:
        return "", ""

    try:
        parsed_datetime = datetime.strptime(str(value).strip(), "%Y-%m-%d %H:%M:%S")
        return str(parsed_datetime.month), str(parsed_datetime.day)
    except ValueError:
        return "", ""


def parse_fireball_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None

    try:
        return datetime.strptime(str(value).strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def parse_close_approach_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None

    text = str(value).strip()

    for date_format in ("%Y-%b-%d %H:%M", "%Y-%b-%d"):
        try:
            return datetime.strptime(text, date_format)
        except ValueError:
            pass

    return None


def date_only(value: Optional[datetime]) -> str:
    if value is None:
        return ""

    return value.strftime("%Y-%m-%d")


def event_id_from_date(prefix: str, date_text: str, index: int) -> str:
    cleaned = re.sub(r"[^0-9]", "", date_text or "")

    if not cleaned:
        cleaned = f"row{index:06d}"

    return f"{prefix}_{cleaned}_{index:05d}"


def sum_float(rows: Iterable[Dict[str, Any]], field_name: str) -> float:
    total = 0.0

    for data_row in rows:
        value = to_float(data_row.get(field_name))

        if value is not None:
            total += value

    return total


def average(total: float, count: int) -> Optional[float]:
    if count <= 0:
        return None

    return total / count


def minimum_float(rows: Iterable[Dict[str, Any]], field_name: str) -> Optional[float]:
    values = [to_float(data_row.get(field_name)) for data_row in rows]
    values = [value for value in values if value is not None]

    if not values:
        return None

    return min(values)


def maximum_float(rows: Iterable[Dict[str, Any]], field_name: str) -> Optional[float]:
    values = [to_float(data_row.get(field_name)) for data_row in rows]
    values = [value for value in values if value is not None]

    if not values:
        return None

    return max(values)


def normalize(value: Optional[float], min_value: Optional[float], max_value: Optional[float], invert: bool = False) -> float:
    if value is None or min_value is None or max_value is None:
        return 0.0

    if max_value == min_value:
        return 0.0

    score = (value - min_value) / (max_value - min_value)

    if invert:
        score = 1.0 - score

    return max(0.0, min(1.0, score))


def unique_join(values: Iterable[Any], separator: str = " | ") -> str:
    seen = set()
    output = []

    for value in values:
        text = str(value or "").strip()

        if not text or text in seen:
            continue

        seen.add(text)
        output.append(text)

    return separator.join(output)



def fetch_json_safe(url: str, params: Optional[Dict[str, Any]] = None, timeout: int = 60) -> Tuple[Optional[Dict[str, Any]], str]:
    try:
        payload = fetch_json(url, params=params, timeout=timeout)
        return payload, ""
    except Exception as exc:
        return None, str(exc)


def normalize_designation(value: Any) -> str:
    text = str(value or "").upper().strip()
    text = re.sub(r"[^A-Z0-9]", "", text)
    return text


def safe_filename(value: Any) -> str:
    text = str(value or "unknown").strip()
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", text)
    return text[:120] or "unknown"


def extract_orbit_element(orbit_payload: Dict[str, Any], element_name: str) -> str:
    elements = orbit_payload.get("elements", [])

    if not isinstance(elements, list):
        return ""

    for element in elements:
        if not isinstance(element, dict):
            continue

        if str(element.get("name", "")).lower() == element_name.lower():
            return str(element.get("value", ""))

    return ""


def extract_sbdb_object_context(designation: str, payload: Optional[Dict[str, Any]], lookup_error: str, lookup_rank: int) -> Dict[str, Any]:
    if payload is None:
        return {
            "lookup_rank": lookup_rank,
            "object_designation": designation,
            "lookup_status": "lookup_error",
            "lookup_error": lookup_error,
            "source_api": "NASA/JPL SBDB API",
        }

    object_payload = payload.get("object", {})
    orbit_payload = payload.get("orbit", {})

    if not isinstance(object_payload, dict):
        object_payload = {}

    if not isinstance(orbit_payload, dict):
        orbit_payload = {}

    orbit_class = object_payload.get("orbit_class", {})
    if not isinstance(orbit_class, dict):
        orbit_class = {}

    moid_au = extract_orbit_element(orbit_payload, "moid")
    perihelion_distance_au = extract_orbit_element(orbit_payload, "q")
    aphelion_distance_au = extract_orbit_element(orbit_payload, "ad")
    semi_major_axis_au = extract_orbit_element(orbit_payload, "a")
    eccentricity = extract_orbit_element(orbit_payload, "e")
    inclination_deg = extract_orbit_element(orbit_payload, "i")
    orbital_period_days = extract_orbit_element(orbit_payload, "per")

    absolute_magnitude_h = object_payload.get("H", "")
    estimated_diameter_km = object_payload.get("diameter", "")

    return {
        "lookup_rank": lookup_rank,
        "object_designation": designation,
        "lookup_status": "ok",
        "object_fullname": object_payload.get("fullname", ""),
        "spkid": object_payload.get("spkid", ""),
        "small_body_kind": object_payload.get("kind", ""),
        "orbit_class_code": orbit_class.get("code", ""),
        "orbit_class_name": orbit_class.get("name", ""),
        "is_neo": object_payload.get("neo", ""),
        "is_pha": object_payload.get("pha", ""),
        "absolute_magnitude_h": absolute_magnitude_h,
        "estimated_diameter_km": estimated_diameter_km,
        "moid_au": moid_au,
        "perihelion_distance_au": perihelion_distance_au,
        "aphelion_distance_au": aphelion_distance_au,
        "semi_major_axis_au": semi_major_axis_au,
        "eccentricity": eccentricity,
        "inclination_deg": inclination_deg,
        "orbital_period_days": orbital_period_days,
        "last_observation_date": orbit_payload.get("last_obs", ""),
        "source_api": "NASA/JPL SBDB API",
        "lookup_error": lookup_error,
    }


def collect_object_designations_for_enrichment() -> List[str]:
    designations: List[str] = []
    seen = set()

    def add_designation(value: Any) -> None:
        text = str(value or "").strip()
        if not text:
            return

        norm = normalize_designation(text)
        if not norm or norm in seen:
            return

        seen.add(norm)
        designations.append(text)

    for data_row in read_csv(PATH_WATCHLIST_CANDIDATES):
        if data_row.get("candidate_type") == "repeating_close_approach_object":
            add_designation(data_row.get("candidate_id"))

    for data_row in read_csv(PATH_REPEATING_CLOSE_APPROACH_OBJECTS):
        add_designation(data_row.get("object_designation"))

    for data_row in read_csv(PATH_CLOSE_APPROACH_WINDOWS):
        object_text = data_row.get("object_designations", "")
        for part in object_text.split("|"):
            add_designation(part.strip())

    return designations[:SBDB_ENRICHMENT_LIMIT]


def confidence_from_score(score: float) -> str:
    if score >= 80.0:
        return "high relative priority"
    if score >= 60.0:
        return "medium relative priority"
    if score >= 40.0:
        return "low-to-medium relative priority"
    return "low relative priority"


# ============================================================
# FETCH + CLEAN
# ============================================================

def fetch_fireballs() -> int:
    params = {
        "limit": FIREBALL_LIMIT,
        "sort": "-date",
        "vel-comp": "true",
    }

    payload = fetch_json(FIREBALL_API_URL, params=params)
    save_json(payload, DATA_RAW_DIR / "fireballs_raw.json")

    fields = payload.get("fields", [])
    clean_rows: List[Dict[str, Any]] = []

    for index, record in enumerate(payload.get("data", []), start=1):
        raw = dict(zip(fields, record))

        date_utc = raw.get("date", "")
        month_value, day_value = parse_month_day_from_fireball_date(date_utc)

        clean_rows.append({
            "event_id": event_id_from_date("FB", date_utc, index),
            "date_utc": date_utc,
            "year": parse_year_from_date_text(date_utc),
            "month": month_value,
            "day": day_value,
            "latitude_deg": signed_coordinate(raw.get("lat"), raw.get("lat-dir")),
            "longitude_deg": signed_coordinate(raw.get("lon"), raw.get("lon-dir")),
            "altitude_km": raw.get("alt", ""),
            "radiated_energy_1e10_j": raw.get("energy", ""),
            "estimated_impact_energy_kt": raw.get("impact-e", ""),
            "velocity_x_km_s": raw.get("vx", ""),
            "velocity_y_km_s": raw.get("vy", ""),
            "velocity_z_km_s": raw.get("vz", ""),
            "data_source": "NASA/JPL CNEOS Fireball Data API",
        })

    write_csv(clean_rows, FIREBALL_HEADERS, DATA_CLEAN_DIR / "fireballs_clean.csv")
    return len(clean_rows)


def fetch_close_approaches() -> int:
    params = {
        "date-min": CLOSE_APPROACH_DATE_MIN,
        "date-max": CLOSE_APPROACH_DATE_MAX,
        "dist-max": CLOSE_APPROACH_DISTANCE_MAX_AU,
        "body": "Earth",
        "sort": "date",
        "limit": CLOSE_APPROACH_LIMIT,
        "diameter": "true",
        "fullname": "true",
    }

    payload = fetch_json(CLOSE_APPROACH_API_URL, params=params)
    save_json(payload, DATA_RAW_DIR / "close_approaches_raw.json")

    fields = payload.get("fields", [])
    clean_rows: List[Dict[str, Any]] = []

    for record in payload.get("data", []):
        raw = dict(zip(fields, record))
        close_date = raw.get("cd", "")

        clean_rows.append({
            "object_designation": raw.get("des", ""),
            "object_fullname": raw.get("fullname", ""),
            "orbit_id": raw.get("orbit_id", ""),
            "close_approach_datetime_tdb": close_date,
            "year": parse_year_from_date_text(close_date),
            "julian_date_tdb": raw.get("jd", ""),
            "distance_au": raw.get("dist", ""),
            "distance_min_au": raw.get("dist_min", ""),
            "distance_max_au": raw.get("dist_max", ""),
            "velocity_relative_km_s": raw.get("v_rel", ""),
            "velocity_infinity_km_s": raw.get("v_inf", ""),
            "time_uncertainty_3sigma": raw.get("t_sigma_f", ""),
            "absolute_magnitude_h": raw.get("h", ""),
            "diameter_km": raw.get("diameter", ""),
            "diameter_sigma_km": raw.get("diameter_sigma", ""),
            "approach_body": "Earth",
            "data_source": "NASA/JPL SBDB Close-Approach Data API",
        })

    write_csv(clean_rows, CLOSE_APPROACH_HEADERS, DATA_CLEAN_DIR / "close_approaches_clean.csv")
    return len(clean_rows)


def fetch_sentry() -> int:
    payload = fetch_json(SENTRY_API_URL)
    save_json(payload, DATA_RAW_DIR / "sentry_risk_raw.json")

    clean_rows: List[Dict[str, Any]] = []

    for raw in payload.get("data", []):
        clean_rows.append({
            "object_id": raw.get("id", ""),
            "object_designation": raw.get("des", ""),
            "object_fullname": raw.get("fullname", ""),
            "year_range": raw.get("range", ""),
            "potential_impact_count": raw.get("n_imp", ""),
            "cumulative_impact_probability": raw.get("ip", ""),
            "palermo_scale_cumulative": raw.get("ps_cum", ""),
            "palermo_scale_maximum": raw.get("ps_max", ""),
            "torino_scale_maximum": raw.get("ts_max", ""),
            "absolute_magnitude_h": raw.get("h", ""),
            "estimated_diameter_km": raw.get("diameter", ""),
            "velocity_infinity_km_s": raw.get("v_inf", ""),
            "last_observation_date": raw.get("last_obs", ""),
            "last_observation_jd": raw.get("last_obs_jd", ""),
            "data_source": "NASA/JPL CNEOS Sentry Data API",
        })

    write_csv(clean_rows, SENTRY_HEADERS, DATA_CLEAN_DIR / "sentry_risk_clean.csv")
    return len(clean_rows)


# ============================================================
# STANDARD REPORTS
# ============================================================

def build_fireball_yearly_summary() -> int:
    rows = read_csv(DATA_CLEAN_DIR / "fireballs_clean.csv")
    grouped: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    for data_row in rows:
        grouped[data_row.get("year") or "unknown"].append(data_row)

    report_rows = []

    for year_key, group_rows in sorted(grouped.items()):
        count = len(group_rows)
        total_energy = sum_float(group_rows, "estimated_impact_energy_kt")
        max_energy = maximum_float(group_rows, "estimated_impact_energy_kt")

        report_rows.append({
            "year": year_key,
            "fireball_event_count": count,
            "total_estimated_impact_energy_kt": safe_round(total_energy),
            "average_estimated_impact_energy_kt": safe_round(average(total_energy, count)),
            "max_estimated_impact_energy_kt": safe_round(max_energy),
        })

    write_csv(report_rows, FIREBALL_YEARLY_SUMMARY_HEADERS, PATH_FIREBALL_YEARLY_SUMMARY)
    return len(report_rows)


def build_fireball_monthly_summary() -> int:
    rows = read_csv(DATA_CLEAN_DIR / "fireballs_clean.csv")
    grouped: Dict[Tuple[str, str], List[Dict[str, str]]] = defaultdict(list)

    for data_row in rows:
        grouped[(data_row.get("year") or "unknown", data_row.get("month") or "unknown")].append(data_row)

    def sort_key(item: Tuple[Tuple[str, str], List[Dict[str, str]]]) -> Tuple[int, int]:
        (year_key, month_key), _ = item
        return int(year_key) if year_key.isdigit() else 999999, int(month_key) if month_key.isdigit() else 99

    report_rows = []

    for (year_key, month_key), group_rows in sorted(grouped.items(), key=sort_key):
        count = len(group_rows)
        total_energy = sum_float(group_rows, "estimated_impact_energy_kt")
        max_energy = maximum_float(group_rows, "estimated_impact_energy_kt")

        report_rows.append({
            "year": year_key,
            "month": month_key,
            "fireball_event_count": count,
            "total_estimated_impact_energy_kt": safe_round(total_energy),
            "average_estimated_impact_energy_kt": safe_round(average(total_energy, count)),
            "max_estimated_impact_energy_kt": safe_round(max_energy),
        })

    write_csv(report_rows, FIREBALL_MONTHLY_SUMMARY_HEADERS, PATH_FIREBALL_MONTHLY_SUMMARY)
    return len(report_rows)


def build_largest_fireballs() -> int:
    rows = read_csv(DATA_CLEAN_DIR / "fireballs_clean.csv")

    ranked_rows = sorted(
        rows,
        key=lambda item: to_float(item.get("estimated_impact_energy_kt")) or -1.0,
        reverse=True,
    )

    report_rows = []

    for rank, data_row in enumerate(ranked_rows[:TOP_REPORT_LIMIT], start=1):
        report_rows.append({
            "rank": rank,
            "event_id": data_row.get("event_id", ""),
            "date_utc": data_row.get("date_utc", ""),
            "year": data_row.get("year", ""),
            "month": data_row.get("month", ""),
            "day": data_row.get("day", ""),
            "latitude_deg": data_row.get("latitude_deg", ""),
            "longitude_deg": data_row.get("longitude_deg", ""),
            "altitude_km": data_row.get("altitude_km", ""),
            "radiated_energy_1e10_j": data_row.get("radiated_energy_1e10_j", ""),
            "estimated_impact_energy_kt": data_row.get("estimated_impact_energy_kt", ""),
        })

    write_csv(report_rows, LARGEST_FIREBALLS_HEADERS, PATH_LARGEST_FIREBALLS)
    return len(report_rows)


def build_close_approach_yearly_summary() -> int:
    rows = read_csv(DATA_CLEAN_DIR / "close_approaches_clean.csv")
    grouped: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    for data_row in rows:
        grouped[data_row.get("year") or "unknown"].append(data_row)

    report_rows = []

    for year_key, group_rows in sorted(grouped.items()):
        report_rows.append({
            "year": year_key,
            "close_approach_count": len(group_rows),
            "minimum_distance_au": safe_round(minimum_float(group_rows, "distance_au"), 12),
            "maximum_velocity_relative_km_s": safe_round(maximum_float(group_rows, "velocity_relative_km_s")),
        })

    write_csv(report_rows, CLOSE_APPROACH_YEARLY_SUMMARY_HEADERS, PATH_CLOSE_APPROACH_YEARLY_SUMMARY)
    return len(report_rows)


def build_closest_approaches() -> int:
    rows = read_csv(DATA_CLEAN_DIR / "close_approaches_clean.csv")

    ranked_rows = sorted(
        rows,
        key=lambda item: to_float(item.get("distance_au")) if to_float(item.get("distance_au")) is not None else float("inf"),
    )

    report_rows = []

    for rank, data_row in enumerate(ranked_rows[:TOP_REPORT_LIMIT], start=1):
        report_rows.append({
            "rank": rank,
            "object_designation": data_row.get("object_designation", ""),
            "object_fullname": data_row.get("object_fullname", ""),
            "close_approach_datetime_tdb": data_row.get("close_approach_datetime_tdb", ""),
            "year": data_row.get("year", ""),
            "distance_au": data_row.get("distance_au", ""),
            "distance_min_au": data_row.get("distance_min_au", ""),
            "distance_max_au": data_row.get("distance_max_au", ""),
            "velocity_relative_km_s": data_row.get("velocity_relative_km_s", ""),
            "absolute_magnitude_h": data_row.get("absolute_magnitude_h", ""),
            "diameter_km": data_row.get("diameter_km", ""),
        })

    write_csv(report_rows, CLOSEST_APPROACHES_HEADERS, PATH_CLOSEST_APPROACHES)
    return len(report_rows)


def build_fastest_approaches() -> int:
    rows = read_csv(DATA_CLEAN_DIR / "close_approaches_clean.csv")

    ranked_rows = sorted(
        rows,
        key=lambda item: to_float(item.get("velocity_relative_km_s")) or -1.0,
        reverse=True,
    )

    report_rows = []

    for rank, data_row in enumerate(ranked_rows[:TOP_REPORT_LIMIT], start=1):
        report_rows.append({
            "rank": rank,
            "object_designation": data_row.get("object_designation", ""),
            "object_fullname": data_row.get("object_fullname", ""),
            "close_approach_datetime_tdb": data_row.get("close_approach_datetime_tdb", ""),
            "year": data_row.get("year", ""),
            "distance_au": data_row.get("distance_au", ""),
            "velocity_relative_km_s": data_row.get("velocity_relative_km_s", ""),
            "velocity_infinity_km_s": data_row.get("velocity_infinity_km_s", ""),
            "absolute_magnitude_h": data_row.get("absolute_magnitude_h", ""),
            "diameter_km": data_row.get("diameter_km", ""),
        })

    write_csv(report_rows, FASTEST_APPROACHES_HEADERS, PATH_FASTEST_CLOSE_APPROACHES)
    return len(report_rows)


def build_sentry_summary() -> int:
    rows = read_csv(DATA_CLEAN_DIR / "sentry_risk_clean.csv")

    report_rows = [
        {"metric": "sentry_object_count", "value": len(rows)},
        {"metric": "highest_cumulative_impact_probability", "value": safe_round(maximum_float(rows, "cumulative_impact_probability"), 12)},
        {"metric": "highest_palermo_scale_cumulative", "value": safe_round(maximum_float(rows, "palermo_scale_cumulative"), 6)},
        {"metric": "highest_torino_scale_maximum", "value": safe_round(maximum_float(rows, "torino_scale_maximum"), 6)},
        {"metric": "largest_estimated_diameter_km", "value": safe_round(maximum_float(rows, "estimated_diameter_km"), 6)},
    ]

    write_csv(report_rows, SENTRY_SUMMARY_HEADERS, PATH_SENTRY_SUMMARY)
    return len(report_rows)


def build_yearly_activity_index() -> int:
    fireballs = read_csv(DATA_CLEAN_DIR / "fireballs_clean.csv")
    approaches = read_csv(DATA_CLEAN_DIR / "close_approaches_clean.csv")

    years = sorted(
        {
            data_row.get("year")
            for data_row in fireballs + approaches
            if data_row.get("year") and data_row.get("year") != "unknown"
        }
    )

    yearly_fireball_count: Dict[str, int] = defaultdict(int)
    yearly_fireball_energy: Dict[str, float] = defaultdict(float)
    yearly_close_approach_count: Dict[str, int] = defaultdict(int)
    yearly_closest_distance: Dict[str, Optional[float]] = defaultdict(lambda: None)
    yearly_fastest_velocity: Dict[str, Optional[float]] = defaultdict(lambda: None)

    for data_row in fireballs:
        year_key = data_row.get("year")
        if not year_key:
            continue

        yearly_fireball_count[year_key] += 1
        yearly_fireball_energy[year_key] += to_float(data_row.get("estimated_impact_energy_kt")) or 0.0

    for data_row in approaches:
        year_key = data_row.get("year")
        if not year_key:
            continue

        yearly_close_approach_count[year_key] += 1
        distance = to_float(data_row.get("distance_au"))
        velocity = to_float(data_row.get("velocity_relative_km_s"))

        if distance is not None:
            current_distance = yearly_closest_distance[year_key]
            if current_distance is None or distance < current_distance:
                yearly_closest_distance[year_key] = distance

        if velocity is not None:
            current_velocity = yearly_fastest_velocity[year_key]
            if current_velocity is None or velocity > current_velocity:
                yearly_fastest_velocity[year_key] = velocity

    fireball_counts = [float(yearly_fireball_count[year_key]) for year_key in years]
    energies = [yearly_fireball_energy[year_key] for year_key in years]
    approach_counts = [float(yearly_close_approach_count[year_key]) for year_key in years]
    closest_distances = [yearly_closest_distance[year_key] for year_key in years if yearly_closest_distance[year_key] is not None]
    fastest_velocities = [yearly_fastest_velocity[year_key] for year_key in years if yearly_fastest_velocity[year_key] is not None]

    min_fireball_count = min(fireball_counts) if fireball_counts else None
    max_fireball_count = max(fireball_counts) if fireball_counts else None
    min_energy = min(energies) if energies else None
    max_energy = max(energies) if energies else None
    min_approach_count = min(approach_counts) if approach_counts else None
    max_approach_count = max(approach_counts) if approach_counts else None
    min_distance = min(closest_distances) if closest_distances else None
    max_distance = max(closest_distances) if closest_distances else None
    min_velocity = min(fastest_velocities) if fastest_velocities else None
    max_velocity = max(fastest_velocities) if fastest_velocities else None

    report_rows = []

    for year_key in years:
        fireball_count = yearly_fireball_count[year_key]
        fireball_energy = yearly_fireball_energy[year_key]
        approach_count = yearly_close_approach_count[year_key]
        closest_distance = yearly_closest_distance[year_key]
        fastest_velocity = yearly_fastest_velocity[year_key]

        fireball_count_score = normalize(float(fireball_count), min_fireball_count, max_fireball_count)
        energy_score = normalize(fireball_energy, min_energy, max_energy)
        approach_count_score = normalize(float(approach_count), min_approach_count, max_approach_count)
        closest_distance_score = normalize(closest_distance, min_distance, max_distance, invert=True)
        fastest_velocity_score = normalize(fastest_velocity, min_velocity, max_velocity)

        activity_score = (
            fireball_count_score * 0.20
            + energy_score * 0.25
            + approach_count_score * 0.20
            + closest_distance_score * 0.20
            + fastest_velocity_score * 0.15
        ) * 100.0

        report_rows.append({
            "year": year_key,
            "fireball_event_count": fireball_count,
            "fireball_total_energy_kt": safe_round(fireball_energy),
            "close_approach_count": approach_count,
            "closest_approach_distance_au": safe_round(closest_distance, 12),
            "fastest_approach_velocity_km_s": safe_round(fastest_velocity),
            "activity_score": safe_round(activity_score, 3),
            "activity_score_note": "0-100 relative score inside current fetched dataset; not a planetary danger score",
        })

    write_csv(report_rows, YEARLY_ACTIVITY_INDEX_HEADERS, PATH_YEARLY_ACTIVITY_INDEX)
    return len(report_rows)


# ============================================================
# PATTERN FINDER REPORTS
# ============================================================

def build_fireball_month_clusters() -> int:
    rows = read_csv(DATA_CLEAN_DIR / "fireballs_clean.csv")
    grouped: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    for data_row in rows:
        month_key = data_row.get("month") or "unknown"
        grouped[month_key].append(data_row)

    counts = [len(group_rows) for group_rows in grouped.values()]
    energies = [sum_float(group_rows, "estimated_impact_energy_kt") for group_rows in grouped.values()]

    min_count = min(counts) if counts else None
    max_count = max(counts) if counts else None
    min_energy = min(energies) if energies else None
    max_energy = max(energies) if energies else None

    report_rows = []

    for month_key, group_rows in grouped.items():
        count = len(group_rows)
        total_energy = sum_float(group_rows, "estimated_impact_energy_kt")
        max_single = maximum_float(group_rows, "estimated_impact_energy_kt")
        active_years = len({data_row.get("year") for data_row in group_rows if data_row.get("year")})

        count_score = normalize(float(count), min_count, max_count)
        energy_score = normalize(total_energy, min_energy, max_energy)
        cluster_score = (count_score * 0.55 + energy_score * 0.45) * 100.0

        report_rows.append({
            "month": month_key,
            "total_fireball_event_count": count,
            "total_estimated_impact_energy_kt": safe_round(total_energy),
            "average_energy_per_event_kt": safe_round(average(total_energy, count)),
            "max_single_event_energy_kt": safe_round(max_single),
            "active_year_count": active_years,
            "cluster_score": safe_round(cluster_score, 3),
            "cluster_note": "Monthly recurrence clue only; may reflect seasonal detection/reporting effects",
        })

    def sort_key(data_row: Dict[str, Any]) -> Tuple[float, int]:
        month_text = str(data_row.get("month", "99"))
        return -float(data_row.get("cluster_score") or 0), int(month_text) if month_text.isdigit() else 99

    report_rows = sorted(report_rows, key=sort_key)

    write_csv(report_rows, FIREBALL_MONTH_CLUSTERS_HEADERS, PATH_FIREBALL_MONTH_CLUSTERS)
    return len(report_rows)


def build_repeating_close_approach_objects() -> int:
    rows = read_csv(DATA_CLEAN_DIR / "close_approaches_clean.csv")
    grouped: Dict[str, List[Dict[str, str]]] = defaultdict(list)

    for data_row in rows:
        designation = data_row.get("object_designation") or "unknown"
        grouped[designation].append(data_row)

    report_rows = []

    for designation, group_rows in grouped.items():
        if len(group_rows) < REPEAT_OBJECT_MIN_COUNT:
            continue

        sorted_rows = sorted(
            group_rows,
            key=lambda item: parse_close_approach_datetime(item.get("close_approach_datetime_tdb")) or datetime.max,
        )

        min_distance = minimum_float(sorted_rows, "distance_au")
        max_velocity = maximum_float(sorted_rows, "velocity_relative_km_s")
        diameter = maximum_float(sorted_rows, "diameter_km")
        h_mag = minimum_float(sorted_rows, "absolute_magnitude_h")

        approach_count_score = min(len(sorted_rows) * 10.0, 50.0)

        if min_distance is None:
            distance_score = 0.0
        else:
            distance_score = max(
                0.0,
                min(
                    30.0,
                    (CLOSE_APPROACH_DISTANCE_MAX_AU_FLOAT - min_distance)
                    / CLOSE_APPROACH_DISTANCE_MAX_AU_FLOAT
                    * 30.0,
                ),
            )

        velocity_score = 0.0 if max_velocity is None else min(max_velocity / 2.0, 20.0)
        repeat_score = approach_count_score + distance_score + velocity_score

        report_rows.append({
            "rank": "",
            "object_designation": designation,
            "object_fullname": sorted_rows[0].get("object_fullname", ""),
            "approach_count": len(sorted_rows),
            "first_close_approach_datetime_tdb": sorted_rows[0].get("close_approach_datetime_tdb", ""),
            "last_close_approach_datetime_tdb": sorted_rows[-1].get("close_approach_datetime_tdb", ""),
            "minimum_distance_au": safe_round(min_distance, 12),
            "maximum_velocity_relative_km_s": safe_round(max_velocity),
            "absolute_magnitude_h": safe_round(h_mag),
            "diameter_km": safe_round(diameter),
            "repeat_score": safe_round(repeat_score, 3),
        })

    report_rows = sorted(report_rows, key=lambda item: float(item.get("repeat_score") or 0), reverse=True)

    for rank, data_row in enumerate(report_rows, start=1):
        data_row["rank"] = rank

    write_csv(report_rows, REPEATING_CLOSE_APPROACH_OBJECTS_HEADERS, PATH_REPEATING_CLOSE_APPROACH_OBJECTS)
    return len(report_rows)


def build_high_energy_fireball_windows() -> int:
    rows = read_csv(DATA_CLEAN_DIR / "fireballs_clean.csv")

    high_energy_rows: List[Dict[str, Any]] = []

    for data_row in rows:
        energy = to_float(data_row.get("estimated_impact_energy_kt"))
        event_datetime = parse_fireball_datetime(data_row.get("date_utc"))

        if energy is None or event_datetime is None:
            continue

        if energy >= HIGH_ENERGY_FIREBALL_KT_THRESHOLD:
            row_copy: Dict[str, Any] = dict(data_row)
            row_copy["_datetime"] = event_datetime
            row_copy["_energy"] = energy
            high_energy_rows.append(row_copy)

    high_energy_rows = sorted(high_energy_rows, key=lambda item: item["_datetime"])

    windows: List[Tuple[datetime, datetime, List[Dict[str, Any]]]] = []
    used_indices = set()

    for index, data_row in enumerate(high_energy_rows):
        if index in used_indices:
            continue

        start_datetime = data_row["_datetime"]
        end_datetime = start_datetime + timedelta(days=HIGH_ENERGY_WINDOW_DAYS)
        window_rows = []

        for other_index, other_row in enumerate(high_energy_rows):
            if other_index in used_indices:
                continue

            other_datetime = other_row["_datetime"]

            if start_datetime <= other_datetime <= end_datetime:
                window_rows.append(other_row)
                used_indices.add(other_index)

        windows.append((start_datetime, end_datetime, window_rows))

    report_rows = []

    for window_index, (start_datetime, end_datetime, window_rows) in enumerate(windows, start=1):
        total_energy = sum(float(data_row["_energy"]) for data_row in window_rows)
        max_energy = max((float(data_row["_energy"]) for data_row in window_rows), default=0.0)

        report_rows.append({
            "window_id": f"HEF_{window_index:04d}",
            "window_start_date": date_only(start_datetime),
            "window_end_date": date_only(end_datetime),
            "event_count": len(window_rows),
            "total_estimated_impact_energy_kt": safe_round(total_energy),
            "max_estimated_impact_energy_kt": safe_round(max_energy),
            "event_ids": unique_join(data_row.get("event_id") for data_row in window_rows),
            "dates_utc": unique_join(data_row.get("date_utc") for data_row in window_rows),
            "window_note": f"High-energy fireballs >= {HIGH_ENERGY_FIREBALL_KT_THRESHOLD} kt inside {HIGH_ENERGY_WINDOW_DAYS}-day window",
        })

    report_rows = sorted(
        report_rows,
        key=lambda item: (float(item.get("total_estimated_impact_energy_kt") or 0), int(item.get("event_count") or 0)),
        reverse=True,
    )

    write_csv(report_rows, HIGH_ENERGY_FIREBALL_WINDOWS_HEADERS, PATH_HIGH_ENERGY_FIREBALL_WINDOWS)
    return len(report_rows)


def build_close_approach_windows() -> int:
    rows = read_csv(DATA_CLEAN_DIR / "close_approaches_clean.csv")

    close_rows: List[Dict[str, Any]] = []

    for data_row in rows:
        distance = to_float(data_row.get("distance_au"))
        approach_datetime = parse_close_approach_datetime(data_row.get("close_approach_datetime_tdb"))

        if distance is None or approach_datetime is None:
            continue

        if distance <= CLOSE_APPROACH_CLUSTER_DISTANCE_AU:
            row_copy: Dict[str, Any] = dict(data_row)
            row_copy["_datetime"] = approach_datetime
            row_copy["_distance"] = distance
            close_rows.append(row_copy)

    close_rows = sorted(close_rows, key=lambda item: item["_datetime"])

    windows: List[Tuple[datetime, datetime, List[Dict[str, Any]]]] = []
    used_indices = set()

    for index, data_row in enumerate(close_rows):
        if index in used_indices:
            continue

        start_datetime = data_row["_datetime"]
        end_datetime = start_datetime + timedelta(days=CLOSE_APPROACH_WINDOW_DAYS)
        window_rows = []

        for other_index, other_row in enumerate(close_rows):
            if other_index in used_indices:
                continue

            other_datetime = other_row["_datetime"]

            if start_datetime <= other_datetime <= end_datetime:
                window_rows.append(other_row)
                used_indices.add(other_index)

        windows.append((start_datetime, end_datetime, window_rows))

    report_rows = []

    for window_index, (start_datetime, end_datetime, window_rows) in enumerate(windows, start=1):
        closest_distance = min((float(data_row["_distance"]) for data_row in window_rows), default=None)
        fastest_velocity = maximum_float(window_rows, "velocity_relative_km_s")

        report_rows.append({
            "window_id": f"CAW_{window_index:04d}",
            "window_start_date": date_only(start_datetime),
            "window_end_date": date_only(end_datetime),
            "close_approach_count": len(window_rows),
            "closest_distance_au": safe_round(closest_distance, 12),
            "fastest_velocity_relative_km_s": safe_round(fastest_velocity),
            "object_designations": unique_join(data_row.get("object_designation") for data_row in window_rows),
            "close_approach_datetimes_tdb": unique_join(data_row.get("close_approach_datetime_tdb") for data_row in window_rows),
            "window_note": f"Close approaches <= {CLOSE_APPROACH_CLUSTER_DISTANCE_AU} au inside {CLOSE_APPROACH_WINDOW_DAYS}-day window",
        })

    report_rows = sorted(
        report_rows,
        key=lambda item: (int(item.get("close_approach_count") or 0), -(float(item.get("closest_distance_au") or 99))),
        reverse=True,
    )

    write_csv(report_rows, CLOSE_APPROACH_WINDOWS_HEADERS, PATH_CLOSE_APPROACH_WINDOWS)
    return len(report_rows)


def build_watchlist_candidates() -> int:
    candidates = []

    for data_row in read_csv(PATH_FIREBALL_MONTH_CLUSTERS):
        score = to_float(data_row.get("cluster_score")) or 0.0

        if score >= WATCHLIST_MIN_SCORE:
            candidates.append({
                "candidate_type": "fireball_month_cluster",
                "candidate_id": f"month_{data_row.get('month')}",
                "candidate_name": f"Month {data_row.get('month')}",
                "primary_date_or_window": f"month={data_row.get('month')}",
                "score": score,
                "reason": f"{data_row.get('total_fireball_event_count')} fireballs; total energy {data_row.get('total_estimated_impact_energy_kt')} kt",
                "source_report": "fireball_month_clusters.csv",
            })

    for data_row in read_csv(PATH_REPEATING_CLOSE_APPROACH_OBJECTS):
        score = to_float(data_row.get("repeat_score")) or 0.0

        if score >= WATCHLIST_MIN_SCORE:
            candidates.append({
                "candidate_type": "repeating_close_approach_object",
                "candidate_id": data_row.get("object_designation", ""),
                "candidate_name": data_row.get("object_fullname") or data_row.get("object_designation", ""),
                "primary_date_or_window": f"{data_row.get('first_close_approach_datetime_tdb')} to {data_row.get('last_close_approach_datetime_tdb')}",
                "score": score,
                "reason": f"{data_row.get('approach_count')} close approaches; minimum distance {data_row.get('minimum_distance_au')} au",
                "source_report": "repeating_close_approach_objects.csv",
            })

    for data_row in read_csv(PATH_HIGH_ENERGY_FIREBALL_WINDOWS):
        event_count = to_float(data_row.get("event_count")) or 0.0
        total_energy = to_float(data_row.get("total_estimated_impact_energy_kt")) or 0.0
        score = min(100.0, event_count * 20.0 + total_energy * 5.0)

        if score >= WATCHLIST_MIN_SCORE:
            candidates.append({
                "candidate_type": "high_energy_fireball_window",
                "candidate_id": data_row.get("window_id", ""),
                "candidate_name": data_row.get("window_id", ""),
                "primary_date_or_window": f"{data_row.get('window_start_date')} to {data_row.get('window_end_date')}",
                "score": score,
                "reason": f"{data_row.get('event_count')} high-energy fireballs; total energy {data_row.get('total_estimated_impact_energy_kt')} kt",
                "source_report": "high_energy_fireball_windows.csv",
            })

    for data_row in read_csv(PATH_CLOSE_APPROACH_WINDOWS):
        count = to_float(data_row.get("close_approach_count")) or 0.0
        closest = to_float(data_row.get("closest_distance_au"))
        distance_bonus = 0.0 if closest is None else max(
            0.0,
            (CLOSE_APPROACH_CLUSTER_DISTANCE_AU - closest) / CLOSE_APPROACH_CLUSTER_DISTANCE_AU * 40.0,
        )
        score = min(100.0, count * 15.0 + distance_bonus)

        if score >= WATCHLIST_MIN_SCORE:
            candidates.append({
                "candidate_type": "close_approach_window",
                "candidate_id": data_row.get("window_id", ""),
                "candidate_name": data_row.get("window_id", ""),
                "primary_date_or_window": f"{data_row.get('window_start_date')} to {data_row.get('window_end_date')}",
                "score": score,
                "reason": f"{data_row.get('close_approach_count')} close approaches; closest distance {data_row.get('closest_distance_au')} au",
                "source_report": "close_approach_windows.csv",
            })

    candidates = sorted(candidates, key=lambda item: float(item["score"]), reverse=True)

    report_rows = []
    for rank, data_row in enumerate(candidates, start=1):
        report_rows.append({
            "rank": rank,
            "candidate_type": data_row.get("candidate_type", ""),
            "candidate_id": data_row.get("candidate_id", ""),
            "candidate_name": data_row.get("candidate_name", ""),
            "primary_date_or_window": data_row.get("primary_date_or_window", ""),
            "score": safe_round(to_float(data_row.get("score")), 3),
            "reason": data_row.get("reason", ""),
            "source_report": data_row.get("source_report", ""),
        })

    write_csv(report_rows, WATCHLIST_CANDIDATES_HEADERS, PATH_WATCHLIST_CANDIDATES)
    return len(report_rows)


# ============================================================
# EVIDENCE REVIEW MODE
# ============================================================

def explain_candidate(candidate_row: Dict[str, str]) -> Dict[str, str]:
    candidate_type = candidate_row.get("candidate_type", "")
    candidate_id = candidate_row.get("candidate_id", "")
    candidate_name = candidate_row.get("candidate_name", "")
    date_window = candidate_row.get("primary_date_or_window", "")
    score = to_float(candidate_row.get("score")) or 0.0
    reason = candidate_row.get("reason", "")
    source_report = candidate_row.get("source_report", "")

    confidence = confidence_from_score(score)

    if candidate_type == "fireball_month_cluster":
        summary = f"{candidate_name} is showing repeated fireball activity inside the fetched CNEOS fireball sample."
        evidence = f"Pattern source: {source_report}. Reason: {reason}. Score: {score}."
        limitations = "Monthly clustering can be affected by seasonal observation geometry, sensor coverage, reporting bias, and the limited 500-row sample."
        next_check = "Compare this month against known meteor showers and extend the fireball limit/date coverage."

    elif candidate_type == "repeating_close_approach_object":
        summary = f"{candidate_name} appears multiple times in the close-approach dataset."
        evidence = f"Pattern source: {source_report}. Reason: {reason}. Score: {score}."
        limitations = "Repeat appearance does not imply impact risk; it may simply mean a well-tracked object with a known Earth-crossing orbit."
        next_check = "Look up the object in the JPL Small-Body Database and compare MOID, orbit class, diameter, and Sentry status."

    elif candidate_type == "high_energy_fireball_window":
        summary = f"{candidate_name} groups high-energy fireballs into a short time window."
        evidence = f"Pattern source: {source_report}. Reason: {reason}. Score: {score}."
        limitations = "A high-energy window can be dominated by one large bolide and does not automatically prove a debris stream."
        next_check = "Check whether the dates line up with known meteor showers, Taurid activity, Perseids, Geminids, Leonids, or sporadic fireball seasonality."

    elif candidate_type == "close_approach_window":
        summary = f"{candidate_name} groups multiple close approaches into a short time window."
        evidence = f"Pattern source: {source_report}. Reason: {reason}. Score: {score}."
        limitations = "Close-approach clustering can occur because the query covers known catalog objects and detection timing is not uniform."
        next_check = "Check whether grouped objects share orbital elements, parent families, meteor streams, or discovery/observational bias."

    else:
        summary = f"{candidate_name} was flagged by the pattern finder."
        evidence = f"Pattern source: {source_report}. Reason: {reason}. Score: {score}."
        limitations = "Candidate type is not recognized by the evidence reviewer."
        next_check = "Inspect the source report manually."

    return {
        "rank": candidate_row.get("rank", ""),
        "candidate_type": candidate_type,
        "candidate_id": candidate_id,
        "candidate_name": candidate_name,
        "primary_date_or_window": date_window,
        "score": candidate_row.get("score", ""),
        "confidence_level": confidence,
        "plain_english_summary": summary,
        "supporting_evidence": evidence,
        "limitations": limitations,
        "next_check": next_check,
        "source_report": source_report,
    }


def build_watchlist_explained() -> int:
    watchlist_rows = read_csv(PATH_WATCHLIST_CANDIDATES)
    explained_rows = [explain_candidate(data_row) for data_row in watchlist_rows]

    write_csv(explained_rows, WATCHLIST_EXPLAINED_HEADERS, PATH_WATCHLIST_EXPLAINED)
    return len(explained_rows)


def build_research_questions() -> int:
    explained_rows = read_csv(PATH_WATCHLIST_EXPLAINED)
    question_rows = []

    priority = 1

    for data_row in explained_rows[:TOP_CANDIDATE_PACKET_LIMIT]:
        candidate_id = data_row.get("candidate_id", "")
        candidate_type = data_row.get("candidate_type", "")
        candidate_name = data_row.get("candidate_name", "")

        if candidate_type == "fireball_month_cluster":
            questions = [
                (
                    f"Do known meteor showers peak during {candidate_name}?",
                    "This checks whether the cluster matches an established debris-stream crossing.",
                    "IAU Meteor Data Center / meteor shower catalog",
                ),
                (
                    f"Does {candidate_name} remain elevated when using a larger fireball sample?",
                    "This tests whether the signal survives more data rather than being a small-sample artifact.",
                    "CNEOS Fireball API with higher limit or archive exports",
                ),
            ]

        elif candidate_type == "repeating_close_approach_object":
            questions = [
                (
                    f"What is the orbit class, MOID, and diameter estimate for {candidate_name}?",
                    "This separates ordinary repeat visitors from objects that deserve deeper tracking.",
                    "JPL Small-Body Database Browser / SBDB API",
                ),
                (
                    f"Is {candidate_name} listed in Sentry or any official risk table?",
                    "This checks whether the object has any recognized impact-monitoring significance.",
                    "NASA/JPL CNEOS Sentry",
                ),
            ]

        elif candidate_type == "high_energy_fireball_window":
            questions = [
                (
                    f"Do the events in {candidate_name} line up with a known meteor stream?",
                    "This tests whether a clustered high-energy window has a plausible parent stream.",
                    "IAU Meteor Data Center / CNEOS Fireball API",
                ),
                (
                    f"Is the window dominated by one event or multiple comparable events?",
                    "This distinguishes a true cluster from a single outlier.",
                    "largest_fireballs.csv and high_energy_fireball_windows.csv",
                ),
            ]

        elif candidate_type == "close_approach_window":
            questions = [
                (
                    f"Do the objects in {candidate_name} share similar orbital elements?",
                    "This checks whether the window may represent related objects or merely calendar coincidence.",
                    "JPL SBDB orbital elements",
                ),
                (
                    f"Are the close approaches in {candidate_name} mostly newly discovered or long-known objects?",
                    "This helps detect discovery/observation bias.",
                    "Minor Planet Center observations / JPL SBDB discovery metadata",
                ),
            ]

        else:
            questions = [
                (
                    f"What primary data produced candidate {candidate_id}?",
                    "This candidate needs manual inspection because its type is unknown.",
                    "Source report listed in watchlist_explained.csv",
                )
            ]

        for question, why_it_matters, suggested_source in questions:
            question_rows.append({
                "priority": priority,
                "candidate_id": candidate_id,
                "candidate_type": candidate_type,
                "research_question": question,
                "why_it_matters": why_it_matters,
                "suggested_next_data_source": suggested_source,
            })
            priority += 1

    write_csv(question_rows, RESEARCH_QUESTIONS_HEADERS, PATH_RESEARCH_QUESTIONS)
    return len(question_rows)


def build_top_candidate_packet() -> int:
    explained_rows = read_csv(PATH_WATCHLIST_EXPLAINED)
    question_rows = read_csv(PATH_RESEARCH_QUESTIONS)

    packet_path = PATH_TOP_CANDIDATE_PACKET

    lines = [
        "IuPetra v1.3.1 - Top Candidate Packet",
        "====================================",
        "",
        "Purpose:",
        "This packet summarizes the strongest anomaly-hunting candidates from the current run.",
        "These are not official impact-risk predictions. They are leads for investigation.",
        "Orbit context reports: object_orbit_context.csv, sentry_crosscheck.csv, candidate_orbit_review.csv.",
        "",
        f"Generated UTC: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
    ]

    top_rows = explained_rows[:TOP_CANDIDATE_PACKET_LIMIT]

    if not top_rows:
        lines.extend([
            "No watchlist candidates were generated in this run.",
            "",
        ])
    else:
        for data_row in top_rows:
            candidate_id = data_row.get("candidate_id", "")
            matching_questions = [
                question_row
                for question_row in question_rows
                if question_row.get("candidate_id") == candidate_id
            ]

            lines.extend([
                f"Rank {data_row.get('rank')}: {data_row.get('candidate_name')}",
                "-" * 72,
                f"Type: {data_row.get('candidate_type')}",
                f"ID: {candidate_id}",
                f"Window/Date: {data_row.get('primary_date_or_window')}",
                f"Score: {data_row.get('score')}",
                f"Confidence: {data_row.get('confidence_level')}",
                "",
                "Summary:",
                data_row.get("plain_english_summary", ""),
                "",
                "Supporting evidence:",
                data_row.get("supporting_evidence", ""),
                "",
                "Limitations:",
                data_row.get("limitations", ""),
                "",
                "Next check:",
                data_row.get("next_check", ""),
                "",
                "Research questions:",
            ])

            if matching_questions:
                for question_row in matching_questions:
                    lines.append(f"- {question_row.get('research_question')}")
            else:
                lines.append("- No generated research questions for this candidate.")

            lines.append("")

    packet_path.parent.mkdir(parents=True, exist_ok=True)
    packet_path.write_text("\n".join(lines), encoding="utf-8")

    return len(top_rows)



# ============================================================
# ORBIT CONTEXT MODE
# ============================================================

def build_object_orbit_context() -> int:
    designations = collect_object_designations_for_enrichment()
    report_rows = []

    for lookup_rank, designation in enumerate(designations, start=1):
        params = {
            "sstr": designation,
            "phys-par": "true",
            "ca-data": "false",
        }

        payload, lookup_error = fetch_json_safe(SBDB_API_URL, params=params)
        raw_path = DATA_RAW_DIR / "sbdb_context" / f"{safe_filename(designation)}.json"

        if payload is not None:
            save_json(payload, raw_path)

        report_rows.append(
            extract_sbdb_object_context(
                designation=designation,
                payload=payload,
                lookup_error=lookup_error,
                lookup_rank=lookup_rank,
            )
        )

    write_csv(report_rows, OBJECT_ORBIT_CONTEXT_HEADERS, PATH_OBJECT_ORBIT_CONTEXT)
    return len(report_rows)


def build_sentry_crosscheck() -> int:
    watchlist_rows = read_csv(PATH_WATCHLIST_CANDIDATES)
    sentry_rows = read_csv(DATA_CLEAN_DIR / "sentry_risk_clean.csv")

    sentry_by_norm = {
        normalize_designation(data_row.get("object_designation")): data_row
        for data_row in sentry_rows
        if normalize_designation(data_row.get("object_designation"))
    }

    report_rows = []

    for candidate in watchlist_rows:
        candidate_type = candidate.get("candidate_type", "")
        candidate_id = candidate.get("candidate_id", "")
        candidate_name = candidate.get("candidate_name", "")
        possible_designations = []

        if candidate_type == "repeating_close_approach_object":
            possible_designations.append(candidate_id)

        elif candidate_type == "close_approach_window":
            for window_row in read_csv(PATH_CLOSE_APPROACH_WINDOWS):
                if window_row.get("window_id") == candidate_id:
                    possible_designations.extend(part.strip() for part in window_row.get("object_designations", "").split("|"))

        if not possible_designations:
            report_rows.append({
                "candidate_id": candidate_id,
                "candidate_name": candidate_name,
                "candidate_type": candidate_type,
                "object_designation": "",
                "sentry_match_status": "not_applicable",
                "crosscheck_note": "Candidate is not a specific asteroid/comet object.",
            })
            continue

        matched_any = False

        for designation in possible_designations:
            if not designation:
                continue

            norm = normalize_designation(designation)
            sentry_match = sentry_by_norm.get(norm)

            if sentry_match:
                matched_any = True
                report_rows.append({
                    "candidate_id": candidate_id,
                    "candidate_name": candidate_name,
                    "candidate_type": candidate_type,
                    "object_designation": designation,
                    "sentry_match_status": "matched_sentry",
                    "sentry_object_fullname": sentry_match.get("object_fullname", ""),
                    "year_range": sentry_match.get("year_range", ""),
                    "potential_impact_count": sentry_match.get("potential_impact_count", ""),
                    "cumulative_impact_probability": sentry_match.get("cumulative_impact_probability", ""),
                    "palermo_scale_cumulative": sentry_match.get("palermo_scale_cumulative", ""),
                    "palermo_scale_maximum": sentry_match.get("palermo_scale_maximum", ""),
                    "torino_scale_maximum": sentry_match.get("torino_scale_maximum", ""),
                    "estimated_diameter_km": sentry_match.get("estimated_diameter_km", ""),
                    "crosscheck_note": "Object appears in the current fetched CNEOS Sentry table.",
                })
            else:
                report_rows.append({
                    "candidate_id": candidate_id,
                    "candidate_name": candidate_name,
                    "candidate_type": candidate_type,
                    "object_designation": designation,
                    "sentry_match_status": "not_matched_in_fetched_sentry",
                    "crosscheck_note": "No match in the current fetched Sentry table. This is not proof of zero risk; it only means no match in this run's Sentry data.",
                })

        if not matched_any and not report_rows:
            report_rows.append({
                "candidate_id": candidate_id,
                "candidate_name": candidate_name,
                "candidate_type": candidate_type,
                "object_designation": "",
                "sentry_match_status": "no_object_designations_found",
                "crosscheck_note": "No object designations could be extracted for this candidate.",
            })

    write_csv(report_rows, SENTRY_CROSSCHECK_HEADERS, PATH_SENTRY_CROSSCHECK)
    return len(report_rows)


def build_candidate_orbit_review() -> int:
    watchlist_rows = read_csv(PATH_WATCHLIST_CANDIDATES)
    orbit_rows = read_csv(PATH_OBJECT_ORBIT_CONTEXT)
    sentry_rows = read_csv(PATH_SENTRY_CROSSCHECK)

    orbit_by_norm = {
        normalize_designation(data_row.get("object_designation")): data_row
        for data_row in orbit_rows
        if normalize_designation(data_row.get("object_designation"))
    }

    sentry_by_candidate = defaultdict(list)
    for data_row in sentry_rows:
        sentry_by_candidate[data_row.get("candidate_id", "")].append(data_row)

    report_rows = []

    for watchlist_row in watchlist_rows:
        candidate_id = watchlist_row.get("candidate_id", "")
        candidate_type = watchlist_row.get("candidate_type", "")

        orbit_row: Dict[str, str] = {}

        if candidate_type == "repeating_close_approach_object":
            orbit_row = orbit_by_norm.get(normalize_designation(candidate_id), {})

        sentry_candidates = sentry_by_candidate.get(candidate_id, [])
        sentry_match = next(
            (item for item in sentry_candidates if item.get("sentry_match_status") == "matched_sentry"),
            sentry_candidates[0] if sentry_candidates else {},
        )

        if orbit_row:
            orbit_status = orbit_row.get("lookup_status", "unknown")
            review_note = "Specific object enriched with SBDB orbital context."
        elif candidate_type in {"fireball_month_cluster", "high_energy_fireball_window"}:
            orbit_status = "not_applicable"
            review_note = "Candidate is a time/month pattern, not a single cataloged object."
        else:
            orbit_status = "not_enriched"
            review_note = "No direct SBDB context attached in this run."

        report_rows.append({
            "rank": watchlist_row.get("rank", ""),
            "candidate_type": candidate_type,
            "candidate_id": candidate_id,
            "candidate_name": watchlist_row.get("candidate_name", ""),
            "primary_date_or_window": watchlist_row.get("primary_date_or_window", ""),
            "score": watchlist_row.get("score", ""),
            "orbit_context_status": orbit_status,
            "orbit_class_code": orbit_row.get("orbit_class_code", ""),
            "orbit_class_name": orbit_row.get("orbit_class_name", ""),
            "is_neo": orbit_row.get("is_neo", ""),
            "is_pha": orbit_row.get("is_pha", ""),
            "moid_au": orbit_row.get("moid_au", ""),
            "estimated_diameter_km": orbit_row.get("estimated_diameter_km", ""),
            "sentry_match_status": sentry_match.get("sentry_match_status", ""),
            "sentry_year_range": sentry_match.get("year_range", ""),
            "sentry_impact_probability": sentry_match.get("cumulative_impact_probability", ""),
            "review_note": review_note,
        })

    write_csv(report_rows, CANDIDATE_ORBIT_REVIEW_HEADERS, PATH_CANDIDATE_ORBIT_REVIEW)
    return len(report_rows)


# ============================================================
# WORKSPACE ORGANIZER
# ============================================================

def build_readme_start_here() -> int:
    lines = [
        "IuPetra v1.3 - Stability + Dashboard",
        "========================================",
        "",
        "Start here if you are trying to understand the run.",
        "",
        "Recommended reading order:",
        "",
        "Before changing code:",
        "Edit settings.json in the main IuPetra folder to adjust limits, thresholds, date range, and scoring sensitivity.",
        "",
        "1. IuPetra_START_HERE.html",
        "   Visual dashboard and navigation hub.",
        "",
        "2. top_candidate_packet.txt",
        "   Human-readable summary of the strongest candidates and why they were flagged.",
        "",
        "3. REPORT_INDEX.csv",
        "   Map of every important report and where it lives.",
        "",
        "../01_EVIDENCE_REVIEW/watchlist_explained.csv",
        "   Spreadsheet version of candidate explanations.",
        "",
        "../03_ORBIT_CONTEXT/candidate_orbit_review.csv",
        "   Shows whether watchlist objects have orbit context, NEO/PHA flags, MOID, and Sentry status.",
        "",
        "../01_EVIDENCE_REVIEW/research_questions.csv",
        "   Next research questions for investigating candidates without jumping to conclusions.",
        "",
        "Folder guide:",
        "",
        "settings.json",
        "  No-code controls for thresholds, limits, dates, and watchlist sensitivity.",
        "",
        "data/raw",
        "  Original API JSON payloads and SBDB object context JSON lookups.",
        "",
        "data/clean",
        "  Clean normalized CSV tables.",
        "",
        "reports/00_START_HERE",
        "  Most important human-facing outputs.",
        "",
        "reports/01_EVIDENCE_REVIEW",
        "  Explanation layer: why a candidate was flagged, limitations, and next checks.",
        "",
        "reports/02_PATTERN_FINDER",
        "  Pattern reports: clusters, windows, repeated objects, and watchlist generation.",
        "",
        "reports/03_ORBIT_CONTEXT",
        "  Object enrichment reports from JPL SBDB and Sentry crosscheck.",
        "",
        "reports/04_SUMMARIES",
        "  General yearly/monthly summaries and top-N lists.",
        "",
        "reports/99_TECHNICAL_LOGS",
        "  Run manifest and technical configuration details.",
        "",
        "Important caution:",
        "IuPetra is an investigation and anomaly-review tool. It does not issue official impact-risk predictions.",
        "Official hazard assessment should always be checked against NASA/JPL CNEOS Sentry and other official monitoring systems.",
        "",
    ]

    PATH_START_HERE_README.write_text("\n".join(lines), encoding="utf-8")
    return 1


def build_index_csv() -> int:
    rows = [
        {"folder": "reports/00_START_HERE", "file": "IuPetra_START_HERE.html", "purpose": "Visual dashboard for navigating the run.", "open_first": "yes"},
        {"folder": "reports/00_START_HERE", "file": "README_START_HERE.txt", "purpose": "Plain-language navigation guide for the whole run.", "open_first": "yes"},
        {"folder": "reports/00_START_HERE", "file": "top_candidate_packet.txt", "purpose": "Human-readable packet of top watchlist candidates, evidence, limitations, and next checks.", "open_first": "yes"},
        {"folder": "reports/00_START_HERE", "file": "REPORT_INDEX.csv", "purpose": "Map of where all organized reports live.", "open_first": "yes"},
        {"folder": "reports/01_EVIDENCE_REVIEW", "file": "watchlist_explained.csv", "purpose": "Detailed explanations for each watchlist candidate.", "open_first": "yes"},
        {"folder": "reports/01_EVIDENCE_REVIEW", "file": "research_questions.csv", "purpose": "Follow-up research questions for top candidates.", "open_first": "yes"},
        {"folder": "reports/02_PATTERN_FINDER", "file": "watchlist_candidates.csv", "purpose": "Combined pattern-finder candidate list.", "open_first": "no"},
        {"folder": "reports/02_PATTERN_FINDER", "file": "fireball_month_clusters.csv", "purpose": "Ranks months by fireball activity and energy.", "open_first": "no"},
        {"folder": "reports/02_PATTERN_FINDER", "file": "repeating_close_approach_objects.csv", "purpose": "Objects appearing multiple times in close-approach data.", "open_first": "no"},
        {"folder": "reports/02_PATTERN_FINDER", "file": "high_energy_fireball_windows.csv", "purpose": "Groups higher-energy fireballs into short windows.", "open_first": "no"},
        {"folder": "reports/02_PATTERN_FINDER", "file": "close_approach_windows.csv", "purpose": "Groups close asteroid/comet approaches into short windows.", "open_first": "no"},
        {"folder": "reports/03_ORBIT_CONTEXT", "file": "object_orbit_context.csv", "purpose": "JPL SBDB orbital context for selected cataloged objects.", "open_first": "no"},
        {"folder": "reports/03_ORBIT_CONTEXT", "file": "sentry_crosscheck.csv", "purpose": "Crosscheck against current fetched CNEOS Sentry table.", "open_first": "no"},
        {"folder": "reports/03_ORBIT_CONTEXT", "file": "candidate_orbit_review.csv", "purpose": "Joined review: candidate + orbit context + Sentry status.", "open_first": "yes"},
        {"folder": "reports/04_SUMMARIES", "file": "yearly_activity_index.csv", "purpose": "Relative yearly anomaly-hunting score.", "open_first": "no"},
        {"folder": "reports/04_SUMMARIES", "file": "fireball_yearly_summary.csv", "purpose": "Fireball counts and energy by year.", "open_first": "no"},
        {"folder": "reports/04_SUMMARIES", "file": "fireball_monthly_summary.csv", "purpose": "Fireball counts and energy by year/month.", "open_first": "no"},
        {"folder": "reports/04_SUMMARIES", "file": "largest_fireballs.csv", "purpose": "Largest fireball events in the fetched sample.", "open_first": "no"},
        {"folder": "reports/04_SUMMARIES", "file": "close_approach_yearly_summary.csv", "purpose": "Close-approach counts and extremes by year.", "open_first": "no"},
        {"folder": "reports/04_SUMMARIES", "file": "closest_approaches.csv", "purpose": "Closest approaches in the fetched sample.", "open_first": "no"},
        {"folder": "reports/04_SUMMARIES", "file": "fastest_close_approaches.csv", "purpose": "Fastest close approaches in the fetched sample.", "open_first": "no"},
        {"folder": "reports/04_SUMMARIES", "file": "sentry_summary.csv", "purpose": "Summary of fetched Sentry risk table.", "open_first": "no"},
        {"folder": "reports/99_TECHNICAL_LOGS", "file": "run_manifest.csv", "purpose": "Run settings, thresholds, API URLs, and warnings.", "open_first": "no"},
    ]

    write_csv(rows, ["folder", "file", "purpose", "open_first"], PATH_REPORT_INDEX)
    return len(rows)


def organize_reports_workspace() -> Dict[str, int]:
    return {
        "README_START_HERE.txt": build_readme_start_here(),
        "REPORT_INDEX.csv": build_index_csv(),
        "IuPetra_START_HERE.html": build_dashboard_html(),
    }

# ============================================================
# HTML DASHBOARD
# ============================================================

def read_first_rows(path: Path, limit: int = 8) -> List[Dict[str, str]]:
    return read_csv(path)[:limit]


def build_html_table(rows: List[Dict[str, str]], max_cols: int = 8) -> str:
    if not rows:
        return "<p class='muted'>No rows available for this table yet.</p>"

    headers = list(rows[0].keys())[:max_cols]
    header_html = "".join(f"<th>{html_escape(header)}</th>" for header in headers)

    body_lines = []
    for data_row in rows:
        cells = "".join(f"<td>{html_escape(data_row.get(header, ''))}</td>" for header in headers)
        body_lines.append(f"<tr>{cells}</tr>")

    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{''.join(body_lines)}</tbody></table>"


# ============================================================
# HTML REPORT VIEWERS
# ============================================================

def viewer_filename_for(path: Path) -> str:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", path.name)
    return f"{safe_name}.html"


def viewer_path_for(path: Path) -> Path:
    return HTML_VIEWERS_DIR / viewer_filename_for(path)


def dashboard_link_for(path: Path) -> str:
    """Dashboard lives in reports/00_START_HERE; link to HTML viewers when possible."""
    if path == SETTINGS_PATH:
        return "../../settings.json"

    if path.suffix.lower() in {".csv", ".txt"}:
        try:
            return viewer_path_for(path).relative_to(IMPORTANT_REPORTS_DIR).as_posix()
        except ValueError:
            return viewer_path_for(path).as_posix()

    try:
        return path.relative_to(IMPORTANT_REPORTS_DIR).as_posix()
    except ValueError:
        return path.as_posix()


def build_html_report_table(csv_path: Path, max_preview_rows: int = 500) -> str:
    rows = read_csv(csv_path)

    if not rows:
        return "<p class='empty'>No rows available in this report.</p>"

    headers = list(rows[0].keys())
    header_html = "".join(f"<th>{html_escape(header)}</th>" for header in headers)

    body_html_parts = []
    for data_row in rows[:max_preview_rows]:
        cells = "".join(f"<td>{html_escape(data_row.get(header, ''))}</td>" for header in headers)
        body_html_parts.append(f"<tr>{cells}</tr>")

    if len(rows) > max_preview_rows:
        body_html_parts.append(
            f"<tr><td colspan='{len(headers)}' class='truncated'>Showing first {max_preview_rows} of {len(rows)} rows. Open the raw CSV for the complete file.</td></tr>"
        )

    return f"<div class='table-wrap'><table><thead><tr>{header_html}</tr></thead><tbody>{''.join(body_html_parts)}</tbody></table></div>"


def build_text_report_view(txt_path: Path) -> str:
    if not txt_path.exists():
        return "<p class='empty'>Text report does not exist yet.</p>"

    text = txt_path.read_text(encoding="utf-8", errors="replace")
    return f"<pre>{html_escape(text)}</pre>"


def build_single_report_viewer(source_path: Path, title: str, description: str = "") -> int:
    HTML_VIEWERS_DIR.mkdir(parents=True, exist_ok=True)
    viewer_path = viewer_path_for(source_path)

    raw_href = ""
    try:
        raw_href = source_path.relative_to(HTML_VIEWERS_DIR).as_posix()
    except ValueError:
        # viewer is reports/HTML_VIEWERS, source is usually reports/<category>/file
        try:
            raw_href = "../" + source_path.relative_to(REPORTS_DIR).as_posix()
        except ValueError:
            raw_href = source_path.as_posix()

    if source_path.suffix.lower() == ".csv":
        content_html = build_html_report_table(source_path)
        type_label = "CSV Data Sheet"
    elif source_path.suffix.lower() == ".txt":
        content_html = build_text_report_view(source_path)
        type_label = "Text Report"
    else:
        content_html = "<p class='empty'>No viewer available for this file type.</p>"
        type_label = "Report"

    html_text = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{html_escape(title)} - IuPetra Viewer</title>
  <style>
    :root {{
      --void: #050403;
      --panel: #17100b;
      --panel2: #2a1710;
      --gold: #f4bd52;
      --amber: #d98736;
      --cream: #ffe8b9;
      --ivory: #fff6df;
      --muted: rgba(255, 232, 185, 0.72);
      --line: rgba(244, 189, 82, 0.28);
      --redspot: #b6402d;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--ivory);
      font-family: "Trebuchet MS", Arial, sans-serif;
      background:
        linear-gradient(180deg, rgba(255,232,185,0.05) 0 8%, rgba(106,63,37,0.20) 8% 19%, rgba(42,23,16,0.40) 19% 38%, rgba(215,111,46,0.12) 38% 48%, rgba(5,4,3,1) 48% 100%),
        #050403;
    }}
    header {{
      padding: 28px clamp(18px, 4vw, 54px);
      border-bottom: 1px solid var(--line);
      background: rgba(5,4,3,0.72);
      position: sticky;
      top: 0;
      z-index: 3;
      backdrop-filter: blur(10px);
    }}
    .topline {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
      justify-content: space-between;
    }}
    h1 {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--cream);
      font-size: clamp(1.8rem, 4vw, 3.2rem);
    }}
    .meta {{
      color: var(--muted);
      margin-top: 8px;
    }}
    .actions {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }}
    a.button {{
      color: #231005;
      background: linear-gradient(135deg, var(--gold), var(--amber));
      text-decoration: none;
      padding: 10px 14px;
      border-radius: 999px;
      font-weight: 800;
    }}
    a.button.secondary {{
      color: var(--ivory);
      background: rgba(5,4,3,0.36);
      border: 1px solid var(--line);
    }}
    main {{
      padding: 24px clamp(18px, 4vw, 54px) 60px;
    }}
    .viewer-panel {{
      border: 1px solid var(--line);
      border-radius: 22px;
      background: rgba(23,16,11,0.86);
      box-shadow: 0 24px 60px rgba(0,0,0,0.35);
      overflow: hidden;
    }}
    .table-wrap {{
      overflow: auto;
      max-height: 74vh;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.88rem;
      min-width: 900px;
    }}
    th, td {{
      border-bottom: 1px solid rgba(255,232,185,0.10);
      padding: 9px 10px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      position: sticky;
      top: 0;
      background: #2a1710;
      color: var(--gold);
      z-index: 2;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      font-size: 0.72rem;
    }}
    td {{
      color: var(--ivory);
    }}
    tr:hover td {{
      background: rgba(215,111,46,0.10);
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      padding: 22px;
      color: var(--ivory);
      font-family: Consolas, "Courier New", monospace;
      line-height: 1.5;
    }}
    .empty, .truncated {{
      color: var(--muted);
      padding: 22px;
    }}
  </style>
</head>
<body>
  <header>
    <div class="topline">
      <div>
        <h1>{html_escape(title)}</h1>
        <div class="meta">{html_escape(type_label)} · {html_escape(description)} · Source: {html_escape(source_path.name)}</div>
      </div>
      <div class="actions">
        <a class="button" href="../00_START_HERE/IuPetra_START_HERE.html">Dashboard</a>
        <a class="button secondary" href="{html_escape(raw_href)}">Open raw file</a>
      </div>
    </div>
  </header>
  <main>
    <section class="viewer-panel">
      {content_html}
    </section>
  </main>
</body>
</html>"""

    viewer_path.write_text(html_text, encoding="utf-8")
    return 1


def build_all_report_viewers() -> int:
    report_specs = [
        (PATH_TOP_CANDIDATE_PACKET, "Top Candidate Packet", "Human-readable top candidate summary"),
        (PATH_REPORT_INDEX, "Report Index", "Map of every report"),
        (PATH_WATCHLIST_EXPLAINED, "Watchlist Explained", "Evidence review table"),
        (PATH_RESEARCH_QUESTIONS, "Research Questions", "Follow-up research questions"),
        (PATH_WATCHLIST_CANDIDATES, "Watchlist Candidates", "Pattern-finder watchlist"),
        (PATH_FIREBALL_MONTH_CLUSTERS, "Fireball Month Clusters", "Recurring monthly fireball activity"),
        (PATH_REPEATING_CLOSE_APPROACH_OBJECTS, "Repeating Close-Approach Objects", "Repeat visitors in close-approach data"),
        (PATH_HIGH_ENERGY_FIREBALL_WINDOWS, "High-Energy Fireball Windows", "Short windows of higher-energy fireballs"),
        (PATH_CLOSE_APPROACH_WINDOWS, "Close-Approach Windows", "Short windows of close approaches"),
        (PATH_CANDIDATE_ORBIT_REVIEW, "Candidate Orbit Review", "Candidate plus orbit and Sentry context"),
        (PATH_OBJECT_ORBIT_CONTEXT, "Object Orbit Context", "SBDB object enrichment"),
        (PATH_SENTRY_CROSSCHECK, "Sentry Crosscheck", "Fetched Sentry matching status"),
        (PATH_YEARLY_ACTIVITY_INDEX, "Yearly Activity Index", "Relative anomaly-hunting score"),
        (PATH_FIREBALL_YEARLY_SUMMARY, "Fireball Yearly Summary", "Fireball counts and energy by year"),
        (PATH_FIREBALL_MONTHLY_SUMMARY, "Fireball Monthly Summary", "Fireball counts and energy by month"),
        (PATH_LARGEST_FIREBALLS, "Largest Fireballs", "Largest fireballs in fetched sample"),
        (PATH_CLOSE_APPROACH_YEARLY_SUMMARY, "Close-Approach Yearly Summary", "Close approach yearly counts and extremes"),
        (PATH_CLOSEST_APPROACHES, "Closest Approaches", "Closest approaches in fetched sample"),
        (PATH_FASTEST_CLOSE_APPROACHES, "Fastest Close Approaches", "Fastest close approaches in fetched sample"),
        (PATH_SENTRY_SUMMARY, "Sentry Summary", "Summary of fetched Sentry table"),
        (PATH_RUN_MANIFEST, "Run Manifest", "Settings, thresholds, and API metadata"),
    ]

    count = 0
    for source_path, title, description in report_specs:
        count += build_single_report_viewer(source_path, title, description)

    return count

def build_dashboard_html() -> int:
    generated_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    build_all_report_viewers()

    css_path = IMPORTANT_REPORTS_DIR / "iupetra-dashboard.css"
    css_path.write_text(':root {\n  --void:#050403; --space:#09080d; --black-brown:#17100b; --band-dark:#2a1710;\n  --band-brown:#6a3f25; --band-copper:#9d4f2e; --band-tan:#c79b62;\n  --cream:#ffe8b9; --ivory:#fff6df; --gold:#f4bd52; --amber:#d98736;\n  --orange:#d76f2e; --rust:#9d3f25; --redspot:#b6402d; --redspot-deep:#5f1c1a;\n  --muted:rgba(255,232,185,.72); --line:rgba(244,189,82,.3);\n  --line-hot:rgba(215,111,46,.72); --shadow:rgba(0,0,0,.5);\n}\n*{box-sizing:border-box} html{scroll-behavior:smooth}\nbody{margin:0;min-height:100vh;color:var(--ivory);font-family:"Trebuchet MS",Arial,sans-serif;background:radial-gradient(circle at 68% 18%,rgba(182,64,45,.22),transparent 18%),linear-gradient(180deg,#030303 0%,#0c0907 42%,#050403 100%);overflow-x:hidden}\n.jovian-atmosphere{position:fixed;inset:0;z-index:-3;background:linear-gradient(180deg,rgba(255,232,185,.05) 0 7%,rgba(106,63,37,.24) 7% 15%,rgba(199,155,98,.17) 15% 22%,rgba(42,23,16,.32) 22% 32%,rgba(215,111,46,.2) 32% 41%,rgba(255,246,223,.1) 41% 46%,rgba(95,28,26,.22) 46% 58%,rgba(244,189,82,.13) 58% 65%,rgba(106,63,37,.26) 65% 74%,rgba(23,16,11,.72) 74% 100%)}\n.jovian-atmosphere:after{content:"";position:absolute;inset:0;background:repeating-linear-gradient(96deg,transparent 0 46px,rgba(255,246,223,.04) 47px 51px,transparent 52px 92px),radial-gradient(ellipse at 70% 31%,rgba(182,64,45,.78) 0 4%,rgba(182,64,45,.35) 5% 10%,transparent 11%);opacity:.9}\n.app-shell{min-height:100vh;display:grid;grid-template-columns:112px minmax(0,1fr)}\n.left-rail{border-right:1px solid var(--line);background:linear-gradient(180deg,rgba(5,4,3,.94),rgba(42,23,16,.76));padding:22px 14px;position:sticky;top:0;height:100vh;display:flex;flex-direction:column;align-items:center;gap:16px}\n.brand-mark{width:70px;height:70px;border-radius:24px;display:grid;place-items:center;color:var(--cream);font-family:Georgia,serif;font-size:1.6rem;border:1px solid var(--line-hot);background:radial-gradient(circle at 68% 40%,var(--redspot) 0 12%,transparent 13%),linear-gradient(180deg,var(--band-tan),var(--band-brown) 42%,var(--black-brown));box-shadow:0 0 24px rgba(244,189,82,.24)}\n.rail-nav{width:100%;display:grid;gap:10px}.rail-nav a{min-height:58px;border:1px solid rgba(244,189,82,.18);border-radius:18px;color:var(--muted);text-decoration:none;display:grid;place-items:center;text-align:center;font-size:.7rem;padding:8px;background:rgba(5,4,3,.42)}\n.rail-nav a:hover{color:var(--ivory);border-color:var(--line-hot);background:rgba(215,111,46,.18)}\n.rail-footer{margin-top:auto;color:rgba(255,232,185,.48);writing-mode:vertical-rl;text-orientation:mixed;letter-spacing:.18em;font-size:.68rem;display:flex;gap:12px}\n.main-deck{padding:28px clamp(18px,3.4vw,52px) 58px}\n.hero-panel{min-height:560px;display:grid;grid-template-columns:minmax(0,.96fr) minmax(440px,1.04fr);gap:32px;align-items:center;border:1px solid var(--line);border-radius:34px;padding:clamp(26px,4vw,54px);background:radial-gradient(circle at top left,rgba(244,189,82,.12),transparent 35%),linear-gradient(135deg,rgba(23,16,11,.92),rgba(8,6,5,.78));box-shadow:0 30px 80px var(--shadow),inset 0 1px 0 rgba(255,246,223,.12);overflow:hidden;position:relative}\n.hero-panel:before{content:"";position:absolute;inset:-30%;background:conic-gradient(from 120deg,transparent,rgba(244,189,82,.08),transparent,rgba(182,64,45,.12),transparent);opacity:.75;animation:slowSpin 40s linear infinite}\n.hero-copy,.jupiter-system{position:relative;z-index:1}.eyebrow{margin:0 0 12px;color:var(--gold);text-transform:uppercase;letter-spacing:.19em;font-size:.78rem}\nh1{margin:0;max-width:860px;font-size:clamp(3rem,7.5vw,7.2rem);line-height:.88;text-transform:uppercase;letter-spacing:.025em;font-family:Georgia,"Times New Roman",serif;text-shadow:0 0 26px rgba(244,189,82,.3),0 8px 0 rgba(0,0,0,.35)}\n.hero-text{max-width:760px;color:var(--muted);font-size:1.08rem}.generated-stamp{color:rgba(255,232,185,.52);font-size:.88rem}\n.hero-actions{display:flex;flex-wrap:wrap;gap:14px;margin-top:28px}.primary-action,.secondary-action,.panel-link{display:inline-flex;align-items:center;justify-content:center;min-height:46px;padding:0 18px;border-radius:999px;text-decoration:none;font-weight:700}\n.primary-action{color:#241005;background:linear-gradient(135deg,var(--gold),var(--amber));box-shadow:0 0 22px rgba(244,189,82,.25)}.secondary-action,.panel-link{color:var(--ivory);border:1px solid var(--line-hot);background:rgba(5,4,3,.36)}\n.jupiter-system{min-height:520px;display:grid;place-items:center}.jupiter{width:min(470px,80vw);aspect-ratio:1/1;border-radius:50%;position:relative;overflow:hidden;background:linear-gradient(180deg,#ead0a0 0 8%,#6a3f25 9% 16%,#fff0c7 17% 25%,#9d4f2e 26% 36%,#f4bd52 37% 46%,#301910 47% 56%,#d98736 57% 66%,#ffe8b9 67% 75%,#6a3f25 76% 88%,#17100b 89% 100%);box-shadow:inset -42px -28px 75px rgba(0,0,0,.66),inset 28px 18px 42px rgba(255,246,223,.18),0 0 88px rgba(244,189,82,.32);border:1px solid rgba(255,246,223,.26)}\n.jupiter:before{content:"";position:absolute;inset:8%;border-radius:50%;background:repeating-linear-gradient(176deg,transparent 0 16px,rgba(255,255,255,.12) 17px 22px,transparent 23px 42px);opacity:.8}\n.great-red-spot{position:absolute;width:32%;height:16%;right:17%;top:42%;border-radius:50%;background:radial-gradient(ellipse at center,#ffd1a2 0 8%,var(--redspot) 9% 38%,var(--redspot-deep) 39% 72%,rgba(95,28,26,.18) 73%);box-shadow:0 0 22px rgba(182,64,45,.58);transform:rotate(-8deg)}\n.orbit{position:absolute;border:1px solid rgba(244,189,82,.16);border-radius:50%}.orbit-one{width:72%;height:72%}.orbit-two{width:92%;height:92%}.orbit-three{width:110%;height:110%}\n.moon{position:absolute;width:13px;height:13px;border-radius:50%;background:var(--cream);box-shadow:0 0 14px rgba(255,232,185,.8)}.moon-one{transform:translate(265px,-180px)}.moon-two{transform:translate(-285px,72px);width:9px;height:9px}.moon-three{transform:translate(315px,166px);width:11px;height:11px}\n.quick-stats{margin:26px 0;display:grid;grid-template-columns:repeat(3,1fr);gap:18px}.quick-stats article,.zone-card,.redspot-core,.redspot-ring,.caution-panel,.report-bands{border:1px solid var(--line);border-radius:24px;background:linear-gradient(180deg,rgba(23,16,11,.9),rgba(8,6,5,.76));box-shadow:0 18px 52px rgba(0,0,0,.32),inset 0 1px 0 rgba(255,246,223,.08)}\n.quick-stats article{padding:20px}.stat-label{color:var(--gold);text-transform:uppercase;font-size:.73rem;letter-spacing:.14em}.quick-stats strong{display:block;margin-top:8px;font-size:1.25rem}.quick-stats p,.zone-card p,.redspot-core p,.caution-panel p{color:var(--muted)}\n.redspot-layout{display:grid;grid-template-columns:.9fr 1.1fr;gap:20px;margin:26px 0}.redspot-core{padding:28px;position:relative;overflow:hidden}.redspot-core:after{content:"";position:absolute;width:240px;height:130px;right:-46px;bottom:-38px;border-radius:50%;background:radial-gradient(ellipse at center,#ffd1a2 0 8%,var(--redspot) 9% 42%,var(--redspot-deep) 43% 72%,transparent 73%);opacity:.62;transform:rotate(-12deg)}\n.redspot-core h2,.report-bands h2,.zone-card h2{margin:0;color:var(--cream);font-family:Georgia,"Times New Roman",serif;font-size:clamp(1.55rem,3vw,2.7rem)}\n.redspot-ring{padding:18px;display:grid;gap:14px}.redspot-ring a{display:grid;grid-template-columns:minmax(140px,.5fr) 1fr;gap:18px;align-items:center;min-height:96px;padding:18px;border-radius:20px;color:var(--ivory);text-decoration:none;background:linear-gradient(90deg,rgba(157,63,37,.32),rgba(244,189,82,.08)),rgba(5,4,3,.28);border:1px solid rgba(244,189,82,.18)}\n.redspot-ring a:hover,.link-list a:hover,.band-row:hover{border-color:var(--line-hot);background:rgba(215,111,46,.18)}.redspot-ring strong{color:var(--gold);font-size:1.1rem}.redspot-ring span{color:var(--muted)}\n.zone-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:20px;margin:26px 0}.zone-card{padding:24px}.large-card{grid-row:span 2}.zone-header{display:flex;align-items:flex-start;gap:16px}\n.zone-number{width:54px;height:54px;border-radius:18px;display:grid;place-items:center;color:var(--gold);border:1px solid var(--line-hot);background:rgba(5,4,3,.42);font-weight:800}\n.link-list{display:grid;gap:10px;margin-top:18px}.link-list a{color:var(--cream);text-decoration:none;border:1px solid rgba(244,189,82,.14);border-radius:14px;padding:11px 13px;background:rgba(5,4,3,.32)}\n.report-bands{margin:26px 0;padding:24px}.band-list{display:grid;gap:12px;margin-top:18px}.band-row{min-height:82px;display:grid;grid-template-columns:68px minmax(160px,.5fr) 1fr;gap:18px;align-items:center;padding:14px 18px;border-radius:20px;color:var(--ivory);text-decoration:none;border:1px solid rgba(244,189,82,.18);background:linear-gradient(90deg,rgba(5,4,3,.44),rgba(106,63,37,.24))}\n.band-row:hover{transform:translateX(4px)}.band-row span{width:48px;height:48px;border-radius:16px;display:grid;place-items:center;color:var(--gold);background:rgba(5,4,3,.44);border:1px solid rgba(244,189,82,.18);font-weight:800}.band-row strong{color:var(--cream)}.band-row em{color:var(--muted);font-style:normal}\n.caution-panel{padding:22px 24px;border-left:6px solid var(--redspot)}.caution-panel strong{color:var(--gold)}\n@keyframes slowSpin{to{transform:rotate(360deg)}}\n@media(max-width:1080px){.app-shell{grid-template-columns:1fr}.left-rail{position:static;height:auto;flex-direction:row;justify-content:space-between;padding:14px}.rail-nav{grid-template-columns:repeat(5,1fr);width:auto;flex:1}.rail-footer{display:none}.hero-panel,.redspot-layout,.zone-grid{grid-template-columns:1fr}.quick-stats{grid-template-columns:1fr}.jupiter-system{min-height:420px}}\n@media(max-width:680px){.main-deck{padding:18px}.hero-panel{min-height:auto;padding:24px}.rail-nav{display:none}.jupiter{width:min(320px,86vw)}.band-row,.redspot-ring a{grid-template-columns:1fr}}\n', encoding="utf-8")

    def link(path: Path) -> str:
        return html_escape(dashboard_link_for(path))

    watchlist_count = count_rows(PATH_WATCHLIST_CANDIDATES)
    orbit_count = count_rows(PATH_CANDIDATE_ORBIT_REVIEW)
    question_count = count_rows(PATH_RESEARCH_QUESTIONS)
    fireball_count = count_rows(DATA_CLEAN_DIR / "fireballs_clean.csv")
    approach_count = count_rows(DATA_CLEAN_DIR / "close_approaches_clean.csv")
    sentry_count = count_rows(DATA_CLEAN_DIR / "sentry_risk_clean.csv")

    html_text = '<!DOCTYPE html>\n<html lang="en">\n<head>\n  <meta charset="UTF-8" />\n  <meta name="viewport" content="width=device-width, initial-scale=1.0" />\n  <title>IuPetra</title>\n  <link rel="stylesheet" href="iupetra-dashboard.css" />\n</head>\n<body>\n  <div class="jovian-atmosphere" aria-hidden="true"></div>\n  <div class="app-shell">\n    <aside class="left-rail">\n      <div class="brand-mark" aria-label="IuPetra">IP</div>\n      <nav class="rail-nav" aria-label="IuPetra dashboard navigation">\n        <a href="#command">Command</a>\n        <a href="#redspot">Lead</a>\n        <a href="#evidence">Evidence</a>\n        <a href="#orbit">Orbit</a>\n        <a href="#reports">Reports</a>\n      </nav>\n      <div class="rail-footer"><span>GROUNDSTATE</span><span>IUPETRA</span></div>\n    </aside>\n\n    <main class="main-deck">\n      <section id="command" class="hero-panel">\n        <div class="hero-copy">\n          <p class="eyebrow">Groundstate Technology</p>\n          <h1>IuPetra</h1>\n          <p class="hero-text">\n            This run pulled __FIREBALL_COUNT__ fireball rows, __APPROACH_COUNT__ close-approach rows,\n            and __SENTRY_COUNT__ Sentry rows. IuPetra found __WATCHLIST_COUNT__ watchlist candidates,\n            built __ORBIT_COUNT__ orbit-review rows, and generated __QUESTION_COUNT__ follow-up research questions.\n          </p>\n          <p class="generated-stamp">Generated __GENERATED_UTC__ · __SETTINGS_LINE__</p>\n          <div class="hero-actions">\n            <a class="primary-action" href="__TOP_PACKET_LINK__">Read the run packet</a>\n            <a class="secondary-action" href="__REPORT_INDEX_LINK__">Open report index</a>\n          </div>\n        </div>\n        <div class="jupiter-system" aria-label="Stylized Jupiter system">\n          <div class="orbit orbit-one"></div><div class="orbit orbit-two"></div><div class="orbit orbit-three"></div>\n          <div class="jupiter"><div class="great-red-spot"></div></div>\n          <span class="moon moon-one"></span><span class="moon moon-two"></span><span class="moon moon-three"></span>\n        </div>\n      </section>\n\n      <section class="quick-stats" aria-label="Run highlights">\n        <article><span class="stat-label">Top lead</span><strong>__TOP_LINE__</strong><p>Open the packet for the complete explanation and limitations.</p></article>\n        <article><span class="stat-label">Orbit review</span><strong>__ORBIT_LINE__</strong><p>Object context is shown only where catalog data is available.</p></article>\n        <article><span class="stat-label">Controls</span><strong>settings.json</strong><p>__SETTINGS_LINE__</p></article>\n      </section>\n\n      <section id="redspot" class="redspot-layout">\n        <div class="redspot-core">\n          <p class="eyebrow">Great Red Spot</p>\n          <h2>Primary lead from this run</h2>\n          <p>__TOP_LINE__ The packet is the cleanest starting point because it summarizes evidence, limitations, and what to check next.</p>\n          <a class="panel-link" href="__TOP_PACKET_LINK__">Read the packet</a>\n        </div>\n        <div class="redspot-ring">\n          <a href="__WATCHLIST_EXPLAINED_LINK__"><strong>Evidence Vault</strong><span>__WATCHLIST_COUNT__ explained candidates</span></a>\n          <a href="__CANDIDATE_ORBIT_REVIEW_LINK__"><strong>Orbital Tribunal</strong><span>__ORBIT_COUNT__ orbit-review rows</span></a>\n          <a href="__RESEARCH_QUESTIONS_LINK__"><strong>Question Forge</strong><span>__QUESTION_COUNT__ generated research questions</span></a>\n        </div>\n      </section>\n\n      <section id="evidence" class="zone-grid">\n        <article class="zone-card large-card">\n          <div class="zone-header"><span class="zone-number">01</span><h2>Evidence Review</h2></div>\n          <p>Use this section to see why a candidate was flagged, what supports it, and what weakens the case.</p>\n          <div class="link-list">\n            <a href="__WATCHLIST_EXPLAINED_LINK__">watchlist_explained.csv viewer</a>\n            <a href="__RESEARCH_QUESTIONS_LINK__">research_questions.csv viewer</a>\n            <a href="__TOP_PACKET_LINK__">top_candidate_packet.txt viewer</a>\n          </div>\n        </article>\n        <article id="orbit" class="zone-card">\n          <div class="zone-header"><span class="zone-number">02</span><h2>Orbit Context</h2></div>\n          <p>__ORBIT_LINE__</p>\n          <div class="link-list">\n            <a href="__CANDIDATE_ORBIT_REVIEW_LINK__">candidate_orbit_review.csv viewer</a>\n            <a href="__OBJECT_ORBIT_CONTEXT_LINK__">object_orbit_context.csv viewer</a>\n            <a href="__SENTRY_CROSSCHECK_LINK__">sentry_crosscheck.csv viewer</a>\n          </div>\n        </article>\n        <article class="zone-card">\n          <div class="zone-header"><span class="zone-number">03</span><h2>Pattern Finder</h2></div>\n          <p>These sheets are the machinery behind the watchlist: repeated months, short windows, and repeat visitors.</p>\n          <div class="link-list">\n            <a href="__WATCHLIST_CANDIDATES_LINK__">watchlist_candidates.csv viewer</a>\n            <a href="__FIREBALL_MONTH_CLUSTERS_LINK__">fireball_month_clusters.csv viewer</a>\n            <a href="__REPEATING_OBJECTS_LINK__">repeating_close_approach_objects.csv viewer</a>\n            <a href="__HIGH_ENERGY_WINDOWS_LINK__">high_energy_fireball_windows.csv viewer</a>\n            <a href="__CLOSE_APPROACH_WINDOWS_LINK__">close_approach_windows.csv viewer</a>\n          </div>\n        </article>\n      </section>\n\n      <section id="reports" class="report-bands">\n        <div class="band-title"><p class="eyebrow">Archive Bands</p><h2>Report zones</h2></div>\n        <div class="band-list">\n          <a class="band-row start" href="__REPORT_INDEX_LINK__"><span>00</span><strong>Start Here</strong><em>Dashboard, packet, and index</em></a>\n          <a class="band-row evidence" href="__WATCHLIST_EXPLAINED_LINK__"><span>01</span><strong>Evidence Review</strong><em>__WATCHLIST_COUNT__ explained candidates</em></a>\n          <a class="band-row pattern" href="__WATCHLIST_CANDIDATES_LINK__"><span>02</span><strong>Pattern Finder</strong><em>Clusters, windows, repeat visitors</em></a>\n          <a class="band-row orbit" href="__CANDIDATE_ORBIT_REVIEW_LINK__"><span>03</span><strong>Orbit Context</strong><em>__ORBIT_COUNT__ orbit-review rows</em></a>\n          <a class="band-row summary" href="__YEARLY_ACTIVITY_INDEX_LINK__"><span>04</span><strong>Summaries</strong><em>__FIREBALL_COUNT__ fireballs · __APPROACH_COUNT__ approaches</em></a>\n          <a class="band-row logs" href="__RUN_MANIFEST_LINK__"><span>99</span><strong>Technical Logs</strong><em>Settings, thresholds, run manifest</em></a>\n        </div>\n      </section>\n\n      <section class="zone-grid">\n        <article class="zone-card">\n          <div class="zone-header"><span class="zone-number">04</span><h2>Summary Tables</h2></div>\n          <div class="link-list">\n            <a href="__YEARLY_ACTIVITY_INDEX_LINK__">yearly_activity_index.csv viewer</a>\n            <a href="__FIREBALL_YEARLY_SUMMARY_LINK__">fireball_yearly_summary.csv viewer</a>\n            <a href="__FIREBALL_MONTHLY_SUMMARY_LINK__">fireball_monthly_summary.csv viewer</a>\n            <a href="__LARGEST_FIREBALLS_LINK__">largest_fireballs.csv viewer</a>\n            <a href="__CLOSE_APPROACH_YEARLY_SUMMARY_LINK__">close_approach_yearly_summary.csv viewer</a>\n            <a href="__CLOSEST_APPROACHES_LINK__">closest_approaches.csv viewer</a>\n            <a href="__FASTEST_APPROACHES_LINK__">fastest_close_approaches.csv viewer</a>\n            <a href="__SENTRY_SUMMARY_LINK__">sentry_summary.csv viewer</a>\n          </div>\n        </article>\n        <article class="zone-card">\n          <div class="zone-header"><span class="zone-number">⚙</span><h2>Controls + Logs</h2></div>\n          <div class="link-list">\n            <a href="__SETTINGS_LINK__">settings.json</a>\n            <a href="__RUN_MANIFEST_LINK__">run_manifest.csv viewer</a>\n            <a href="__README_START_LINK__">README_START_HERE.txt viewer</a>\n          </div>\n        </article>\n      </section>\n\n      <section class="caution-panel">\n        <strong>Boundary note</strong>\n        <p>IuPetra highlights leads for review. It does not issue impact predictions. Use the Sentry crosscheck and official NASA/JPL CNEOS sources before treating any candidate as risk-significant.</p>\n      </section>\n    </main>\n  </div>\n</body>\n <footer>IuPetra · Built by Groundstate Technology · Turning public celestial data into local investigative intelligence.</footer>\n </html>\n'
    replacements = {
        "__GENERATED_UTC__": html_escape(generated_utc),
        "__FIREBALL_COUNT__": format_count(fireball_count),
        "__APPROACH_COUNT__": format_count(approach_count),
        "__SENTRY_COUNT__": format_count(sentry_count),
        "__WATCHLIST_COUNT__": format_count(watchlist_count),
        "__ORBIT_COUNT__": format_count(orbit_count),
        "__QUESTION_COUNT__": format_count(question_count),
        "__TOP_LINE__": html_escape(top_candidate_line()),
        "__ORBIT_LINE__": html_escape(orbit_review_line()),
        "__SETTINGS_LINE__": html_escape(settings_summary_line()),
        "__TOP_PACKET_LINK__": link(PATH_TOP_CANDIDATE_PACKET),
        "__REPORT_INDEX_LINK__": link(PATH_REPORT_INDEX),
        "__WATCHLIST_EXPLAINED_LINK__": link(PATH_WATCHLIST_EXPLAINED),
        "__RESEARCH_QUESTIONS_LINK__": link(PATH_RESEARCH_QUESTIONS),
        "__CANDIDATE_ORBIT_REVIEW_LINK__": link(PATH_CANDIDATE_ORBIT_REVIEW),
        "__OBJECT_ORBIT_CONTEXT_LINK__": link(PATH_OBJECT_ORBIT_CONTEXT),
        "__SENTRY_CROSSCHECK_LINK__": link(PATH_SENTRY_CROSSCHECK),
        "__WATCHLIST_CANDIDATES_LINK__": link(PATH_WATCHLIST_CANDIDATES),
        "__FIREBALL_MONTH_CLUSTERS_LINK__": link(PATH_FIREBALL_MONTH_CLUSTERS),
        "__REPEATING_OBJECTS_LINK__": link(PATH_REPEATING_CLOSE_APPROACH_OBJECTS),
        "__HIGH_ENERGY_WINDOWS_LINK__": link(PATH_HIGH_ENERGY_FIREBALL_WINDOWS),
        "__CLOSE_APPROACH_WINDOWS_LINK__": link(PATH_CLOSE_APPROACH_WINDOWS),
        "__YEARLY_ACTIVITY_INDEX_LINK__": link(PATH_YEARLY_ACTIVITY_INDEX),
        "__RUN_MANIFEST_LINK__": link(PATH_RUN_MANIFEST),
        "__FIREBALL_YEARLY_SUMMARY_LINK__": link(PATH_FIREBALL_YEARLY_SUMMARY),
        "__FIREBALL_MONTHLY_SUMMARY_LINK__": link(PATH_FIREBALL_MONTHLY_SUMMARY),
        "__LARGEST_FIREBALLS_LINK__": link(PATH_LARGEST_FIREBALLS),
        "__CLOSE_APPROACH_YEARLY_SUMMARY_LINK__": link(PATH_CLOSE_APPROACH_YEARLY_SUMMARY),
        "__CLOSEST_APPROACHES_LINK__": link(PATH_CLOSEST_APPROACHES),
        "__FASTEST_APPROACHES_LINK__": link(PATH_FASTEST_CLOSE_APPROACHES),
        "__SENTRY_SUMMARY_LINK__": link(PATH_SENTRY_SUMMARY),
        "__SETTINGS_LINK__": link(SETTINGS_PATH),
        "__README_START_LINK__": link(PATH_START_HERE_README),
    }

    for key, value in replacements.items():
        html_text = html_text.replace(key, value)

    PATH_DASHBOARD_HTML.parent.mkdir(parents=True, exist_ok=True)
    PATH_DASHBOARD_HTML.write_text(html_text, encoding="utf-8")
    return 1


def build_run_manifest(
    fireball_count: int,
    close_approach_count: int,
    sentry_count: int,
) -> int:
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    rows = [
        {"field": "script_version", "value": "IuPetra v1.3.1"},
        {"field": "run_time_utc", "value": now_utc},
        {"field": "fireball_limit", "value": FIREBALL_LIMIT},
        {"field": "close_approach_date_min", "value": CLOSE_APPROACH_DATE_MIN},
        {"field": "close_approach_date_max", "value": CLOSE_APPROACH_DATE_MAX},
        {"field": "close_approach_distance_max_au", "value": CLOSE_APPROACH_DISTANCE_MAX_AU},
        {"field": "close_approach_limit", "value": CLOSE_APPROACH_LIMIT},
        {"field": "top_report_limit", "value": TOP_REPORT_LIMIT},
        {"field": "high_energy_fireball_kt_threshold", "value": HIGH_ENERGY_FIREBALL_KT_THRESHOLD},
        {"field": "high_energy_window_days", "value": HIGH_ENERGY_WINDOW_DAYS},
        {"field": "close_approach_window_days", "value": CLOSE_APPROACH_WINDOW_DAYS},
        {"field": "close_approach_cluster_distance_au", "value": CLOSE_APPROACH_CLUSTER_DISTANCE_AU},
        {"field": "repeat_object_min_count", "value": REPEAT_OBJECT_MIN_COUNT},
        {"field": "watchlist_min_score", "value": WATCHLIST_MIN_SCORE},
        {"field": "top_candidate_packet_limit", "value": TOP_CANDIDATE_PACKET_LIMIT},
        {"field": "fireball_rows_saved", "value": fireball_count},
        {"field": "close_approach_rows_saved", "value": close_approach_count},
        {"field": "sentry_rows_saved", "value": sentry_count},
        {"field": "settings_loaded_keys", "value": ", ".join(sorted(SETTINGS.keys()))},
        {"field": "fireball_api_url", "value": FIREBALL_API_URL},
        {"field": "close_approach_api_url", "value": CLOSE_APPROACH_API_URL},
        {"field": "sentry_api_url", "value": SENTRY_API_URL},
        {"field": "sbdb_api_url", "value": SBDB_API_URL},
        {"field": "sbdb_enrichment_limit", "value": SBDB_ENRICHMENT_LIMIT},
        {"field": "activity_score_warning", "value": "Relative anomaly-hunting score only. It is not a formal impact-risk metric."},
        {"field": "watchlist_warning", "value": "Pattern-finder candidates only. These are not official hazard predictions."},
        {"field": "evidence_review_warning", "value": "Evidence review explains why a candidate was flagged; it does not validate a causal hypothesis."},
        {"field": "orbit_context_warning", "value": "SBDB enrichment is a context lookup. It does not replace official risk analysis."},
        {"field": "workspace_organization", "value": "Reports are written directly into categorized subfolders. Root reports/ is only a container."},
        {"field": "dashboard_html", "value": str(PATH_DASHBOARD_HTML)},
    ]

    write_csv(rows, RUN_MANIFEST_HEADERS, PATH_RUN_MANIFEST)
    return len(rows)


def build_reports() -> Dict[str, int]:
    report_counts = {
        "fireball_yearly_summary.csv": build_step("fireball_yearly_summary.csv", build_fireball_yearly_summary),
        "fireball_monthly_summary.csv": build_step("fireball_monthly_summary.csv", build_fireball_monthly_summary),
        "largest_fireballs.csv": build_step("largest_fireballs.csv", build_largest_fireballs),
        "close_approach_yearly_summary.csv": build_step("close_approach_yearly_summary.csv", build_close_approach_yearly_summary),
        "closest_approaches.csv": build_step("closest_approaches.csv", build_closest_approaches),
        "fastest_close_approaches.csv": build_step("fastest_close_approaches.csv", build_fastest_approaches),
        "sentry_summary.csv": build_step("sentry_summary.csv", build_sentry_summary),
        "yearly_activity_index.csv": build_step("yearly_activity_index.csv", build_yearly_activity_index),
        "fireball_month_clusters.csv": build_step("fireball_month_clusters.csv", build_fireball_month_clusters),
        "repeating_close_approach_objects.csv": build_step("repeating_close_approach_objects.csv", build_repeating_close_approach_objects),
        "high_energy_fireball_windows.csv": build_step("high_energy_fireball_windows.csv", build_high_energy_fireball_windows),
        "close_approach_windows.csv": build_step("close_approach_windows.csv", build_close_approach_windows),
        "watchlist_candidates.csv": build_step("watchlist_candidates.csv", build_watchlist_candidates),
        "watchlist_explained.csv": build_step("watchlist_explained.csv", build_watchlist_explained),
        "research_questions.csv": build_step("research_questions.csv", build_research_questions),
        "object_orbit_context.csv": build_step("object_orbit_context.csv", build_object_orbit_context),
        "sentry_crosscheck.csv": build_step("sentry_crosscheck.csv", build_sentry_crosscheck),
        "candidate_orbit_review.csv": build_step("candidate_orbit_review.csv", build_candidate_orbit_review),
        "top_candidate_packet.txt": build_step("top_candidate_packet.txt", build_top_candidate_packet),
    }

    return report_counts


# ============================================================
# MAIN
# ============================================================

def main() -> int:
    try:
        ensure_dirs()

        print("IuPetra v1.3.1.1 - Stability + Dashboard")
        print("------------------------------------")

        fireball_count = fetch_step("Fetching CNEOS fireballs...", fetch_fireballs)
        close_approach_count = fetch_step("Fetching JPL close approaches...", fetch_close_approaches)
        sentry_count = fetch_step("Fetching CNEOS Sentry risk table...", fetch_sentry)

        print("Building reports...")
        report_counts = build_reports()
        build_run_manifest(fireball_count, close_approach_count, sentry_count)

        print("Writing navigation files...")
        organization_counts = organize_reports_workspace()
        report_counts.update(organization_counts)

        for report_name, row_count in report_counts.items():
            print(f"  {report_name}: {row_count} rows")

        print("")
        print("DONE")
        print(f"Raw JSON:   {DATA_RAW_DIR}")
        print(f"Clean CSV:  {DATA_CLEAN_DIR}")
        print(f"Reports:    {REPORTS_DIR}")
        print("")
        print("Start here:")
        print(f"  {PATH_DASHBOARD_HTML}")
        print(f"  {PATH_START_HERE_README}")
        print(f"  {PATH_TOP_CANDIDATE_PACKET}")
        print(f"  {PATH_REPORT_INDEX}")
        print("")
        print("No-code controls:")
        print(f"  {SETTINGS_PATH}")

        return 0

    except Exception as exc:
        print("")
        print("ERROR")
        print(str(exc))
        print("")
        print("Troubleshooting:")
        print("1. Make sure you are connected to the internet.")
        print("2. Make sure Windows Defender/Firewall is not blocking Python.")
        print("3. Try running from inside the folder with: python iupetra.py")

        return 1


if __name__ == "__main__":
    raise SystemExit(main())
