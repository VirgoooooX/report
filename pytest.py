"""Workspace-local pytest launcher for constrained runtimes.

Allows `python -m pytest` to work when dependencies are vendored in `.pydeps`.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(__file__)
_VENDORED = os.path.join(_ROOT, ".pydeps")
_BACKEND = os.path.join(_ROOT, "backend")

# When this file is executed via `python -m pytest`, the repository root is
# placed on sys.path first. That would make internal pytest imports resolve
# back to this launcher instead of the installed pytest package.
sys.path = [
    path for path in sys.path
    if os.path.abspath(path or os.getcwd()) != os.path.abspath(_ROOT)
]

if os.path.isdir(_VENDORED) and _VENDORED not in sys.path:
    sys.path.insert(0, _VENDORED)
if os.path.isdir(_BACKEND) and _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from _pytest.config import main as _main


if __name__ == "__main__":
    raise SystemExit(_main())
