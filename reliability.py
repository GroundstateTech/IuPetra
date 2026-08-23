from __future__ import annotations

import hashlib
import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


RETRIABLE_HTTP_CODES = {408, 425, 429, 500, 502, 503, 504}
DEFAULT_ATTEMPTS = 4
DEFAULT_BASE_DELAY = 0.75
STALE_AFTER_HOURS = 24.0


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')


def reliable_fetch_json(
    url: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 60,
    attempts: int = DEFAULT_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
    user_agent: str = 'IuPetra-v1.3.2',
) -> Dict[str, Any]:
    """Fetch a JSON object with bounded exponential backoff.

    Retries only transient HTTP/network/timeout/JSON failures. Permanent HTTP
    errors fail immediately so IuPetra can fall back to its existing local-data
    behavior rather than hiding a bad request behind repeated attempts.
    """
    full_url = url
    if params:
        full_url = f"{url}?{urllib.parse.urlencode(params)}"

    last_error: Exception | None = None
    attempt_limit = max(1, int(attempts))

    for attempt in range(1, attempt_limit + 1):
        request = urllib.request.Request(full_url, headers={'User-Agent': user_agent})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode('utf-8'))
                if not isinstance(payload, dict):
                    raise ValueError('API response was not a JSON object')
                return payload
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code not in RETRIABLE_HTTP_CODES or attempt >= attempt_limit:
                raise
        except (urllib.error.URLError, TimeoutError, ConnectionError, json.JSONDecodeError, ValueError) as exc:
            last_error = exc
            if attempt >= attempt_limit:
                raise

        delay = float(base_delay) * (2 ** (attempt - 1))
        delay += random.uniform(0.0, min(0.35, delay * 0.2))
        time.sleep(delay)

    if last_error:
        raise last_error
    raise RuntimeError('fetch failed without an exception')


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def freshness_record(path: Path, now: datetime | None = None) -> Dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    stat = path.stat()
    modified = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
    age_hours = max(0.0, (now - modified).total_seconds() / 3600.0)
    return {
        'modified_utc': modified.isoformat().replace('+00:00', 'Z'),
        'age_hours': round(age_hours, 3),
        'freshness': 'fresh' if age_hours <= STALE_AFTER_HOURS else 'stale',
    }


def build_provenance(project_root: Path, exit_code: int) -> Dict[str, Any]:
    """Build a compact, machine-readable provenance record for the run."""
    reports = project_root / 'reports'
    data = project_root / 'data'
    now = datetime.now(timezone.utc)
    files = []

    for base in (data / 'raw', data / 'clean', reports):
        if not base.exists():
            continue
        for path in sorted(base.rglob('*')):
            if not path.is_file() or path.name == 'run_provenance.json':
                continue
            try:
                record = {
                    'path': path.relative_to(project_root).as_posix(),
                    'size_bytes': path.stat().st_size,
                    'sha256': sha256_file(path),
                }
                record.update(freshness_record(path, now))
                files.append(record)
            except OSError:
                continue

    raw_sources = [item for item in files if item['path'].startswith('data/raw/')]
    stale_sources = [item['path'] for item in raw_sources if item['freshness'] == 'stale']

    return {
        'schema_version': 1,
        'generated_utc': now.isoformat().replace('+00:00', 'Z'),
        'iupetra_exit_code': int(exit_code),
        'fetch_policy': {
            'attempts': DEFAULT_ATTEMPTS,
            'base_delay_seconds': DEFAULT_BASE_DELAY,
            'stale_after_hours': STALE_AFTER_HOURS,
        },
        'raw_source_count': len(raw_sources),
        'stale_raw_sources': stale_sources,
        'file_count': len(files),
        'files': files,
    }


def write_provenance(project_root: Path, exit_code: int) -> Path:
    target = project_root / 'reports' / '99_TECHNICAL_LOGS' / 'run_provenance.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(build_provenance(project_root, exit_code), indent=2) + '\n', encoding='utf-8')
    return target
