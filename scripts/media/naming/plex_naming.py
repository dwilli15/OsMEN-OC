#!/usr/bin/env python3
"""Plex Naming Convention Engine — enforce naming standards across all media types.

Standards (per NAMING_CONVENTIONS.md):
  TV:     Show Name (Year)/Season XX/Show Name - SXXEXX - Episode Title {Quality}.ext
  Movies: Movie Name (Year)/Movie Name (Year) {Quality}.ext
  Anime:  Anime Name (Year)/Season XX/Anime Name - SXXEXX - Title {Quality}.ext
  Music:  Artist/Album (Year)/Track - Title.ext
"""
import re
from pathlib import Path
from dataclasses import dataclass
from enum import Enum


class MediaType(Enum):
    TV = "tv"
    MOVIE = "movie"
    ANIME = "anime"
    MUSIC = "music"


@dataclass
class NamingResult:
    original: str
    proposed: str
    media_type: MediaType
    needs_rename: bool
    issues: list


def sanitize_title(title):
    """Clean a title for filesystem use."""
    tags = ("1080p", "720p", "480p", "2160p", "4K", "UHD", "HEVC",
            "x264", "x265", "AAC", "DD5.1", "WEB-DL", "WEBRip",
            "BluRay", "BRRip", "HDRip", "IMAX", "REPACK", "PROPER")
    for tag in tags:
        title = re.sub(rf'\b{tag}\b', '', title, flags=re.IGNORECASE)
    title = title.replace('.', ' ').replace('_', ' ')
    title = re.sub(r'\s+', ' ', title).strip().strip(' -')
    return title


def extract_year(name):
    """Extract year from name, return (cleaned_name, year_or_None)."""
    m = re.search(r'\((\d{4})\)', name)
    if m:
        return name[:m.start()].strip(), m.group(1)
    m = re.search(r'[\s.\-](\d{4})[\s.\-]', name)
    if m:
        return (name[:m.start()] + name[m.end():]).strip(), m.group(1)
    return name, None


def season_folder(season_num):
    return f"Season {season_num:02d}"


def tv_episode_filename(show, season, episode, title="", quality="", ext=".mkv"):
    name = f"{show} - S{season:02d}E{episode:02d}"
    if title:
        name += f" - {title}"
    if quality:
        name += f" {{{quality}}}"
    return name + ext


def movie_filename(movie, year, quality="", ext=".mkv"):
    name = f"{movie} ({year})"
    if quality:
        name += f" {{{quality}}}"
    return name + ext


def check_tv_path(path):
    """Validate a TV show path structure."""
    issues = []
    parts = path.parts
    if len(parts) >= 3:
        show_dir = parts[-3]
        season_dir = parts[-2]
        if not re.search(r'\(\d{4}\)', show_dir):
            issues.append(f"Show dir missing year: {show_dir}")
        if not re.match(r'Season \d{2}$', season_dir):
            issues.append(f"Non-standard season dir: {season_dir}")
    filename = path.name
    if not re.search(r'- S\d{2}E\d{2} -', filename) and not re.search(r'S\d{2}E\d{2}', filename):
        issues.append(f"Non-standard episode naming: {filename}")
    return issues


def check_movie_path(path):
    """Validate a movie path structure."""
    issues = []
    parts = path.parts
    if len(parts) >= 2:
        folder = parts[-2]
        if not re.search(r'\(\d{4}\)', folder):
            issues.append(f"Movie folder missing year: {folder}")
    filename = path.stem
    if not re.search(r'\(\d{4}\)', filename):
        issues.append(f"Movie filename missing year: {filename}")
    return issues


def propose_rename(path, media_type):
    """Propose a rename for a file based on media type conventions."""
    original = str(path)
    checks = check_tv_path if media_type in (MediaType.TV, MediaType.ANIME) else check_movie_path
    issues = checks(path)
    return NamingResult(original, original, media_type, bool(issues), issues)


if __name__ == "__main__":
    import sys
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    for p in sorted(target.rglob("*")):
        if p.is_file():
            result = propose_rename(p, MediaType.TV)
            if result.needs_rename:
                for issue in result.issues:
                    print(f"  {issue}")
