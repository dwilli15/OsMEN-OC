#!/usr/bin/env bash
# Movie intake -> per-movie folder -> place in Plex
# Usage: movie_transfer.sh /path/to/movie.mkv
set -euo pipefail

PLEX_MOVIES="/run/media/dwill/plex/Media/Movies"
DOWNLOADS="$HOME/Downloads"
DRY_RUN="${DRY_RUN:-true}"

src="$1"
filename=$(basename "$src")
stem="${filename%.*}"
ext="${filename##*.}"

# Extract title and year
year=$(echo "$stem" | grep -oP '\d{4}' | head -1)
if [ -n "$year" ]; then
    title=$(echo "$stem" | sed "s/[$year]//g; s/[()\-._]/ /g; s/  */ /g" | sed 's/^\s*//;s/\s*$//')
    folder="$PLEX_MOVIES/$title ($year)"
else
    title="$stem"
    folder="$PLEX_MOVIES/$title"
fi

echo "Source:   $src"
echo "Dest:     $folder/$filename"

if [ "$DRY_RUN" = "false" ]; then
    mkdir -p "$folder"
    mv "$src" "$folder/$filename"
    echo "MOVED."
else
    echo "DRY RUN — set DRY_RUN=false to execute"
fi
