"""Quadlet compliance tests for production safety guardrails."""

from __future__ import annotations

import configparser
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
QUADLETS_DIR = REPO_ROOT / "quadlets"


def _parse_ini(path: Path) -> configparser.RawConfigParser:
    parser = configparser.RawConfigParser(strict=False)
    parser.read_string(path.read_text(encoding="utf-8"))
    return parser


def _container_files() -> list[Path]:
    return sorted(QUADLETS_DIR.rglob("*.container"))


def test_container_quadlets_exist() -> None:
    files = _container_files()
    assert files, "Expected at least one .container quadlet under quadlets/"


def test_container_quadlets_have_health_checks() -> None:
    for path in _container_files():
        parser = _parse_ini(path)
        assert parser.has_section("Container"), f"{path} missing [Container] section"
        health_cmd = parser.get("Container", "HealthCmd", fallback="").strip()
        assert health_cmd, f"{path} missing HealthCmd"


def test_container_quadlets_pin_image_tags() -> None:
    for path in _container_files():
        parser = _parse_ini(path)
        image = parser.get("Container", "Image", fallback="").strip()
        assert image, f"{path} missing Image"
        assert ":" in image, f"{path} image is not version-pinned: {image!r}"
        assert not image.endswith(":latest"), f"{path} must not use :latest"


def test_container_quadlets_use_default_target() -> None:
    for path in _container_files():
        parser = _parse_ini(path)
        assert parser.has_section("Install"), f"{path} missing [Install] section"
        wanted_by = parser.get("Install", "WantedBy", fallback="")
        assert "default.target" in wanted_by, f"{path} must use WantedBy=default.target"


def test_container_quadlets_use_rootless_slice() -> None:
    for path in _container_files():
        parser = _parse_ini(path)
        assert parser.has_section("Service"), f"{path} missing [Service] section"
        slice_name = parser.get("Service", "Slice", fallback="")
        assert slice_name.startswith("user-osmen-"), f"{path} has unexpected Slice: {slice_name!r}"


def test_container_quadlets_enforce_no_new_privileges() -> None:
    for path in _container_files():
        parser = _parse_ini(path)
        assert parser.has_section("Container"), f"{path} missing [Container] section"
        value = parser.get("Container", "NoNewPrivileges", fallback="").strip().lower()
        assert value == "true", f"{path} must set NoNewPrivileges=true"


# Containers with documented reasons for not using ReadOnly=true.
# Each entry corresponds to a comment in the quadlet file explaining why.
_READ_ONLY_EXEMPT = {
    "osmen-core-chromadb.container",  # uvicorn writes /chroma/chroma.log outside data volume
    "osmen-core-langflow.container",  # app writes runtime state outside volumes
    "osmen-core-nextcloud.container",  # PHP runtime needs writable rootfs
    "osmen-core-siyuan.container",  # chown on /opt/siyuan at startup
    "osmen-media-gluetun.container",  # writes /etc/passwd and /tmp at startup
    "osmen-librarian-audiobookshelf.container",  # app writes runtime config outside volumes
    "osmen-librarian-convertx.container",  # file conversion writes to app directory
    "osmen-librarian-kavita.container",  # app writes runtime config outside volumes
    "osmen-librarian-whisper.container",  # NVIDIA CDI hook needs writable rootfs for GPU device files
}


def test_container_quadlets_enforce_read_only_rootfs() -> None:
    for path in _container_files():
        if path.name in _READ_ONLY_EXEMPT:
            continue
        parser = _parse_ini(path)
        assert parser.has_section("Container"), f"{path} missing [Container] section"
        value = parser.get("Container", "ReadOnly", fallback="").strip().lower()
        assert value == "true", f"{path} must set ReadOnly=true"
