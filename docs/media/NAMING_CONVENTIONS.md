# OsMEN-OC Naming Conventions — Single Source of Truth

## Decision: Per-Movie Folders (D.33)
Movies use **per-movie folders**: `Movie Name (Year)/Movie Name (Year) {Quality}.ext`
This matches Plex best practice and Sonarr/Radarr defaults.

## TV Shows
```
Show Name (Year)/
  Season 01/
    Show Name - S01E01 - Episode Title {Quality}.ext
    Show Name - S01E02 - Episode Title {Quality}.ext
  Season 02/
  Extras/
```

## Movies
```
Movie Name (Year)/
  Movie Name (Year) {Quality}.ext
  Movie Name (Year).srt
```

## Anime
```
Anime Name (Year)/
  Season 01/
    Anime Name - S01E01 - Title {Quality}.ext
  Extras/
```

## Music
```
Artist Name/
  Album Name (Year)/
    01 - Track Title.flac
    02 - Track Title.flac
```

## Audiobooks
```
Author Name/
  Book Title/
    Book Title.m4b
```

## Comics
```
Series Name/
  Series Name v01.cbz
  Series Name v02.cbz
```

## Quality Tags
- Format: `{Quality}` in curly braces after title
- Examples: `{1080p HEVC}`, `{720p x264}`, `{4K HDR}`
- Scene tags (group names, release tags) stripped from filenames

## Season Folder Format
- Always two digits: `Season 01`, `Season 02`, ... `Season 15`
- Specials: `Season 00`
- NEVER: `Season 1`, `S01`, `season 01`
