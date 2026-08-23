from __future__ import annotations

import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

import reliability


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode('utf-8')


class ReliabilityTests(unittest.TestCase):
    def test_fetch_success(self):
        with mock.patch('urllib.request.urlopen', return_value=FakeResponse({'ok': True})) as opened:
            payload = reliability.reliable_fetch_json('https://example.invalid/api', attempts=1)
        self.assertEqual(payload, {'ok': True})
        self.assertEqual(opened.call_count, 1)

    def test_fetch_retries_transient_network_failure(self):
        side_effects = [
            urllib.error.URLError('temporary'),
            FakeResponse({'ok': True}),
        ]
        with mock.patch('urllib.request.urlopen', side_effect=side_effects) as opened, mock.patch('time.sleep'):
            payload = reliability.reliable_fetch_json('https://example.invalid/api', attempts=2, base_delay=0)
        self.assertEqual(payload, {'ok': True})
        self.assertEqual(opened.call_count, 2)

    def test_fetch_does_not_retry_permanent_http_error(self):
        error = urllib.error.HTTPError('https://example.invalid', 404, 'not found', None, None)
        with mock.patch('urllib.request.urlopen', side_effect=error) as opened, self.assertRaises(urllib.error.HTTPError):
            reliability.reliable_fetch_json('https://example.invalid/api', attempts=4, base_delay=0)
        self.assertEqual(opened.call_count, 1)

    def test_provenance_records_checksums_and_source_freshness(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw = root / 'data' / 'raw'
            reports = root / 'reports' / '99_TECHNICAL_LOGS'
            raw.mkdir(parents=True)
            reports.mkdir(parents=True)
            source = raw / 'sample.json'
            source.write_text('{"x": 1}\n', encoding='utf-8')

            target = reliability.write_provenance(root, 0)
            payload = json.loads(target.read_text(encoding='utf-8'))

            self.assertEqual(payload['iupetra_exit_code'], 0)
            self.assertEqual(payload['raw_source_count'], 1)
            self.assertEqual(payload['file_count'], 1)
            record = payload['files'][0]
            self.assertEqual(record['path'], 'data/raw/sample.json')
            self.assertEqual(len(record['sha256']), 64)
            self.assertIn(record['freshness'], {'fresh', 'stale'})


if __name__ == '__main__':
    unittest.main()
