"""Workspace-local pytest launcher for constrained runtimes.

Allows `python -m pytest` to work when dependencies are vendored in `.pydeps`.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(__file__)
_VENDORED = os.path.join(_ROOT, ".pydeps")
if os.path.isdir(_VENDORED) and _VENDORED not in sys.path:
    sys.path.insert(0, _VENDORED)

from _pytest.config import main as _main


if __name__ == "__main__":
    raise SystemExit(_main())
