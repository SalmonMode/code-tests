"""Pytest configuration for local package import resolution."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
project_root_str = str(PROJECT_ROOT)
if project_root_str not in sys.path:
    # Ensure tests can import `inventory_parser` without package installation.
    sys.path.insert(0, project_root_str)
