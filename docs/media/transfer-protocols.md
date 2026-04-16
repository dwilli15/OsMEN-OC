# Media Transfer Protocols

## VPN-Walled Acquisition Flow
Prowlarr → Sonarr/Radarr → Gluetun VPN → qBittorrent/SABnzbd → ~/Downloads/ → auto-import → /media/plex/*
Kill-switch: ON. All torrent/usenet through VPN only.

## TV (F.1)
- Sonarr → /media/plex/TV/ | Naming: Show (Year)/Season XX/Show - SXXEXX - Title {Quality}

## Movies (F.2)
- Radarr → /media/plex/Movies/ | Naming: Movie (Year)/Movie (Year) {Quality}

## Anime (F.3)
- Sonarr → /media/plex/Anime/ | Handle fansub [Group] tags

## Music (F.4)
- Lidarr → /media/plex/Other/ | Artist/Album (Year)/Track - Title

## Books (F.5)
- Readarr → /media/books/ → Kavita | EPUB preferred

## Comics (F.6)
- Mylar3 → /media/comics/ → Kavita | CBZ/CBR preferred

## Audiobooks (F.7)
- Manual/Audiobookshelf → /media/plex/Other/Audiobooks/ | M4B preferred

## Podcasts (F.8)
- Audiobookshelf → /media/podcasts/ | Auto-download
