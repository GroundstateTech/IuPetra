from __future__ import annotations

import unittest
from unittest import mock

import run_iupetra


class RunnerTests(unittest.TestCase):
    def test_wrapper_runs_core_and_writes_provenance(self):
        with mock.patch.object(run_iupetra.iupetra, 'main', return_value=0) as core, \
             mock.patch.object(run_iupetra, 'write_provenance') as provenance:
            code = run_iupetra.main()

        self.assertEqual(code, 0)
        core.assert_called_once_with()
        provenance.assert_called_once()
        self.assertIs(run_iupetra.iupetra.fetch_json, run_iupetra.reliable_fetch_json)


if __name__ == '__main__':
    unittest.main()
