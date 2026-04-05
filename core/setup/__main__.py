"""Entry point for ``python -m core.setup`` and the ``osmen-setup`` CLI.

Usage::

    python -m core.setup                   # interactive
    python -m core.setup --auto            # non-interactive (env vars / defaults)
    python -m core.setup --reconfigure     # re-run even if already configured
"""

from __future__ import annotations

import argparse
import sys

from core.setup.wizard import run_wizard


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the setup wizard.

    Args:
        argv: Argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Exit code: 0 on success, 1 on error or cancellation.
    """
    parser = argparse.ArgumentParser(
        prog="osmen-setup",
        description="OsMEN-OC semi-automated interactive first-run setup wizard.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  osmen-setup                  # interactive\n"
            "  osmen-setup --auto           # non-interactive (CI / scripted)\n"
            "  osmen-setup --reconfigure    # update an existing configuration\n"
        ),
    )
    parser.add_argument(
        "--auto",
        action="store_true",
        help="Non-interactive: use env vars and defaults for all prompts.",
    )
    parser.add_argument(
        "--reconfigure",
        action="store_true",
        help="Re-run even if setup is already marked complete.",
    )
    args = parser.parse_args(argv)
    return run_wizard(auto=args.auto, reconfigure=args.reconfigure)


if __name__ == "__main__":
    sys.exit(main())
