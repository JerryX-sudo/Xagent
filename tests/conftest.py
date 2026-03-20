"""Pytest configuration."""

import sys
from pathlib import Path

# Ensure project root is FIRST in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Remove parent directories that might interfere
to_remove = []
for p in sys.path:
    if p and Path(p) == project_root.parent:
        to_remove.append(p)
for p in to_remove:
    sys.path.remove(p)

# Ensure our utils is loaded, not the parent's
if 'utils' in sys.modules:
    del sys.modules['utils']
