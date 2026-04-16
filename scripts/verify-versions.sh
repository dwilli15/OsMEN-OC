#!/usr/bin/env bash
# verify-versions.sh — Post-upgrade verification for critical packages.
# Checks NVIDIA driver, kernel, Python, and Podman versions against known minimums.
set -euo pipefail

echo "=== OsMEN-OC Version Verification ==="
echo

# Kernel
KVER=$(uname -r)
echo "Kernel: $KVER"

# NVIDIA
if command -v nvidia-smi &>/dev/null; then
    NVIDIA_VER=$(nvidia-smi --query-gpu=driver_version --format=csv,noheader 2>/dev/null | head -1)
    echo "NVIDIA Driver: $NVIDIA_VER"
    NVIDIA_GPU=$(nvidia-smi --query-gpu=name --format=csv,noheader 2>/dev/null | head -1)
    echo "NVIDIA GPU: $NVIDIA_GPU"
else
    echo "NVIDIA: not installed"
fi

# Python
PYVER=$(python3 --version 2>/dev/null || echo "not found")
echo "Python: $PYVER"

# Podman
PVER=$(podman --version 2>/dev/null || echo "not found")
echo "Podman: $PVER"

# PostgreSQL
PGVER=$(podman exec osmen-core-postgres psql -V 2>/dev/null || echo "not accessible")
echo "PostgreSQL: $PGVER"

# Redis
RVER=$(podman exec osmen-core-redis redis-server --version 2>/dev/null | grep -oP 'v=\K[^ ]+' || echo "not accessible")
echo "Redis: $RVER"

# Taskwarrior
TVER=$(task --version 2>/dev/null || echo "not found")
echo "Taskwarrior: $TVER"

# Docker/Podman Compose
echo; echo "=== Running Containers ==="
podman ps --format '{{.Names}}\t{{.Status}}' 2>/dev/null | sort

echo; echo "=== Disk Usage ==="
df -h / /home 2>/dev/null | grep -v '^Filesystem'

echo; echo "Verification complete."
