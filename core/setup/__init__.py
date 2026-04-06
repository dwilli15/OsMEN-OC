"""First-run setup wizard for OsMEN-OC.

Run interactively::

    python -m core.setup

Run non-interactively (uses env vars / defaults)::

    python -m core.setup --auto

Re-run on an already-configured system::

    python -m core.setup --reconfigure
"""

from __future__ import annotations

from core.setup.wizard import SetupConfig, SetupWizard, run_wizard
from core.utils.exceptions import SetupError

__all__ = ["SetupConfig", "SetupError", "SetupWizard", "run_wizard"]
