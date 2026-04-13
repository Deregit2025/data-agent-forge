"""
Root conftest.py — makes the project root importable so that
`from utils.xxx import ...` and `from agent.xxx import ...` work
when pytest is run from any subdirectory.
"""

import sys
from pathlib import Path

# insert the project root at the front of sys.path
sys.path.insert(0, str(Path(__file__).parent))
