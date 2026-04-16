"""CLI entry point for secrets custodian operations.

Usage:
    python -m core.secrets.cli audit
    python -m core.secrets.cli verify-env
    python -m core.secrets.cli verify-podman
"""

from __future__ import annotations

import json
import sys

from loguru import logger

from core.secrets.custodian import SecretsCustodian


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python -m core.secrets.cli <audit|verify-env|verify-podman>")
        sys.exit(1)

    command = sys.argv[1]
    custodian = SecretsCustodian()

    if command == "audit":
        report = custodian.audit_secrets()
        print(json.dumps(report.summary(), indent=2))
        sys.exit(0 if report.clean else 1)
    elif command == "verify-env":
        findings = custodian.verify_env_file()
        for f in findings:
            print(f"[{f.severity}] {f.message}")
        sys.exit(0 if not findings else 1)
    elif command == "verify-podman":
        findings = custodian.verify_podman_secrets()
        for f in findings:
            print(f"[{f.severity}] {f.message}")
        sys.exit(0 if not findings else 1)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
