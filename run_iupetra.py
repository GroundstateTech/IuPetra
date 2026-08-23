from __future__ import annotations

from pathlib import Path

import iupetra
from reliability import reliable_fetch_json, write_provenance


def main() -> int:
    # Keep the analysis/report pipeline unchanged; only replace the network
    # fetch primitive with the retry-aware implementation.
    iupetra.fetch_json = reliable_fetch_json

    exit_code = 1
    try:
        exit_code = int(iupetra.main())
        return exit_code
    finally:
        try:
            provenance = write_provenance(Path(__file__).resolve().parent, exit_code)
            print(f"Run provenance: {provenance}")
        except Exception as exc:
            # Provenance is diagnostic only and must never turn a successful
            # scientific/report run into a failed run.
            print(f"WARNING: could not write run provenance: {exc}")


if __name__ == '__main__':
    raise SystemExit(main())
