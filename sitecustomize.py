"""Project-local Python startup tweaks.

Automatically include workspace vendored dependencies so commands like
`python -m pytest` work in constrained environments.
"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(__file__)
_VENDORED = os.path.join(_ROOT, ".pydeps")

if os.path.isdir(_VENDORED) and _VENDORED not in sys.path:
    sys.path.insert(0, _VENDORED)
