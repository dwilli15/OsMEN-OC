#!/usr/bin/env bash
# Movie intake -> per-movie folder -> place in Plex
# Usage: movie_transfer.sh /path/to/movie.mkv
set -euo pipefail

PLEX_MOVIES="${PLEX_MOVIES:-/mnt/plex/Media/Movies}"
DRY_RUN="${DRY_RUN:-true}"

sanitize_title() {
    printf '%s' "$1" | sed -E 's/[._-]+/ /g; s/[[:space:]]+/ /g; s/^[[:space:]]+//; s/[[:space:]]+$//'
}

if [[ $# -ne 1 ]]; then
    echo "Usage: $0 /path/to/movie.mkv" >&2
    exit 1
fi

src="$1"
if [[ ! -f "$src" ]]; then
    echo "Source file not found: $src" >&2
    exit 1
fi

filename=$(basename "$src")
stem="${filename%.*}"
ext="${filename##*.}"
year=$(printf '%s' "$stem" | grep -oE '(19|20)[0-9]{2}' | head -1 || true)

if [[ -n "$year" ]]; then
    raw_title=$(printf '%s' "$stem" | sed -E "s/[[(]?$year[)\]]?//")
    title=$(sanitize_title "$raw_title")
    folder="$PLEX_MOVIES/$title ($year)"
    dest_name="$title ($year).$ext"
else
    title=$(sanitize_title "$stem")
    folder="$PLEX_MOVIES/$title"
    dest_name="$title.$ext"
fi

dest_path="$folder/$dest_name"

echo "Source:   $src"
echo "Dest:     $dest_path"

if [[ "$DRY_RUN" == "false" ]]; then
    mkdir -p "$folder"
    cp -n --preserve=timestamps "$src" "$dest_path"
    echo "COPIED."
else
    echo "DRY RUN -- set DRY_RUN=false to execute"
fi
