# Media Transfer Protocols

## Canonical Flow
Prowlarr → Sonarr/Radarr → Gluetun VPN → qBittorrent/SABnzbd → `/home/dwill/Downloads` → copy/verify workflow → `/mnt/plex/*` or `/mnt/tv-anime/*`

Remote Windows fallback:
`ssh Dlex` → `scp` or another SSH copy path → same Linux destinations.

Kill-switch: ON. All torrent and usenet traffic stays behind the Linux VPN stack.

## TV (F.1)
- Preferred destination: `/mnt/plex/Media/TV/`
- Overflow destination: `/mnt/tv-anime/Media/TV/` only when the show already lives there
- Naming: `Show (Year)/Season XX/Show - SXXEYY - Title {Quality}`

## Movies (F.2)
- Destination: `/mnt/plex/Media/Movies/`
- Naming: `Movie (Year)/Movie (Year) {Quality}`
- Movies use per-movie folders

## Anime (F.3)
- Preferred destination: `/mnt/plex/Media/Anime/`
- Overflow destination: `/mnt/tv-anime/Media/Anime/` only when the series already lives there
- Naming: `Anime (Year)/Season XX/Anime - SXXEYY - Title {Quality}`

## Music (F.4)
- Lidarr → `/mnt/other-media/Media/Other/` or the current music root once finalized
- Naming: `Artist/Album (Year)/Track - Title`

## Books (F.5)
- Readarr → library root consumed by Kavita
- EPUB preferred

## Comics (F.6)
- Mylar3 → `/mnt/other-media/Media/Other/Comics/` → Kavita
- CBZ and CBR preferred

## Audiobooks (F.7)
- Manual or Audiobookshelf → `/mnt/other-media/Media/Other/Audiobooks/`
- M4B preferred

## Podcasts (F.8)
- Audiobookshelf → podcast root once finalized
- Auto-download
