"""Replace a file with a fully written temporary file, also on Windows.

On Windows the rename fails with PermissionError while any other process
(antivirus, indexer, a reader thread) briefly holds the target open; on Linux
it never does. Retry a few times before giving up.
"""
from __future__ import annotations

import time
from pathlib import Path

ATTEMPTS = 8


def replace(temporary, path) -> None:
    for attempt in range(ATTEMPTS):
        try:
            Path(temporary).replace(path)
            return
        except PermissionError:
            if attempt == ATTEMPTS - 1:
                raise
            time.sleep(0.05 * 2 ** attempt)  # ~6 s in total
