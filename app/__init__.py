"""Trading game backend package.

Ensures the project root is importable so that `import config` works no matter
how the package is launched (uvicorn, python -m, tests).
"""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
