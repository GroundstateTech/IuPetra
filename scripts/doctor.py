#!/usr/bin/env python3
"""IuPetra environment and configuration preflight.

Default mode is offline-safe and suitable for CI. Use --network to also verify
that the configured NASA/JPL endpoints are reachable.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SETTINGS_PATH = ROOT / "settings.json"

REQUIRED_SETTINGS: dict[str, type] = {
    "fireball_limit": int,
    "close_approach_date_min": str,
    "close_approach_date_max": str,
    "close_approach_distance_max_au": (str, int, float),
    "close_approach_limit": int,
    "top_report_limit": int,
    "high_energy_fireball_kt_threshold": (int, float),
    "high_energy_window_days": int,
    "close_approach_window_days": int,
    "close_approach_cluster_distance_au": (int, float),
    "repeat_object_min_count": int,
    "watchlist_min_score": (int, float),
    "top_candidate_packet_limit": int,
    "sbdb_enrichment_limit": int,
}

ENDPOINTS = {
    "fireball": "https://ssd-api.jpl.nasa.gov/fireball.api",
    "close approaches": "https://ssd-api.jpl.nasa.gov/cad.api",
    "Sentry": "https://ssd-api.jpl.nasa.gov/sentry.api",
    "SBDB": "https://ssd-api.jpl.nasa.gov/sbdb.api",
}


def ok(message: str) -> None:
    print(f"[OK]   {message}")


def fail(message: str, errors: list[str]) -> None:
    print(f"[FAIL] {message}")
    errors.append(message)


def load_settings(errors: list[str]) -> dict[str, Any]:
    if not SETTINGS_PATH.exists():
        fail("settings.json is missing", errors)
        return {}
    try:
        data = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        fail(f"settings.json cannot be read: {exc}", errors)
        return {}
    if not isinstance(data, dict):
        fail("settings.json must contain one JSON object", errors)
        return {}
    ok("settings.json parsed")
    return data


def validate_settings(settings: dict[str, Any], errors: list[str]) -> None:
    for key, expected in REQUIRED_SETTINGS.items():
        if key not in settings:
            fail(f"missing setting: {key}", errors)
            continue
        if not isinstance(settings[key], expected):
            fail(f"invalid type for {key}: {type(settings[key]).__name__}", errors)
    if errors:
        return

    numeric_positive = [
        "fireball_limit",
        "close_approach_limit",
        "top_report_limit",
        "high_energy_window_days",
        "close_approach_window_days",
        "repeat_object_min_count",
        "top_candidate_packet_limit",
        "sbdb_enrichment_limit",
    ]
    for key in numeric_positive:
        if int(settings[key]) <= 0:
            fail(f"{key} must be greater than zero", errors)

    try:
        distance = float(settings["close_approach_distance_max_au"])
        if not 0 < distance <= 1:
            fail("close_approach_distance_max_au must be > 0 and <= 1 AU", errors)
    except (TypeError, ValueError):
        fail("close_approach_distance_max_au must be numeric", errors)

    if not errors:
        ok("settings contract and basic ranges")


def validate_environment(errors: list[str]) -> None:
    if sys.version_info < (3, 10):
        fail(f"Python 3.10+ required; found {sys.version.split()[0]}", errors)
    else:
        ok(f"Python {sys.version.split()[0]}")

    if not os.access(ROOT, os.W_OK):
        fail(f"project folder is not writable: {ROOT}", errors)
    else:
        ok("project folder is writable")

    source = ROOT / "iupetra.py"
    if not source.exists():
        fail("iupetra.py is missing", errors)
    else:
        ok("iupetra.py present")


def validate_network(errors: list[str]) -> None:
    for label, url in ENDPOINTS.items():
        try:
            request = urllib.request.Request(url, headers={"User-Agent": "IuPetra-doctor/1.0"})
            with urllib.request.urlopen(request, timeout=12) as response:
                if 200 <= response.status < 400:
                    ok(f"{label} endpoint reachable")
                else:
                    fail(f"{label} endpoint returned HTTP {response.status}", errors)
        except Exception as exc:
            fail(f"{label} endpoint unavailable: {exc}", errors)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check IuPetra before running it.")
    parser.add_argument("--network", action="store_true", help="also verify NASA/JPL endpoint connectivity")
    args = parser.parse_args()

    print("IuPetra Doctor")
    print("==============")
    errors: list[str] = []
    validate_environment(errors)
    settings = load_settings(errors)
    if settings:
        validate_settings(settings, errors)
    if args.network:
        validate_network(errors)

    print()
    if errors:
        print(f"Doctor found {len(errors)} problem(s).")
        return 1
    print("Doctor found no problems.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
