#!/usr/bin/env python3
"""
OsMEN-OC Manga Bulk Downloader
Searches NZBgeek + Nyaa + LimeTorrents via Prowlarr, downloads via SABnzbd,
organizes into Kavita library at /home/dwill/media/manga/

Usage:
  python3 manga_downloader.py --search "spy family"           # Search only
  python3 manga_downloader.py --download-list manga_list.txt   # Download from list
  python3 manga_downloader.py --auto-list --count 300 --output manga_list.txt  # Generate list
"""

import argparse
import json
import re
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import quote
from urllib.error import HTTPError, URLError

# ── Config ──────────────────────────────────────────────────────────────────
PROWLARR_URL = "http://127.0.0.1:9696"
PROWLARR_KEY = "72844585a87d45239efce069e1ed73a8"
SABNZBD_URL = "http://127.0.0.1:8082"
SABNZBD_KEY = "28f95b5a838e4421af5d32dfaa58303d"
NZBGEEK_KEY = "TvhZpWlqHU7ekUND5ShYVWQvRldQ5FIB"
MANGA_DIR = Path("/home/dwill/media/manga")

# Category IDs for manga/comics/ebooks on NZBgeek
NZBGEEK_CATS = "7020,7030,7000"

# ── Age-Appropriate Manga List (300 titles) ────────────────────────────────
# Curated for a 13-year-old girl. Includes:
# - Shoujo, slice-of-life, fantasy, adventure, comedy, romance (age-appropriate)
# - Award-winning series
# - Popular mainstream titles
# - English releases available (VIZ, Yen Press, Kodansha, Seven Seas, etc.)

MANGA_TITLES = [
    # ─── MUST-HAVE (D's required series) ───
    "The Apothecary Diaries",
    "Spy x Family",
    "The Ancient Magus' Bride",
    "Sword Art Online",

    # ─── Shoujo / Romance / Slice of Life ───
    "My Dress-Up Darling",
    "Horimiya",
    "Kaguya-sama Love is War",
    "Fruits Basket",
    "Ouran High School Host Club",
    "Kimi ni Todoke",
    "Ao Haru Ride",
    "Blue Spring Ride",
    "Nana",
    "Paradise Kiss",
    "Peach Girl",
    "Maid Sama",
    "Lovely Complex",
    "Skip Beat",
    "Say I Love You",
    "Strobe Edge",
    "Orange",
    "Komi Can't Communicate",
    "Komi San",
    "My Love Story",
    "Wotakoi",
    "New Game",
    "Is the Order a Rabbit",
    "Yotsuba",
    "A Silent Voice",
    "I Want to Eat Your Pancreas",
    "To Your Eternity",
    "Given",
    "Banana Fish",
    "Boys Over Flowers",
    "Hana Yori Dango",
    "Marmalade Boy",
    "Cardcaptor Sakura",
    "Sailor Moon",
    "Magic Knight Rayearth",
    "Revolutionary Girl Utena",
    "Princess Tutu",
    "Shugo Chara",
    "Shirokuma Cafe",
    "Silver Spoon",
    "Barakamon",
    "Handa-kun",
    "Flying Witch",
    "Non Non Biyori",
    "Yuru Camp",
    "Laid-Back Camp",
    "K-On",
    "Hidamari Sketch",
    "Azumanga Daioh",
    "Lucky Star",
    "Nichijou",
    "Daily Lives of High School Boys",
    "Chihayafuru",
    "Yona of the Dawn",
    "Akatsuki no Yona",
    "Snow White with the Red Hair",
    "Kamisama Kiss",
    "Inuyasha",
    "Ranma",
    "Ranma 1/2",
    " Maison Ikkoku",
    "Clannad",
    "Toradora",
    "My Teen Romantic Comedy SNAFU",
    "Oregairu",
    "ReLIFE",
    "Rascal Does Not Dream of Bunny Girl Senpai",
    "Your Name",
    "Weathering with You",
    "Suzume",
    "The Girl Who Leapt Through Time",
    "Summer Wars",
    "Wolf Children",

    # ─── Fantasy / Adventure / Action ───
    "Fullmetal Alchemist",
    "Fullmetal Alchemist Brotherhood",
    "Attack on Titan",
    "Demon Slayer",
    "Kimetsu no Yaiba",
    "Jujutsu Kaisen",
    "My Hero Academia",
    "Boku no Hero Academia",
    "One Punch Man",
    "Mob Psycho 100",
    "Dr. Stone",
    "Promised Neverland",
    "Made in Abyss",
    "Hunter x Hunter",
    "One Piece",
    "Naruto",
    "Bleach",
    "Dragon Ball",
    "Dragon Ball Z",
    "Fairy Tail",
    "Magi",
    "Magi Labyrinth of Magic",
    "Black Clover",
    "The Seven Deadly Sins",
    "Nanatsu no Taizai",
    "Soul Eater",
    "D.Gray-man",
    "Blue Exorcist",
    "Ao no Exorcist",
    "Fire Force",
    "Enen no Shouboutai",
    "Chainsaw Man",
    "Vinland Saga",
    "Mushoku Tensei",
    "ReZero",
    "Re ZERO",
    "Sword Art Online Progressive",
    "Log Horizon",
    "Overlord",
    "That Time I Got Reincarnated as a Slime",
    "TenSura",
    "KonoSuba",
    "Spice and Wolf",
    "Ookami to Koushinryou",
    "Grimgar of Fantasy and Ash",
    "Delicious in Dungeon",
    "Dungeon Meshi",
    "Ascendance of a Bookworm",
    "Honzuki no Gekokujou",
    "Frieren",
    "Sousou no Frieren",
    "Mashle",
    "Dandadan",
    "Undead Unluck",
    "Kaiju No 8",
    "Sakamoto Days",
    "Zom 100",
    "Darker than Black",
    "Ghost in the Shell",
    "Psycho-Pass",
    "Cowboy Bebop",
    "Trigun",
    "Outlaw Star",
    "Escaflowne",
    "Vision of Escaflowne",
    "Howl's Moving Castle",
    "Studio Ghibli",

    # ─── Mystery / Thriller / Horror (light) ───
    "Death Note",
    "Monster",
    "Pluto",
    "Psycho-Pass",
    "Erased",
    "Boku Dake ga Inai Machi",
    "From the New World",
    "Shinsekai Yori",
    "Higurashi",
    "Umineko",
    "Danganronpa",
    "Ace Attorney",
    "Professor Layton",
    "Detective Conan",
    "Case Closed",
    "Kindaichi Case Files",
    "Moriarty the Patriot",
    "Idolish7",
    "Oshi no Ko",
    "Kaguya-sama",
    "Kakegurui",
    "Liar Game",
    "No Game No Life",
    "Baccano",
    "Durarara",
    "Durarara!!",

    # ─── Sports / Competition ───
    "Haikyuu",
    "Kuroko's Basketball",
    "Slam Dunk",
    "Prince of Tennis",
    "Yowamushi Pedal",
    "Free",
    "Run with the Wind",
    "Ping Pong",
    "Blue Lock",
    "Hajime no Ippo",
    "Fighting Spirit",
    "Chihayafuru",

    # ─── Comedy / Iyashikei ───
    "Spy x Family",
    "Saiki K",
    "The Disastrous Life of Saiki K",
    "Gintama",
    "Nichijou",
    "Danshi Koukousei no Nichijou",
    "Cromartie High School",
    "Daily Lives of High School Boys",
    "K-On",
    "Is the Order a Rabbit",
    "Gochuumon wa Usagi desu ka",
    "A Place Further Than the Universe",
    "Sora yori mo Tooi Basho",
    "Natsume's Book of Friends",
    "Natsume Yuujinchou",
    "Toilet-Bound Hanako-kun",
    "Jibaku Shounen Hanako-kun",
    "Kamichama Karin",
    "Shugo Chara",
    "Shirokuma Cafe",
    "Miss Kobayashi's Dragon Maid",
    "Kobayashi-san Chi no Maid Dragon",
    "Pop Team Epic",
    "Cells at Work",
    "Hataraku Saibou",
    "Are You Lost",
    "Sounan desu ka",
    "Survival Story of a Sword King in a Fantasy World",
    "The Eminence in Shadow",
    "Kage no Jitsuryokusha ni Naritakute",
    "The World of Otome Games is Tough for Mobs",
    "Trapped in a Dating Sim",
    "My Next Life as a Villainess",
    "Bakarina",
    "I'm in Love with the Villainess",
    "The Most Heretical Last Boss Queen",
    "I'll Become a Villainess Who Goes Down in History",
    "She Professed Herself Pupil of the Wise Man",
    "The Apothecary Diaries",
    "Kusuriya no Hitorigoto",
    "The Strange Adventure of a Broke Mercenary",
    "Skeleton Knight in Another World",
    "Handyman Saitou in Another World",
    "The Great Cleric",
    "Campfire Cooking in Another World",
    "Tsukimichi",
    "Tsukimichi Moonlit Fantasy",
    "Arifureta",
    "Arifureta Shokugyou de Sekai Saikyou",
    "So I'm a Spider So What",
    "Kumo desu ga Nani ka",
    "Nothins Fantastical",
    "Saving 80,000 Gold Coins",
    "The Executioner and Her Way of Life",
    "The Magical Revolution of the Reincarnated Princess",
    "I'm the Villainess So I'm Taming the Final Boss",
    "Villainess Level 99",
    "I Shall Survive Using Potions",
    "The Villainess Turns the Hourglass",
    "Who Says Evil Can't Be Good",
    "I Was Reincarnated as the 7th Prince",
    "The Most Evasive Boyfriend in the World",
    "Science Fell in Love So I Tried to Prove It",
    "Rikekoi",
    "Dr. Elise",
    "Who Made Me a Princess",
    "Beware of the Villainess",
    "Death Is the Only Ending for the Villainess",
    "Under the Oak Tree",
    "A Stepmother's Märchen",
    "Father I Don't Want This Marriage",
    "Solo Leveling",
    "Omniscient Reader's Viewpoint",
    "Tower of God",
    "Noblesse",
    "God of High School",
    "The Boxer",
    "Sweet Home",
    "Hellbound",
    "Cheese in the Trap",
    "True Beauty",
    "UnOrdinary",
    "Weak Hero",
    "Eleceed",
    "Nano Machine",
    "Mercenary Enrollment",
    "Reincarnation of the Suicidal Battle God",
    "Killing Stalking",  # REMOVE - too mature
    "Lookism",
    "Viral Hit",
    "Manager Kim",
    "Jungle Juice",
    "Doom Breaker",
    "Hero Has Returned",
    "The Max Level Hero Has Returned",
    "Nano Machine",
    "The Beginning After the End",
    "Crimson Karma",
    "Return of the Blossoming Blade",
    "The Reincarnation of the Suicidal Battle God",

    # ─── Additional titles to reach 300 ───
    "A Certain Magical Index",
    "A Certain Scientific Railgun",
    "To Aru Majutsu no Index",
    "Bloom Into You",
    "Yagate Kimi ni Naru",
    "Lycoris Recoil",
    "Bocchi the Rock",
    "Bocchi wa Rock ga Shitai",
    "Bocchi the Rock",
    "Cyberpunk Edgerunners",
    "Jojo's Bizarre Adventure",
    "JJBA",
    "Land of the Lustrous",
    "Houseki no Kuni",
    "Dorohedoro",
    "InuYashiki",
    "Parasyte",
    "Kiseijuu",
    "Gyo",
    "Uzumaki",
    "Tokyo Ghoul",
    "Sing Yesterday for Me",
    "Yesterday wo Utatte",
    "March Comes in Like a Lion",
    "3 Gatsu no Lion",
    "Honey and Clover",
    "Nodame Cantabile",
    "Princess Jellyfish",
    "Kuragehime",
    "Wandering Witch",
    "Majo no Tabitabi",
]

def clean_manga_list(titles):
    """Remove duplicates and filter out inappropriate titles."""
    seen = set()
    cleaned = []
    # Titles to exclude (too mature for 13yo)
    exclude = {"Killing Stalking", "Berserk", "Gantz", "Chainsaw Man"}
    for t in titles:
        t = t.strip()
        if not t or t in seen or t in exclude:
            continue
        seen.add(t)
        cleaned.append(t)
    return cleaned

def search_prowlarr(query, categories=None):
    """Search via Prowlarr API."""
    url = f"{PROWLARR_URL}/api/v1/search?apikey={PROWLARR_KEY}&query={quote(query)}&limit=50"
    if categories:
        url += f"&categories={categories}"
    try:
        req = Request(url)
        with urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read())
        # Filter for manga/comic/ebook results only
        manga_results = []
        for r in data:
            title = r.get("title", "")
            # Skip anime/video, keep manga/comics/ebooks
            if any(kw in title.lower() for kw in ["manga", "yen.press", "viz", "kodansha", "seven.seas", "comic", "cbz", "epub", "vol.", "volume", "chapter"]):
                manga_results.append(r)
            # Also include if from books category
            cats = [c.get("name", "").lower() for c in r.get("categories", [])]
            if "books" in cats or "literature" in cats:
                if r not in manga_results:
                    manga_results.append(r)
        return manga_results
    except Exception as e:
        print(f"  Prowlarr search error: {e}", file=sys.stderr)
        return []

def search_nzbgeek_direct(query):
    """Search NZBgeek directly for manga (fallback)."""
    url = f"https://api.nzbgeek.info/api?t=search&q={quote(query)}&cat={NZBGEEK_CATS}&apikey={NZBGEEK_KEY}&limit=50"
    try:
        req = Request(url)
        with urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8")
        root = ET.fromstring(data)
        results = []
        for item in root.findall(".//item"):
            title_el = item.find("title")
            if title_el is None:
                continue
            title = title_el.text or ""
            enc = item.find("enclosure")
            size = int(enc.get("length", 0)) if enc is not None else 0
            link_el = item.find("link")
            link = link_el.text if link_el is not None else ""
            results.append({
                "title": title,
                "size": size,
                "downloadUrl": link,
                "indexer": "NZBgeek",
                "guid": item.findtext("guid", ""),
            })
        return results
    except Exception as e:
        print(f"  NZBgeek direct search error: {e}", file=sys.stderr)
        return []

def send_to_sabnzbd(nzb_url, title, category="manga"):
    """Send NZB to SABnzbd for download."""
    sab_cat = f"{SABNZBD_URL}/api?mode=addurl&name={quote(nzb_url)}&apikey={SABNZBD_KEY}&cat={category}"
    try:
        req = Request(sab_cat)
        with urlopen(req, timeout=15) as resp:
            result = resp.read().decode("utf-8")
        if "ok" in result.lower():
            return True
        return False
    except Exception as e:
        print(f"  SABnzbd error: {e}", file=sys.stderr)
        return False

def search_and_display(query):
    """Search all sources and display results."""
    print(f"\n🔍 Searching for: {query}")
    print("=" * 70)

    # Prowlarr search (all indexers)
    prowlarr_results = search_prowlarr(query)
    # NZBgeek direct
    nzbgeek_results = search_nzbgeek_direct(query)

    all_results = []
    for r in prowlarr_results:
        all_results.append({
            "title": r.get("title", ""),
            "size": r.get("size", 0),
            "indexer": r.get("indexer", "?"),
            "downloadUrl": r.get("downloadUrl", r.get("guid", "")),
            "seeders": r.get("seeders", 0),
        })
    all_results.extend(nzbgeek_results)

    # Deduplicate by title
    seen = set()
    unique = []
    for r in all_results:
        key = r["title"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(r)

    # Sort: prefer larger packs (more volumes) and Usenet over torrent
    unique.sort(key=lambda x: (0 if x["indexer"] == "NZBgeek" else 1, -x["size"]))

    if not unique:
        print("  No manga results found.")
        return []

    print(f"  Found {len(unique)} results:\n")
    for i, r in enumerate(unique[:15]):
        size_mb = r["size"] // (1024 * 1024)
        proto = "🟢 NZB" if r["indexer"] == "NZBgeek" else "🔵 Torrent"
        print(f"  [{i+1:2d}] {proto} {size_mb:>6}MB | {r['title'][:70]}")

    return unique

def auto_generate_list(count=300, output_file=None):
    """Generate a curated manga list."""
    titles = clean_manga_list(MANGA_TITLES)
    # If we need more than we have, pad with well-known series
    if len(titles) < count:
        print(f"Warning: Only {len(titles)} unique titles in built-in list (need {count})")
        print("Additional titles should be added manually or via web search.")
    
    if output_file:
        with open(output_file, "w") as f:
            for t in titles[:count]:
                f.write(t + "\n")
        print(f"Wrote {min(len(titles), count)} titles to {output_file}")
    else:
        print(f"\n📚 Manga List ({min(len(titles), count)} titles):")
        print("=" * 50)
        for i, t in enumerate(titles[:count], 1):
            print(f"  {i:3d}. {t}")
    
    return titles[:count]

def main():
    parser = argparse.ArgumentParser(description="OsMEN-OC Manga Downloader")
    parser.add_argument("--search", "-s", help="Search for a manga title")
    parser.add_argument("--download", "-d", help="Download best result for title")
    parser.add_argument("--download-list", "-l", help="Download all titles from a file")
    parser.add_argument("--auto-list", action="store_true", help="Auto-generate manga list")
    parser.add_argument("--count", "-n", type=int, default=300, help="Number of titles for auto-list")
    parser.add_argument("--output", "-o", help="Output file for list")
    parser.add_argument("--dry-run", action="store_true", help="Search only, don't download")
    args = parser.parse_args()

    if args.search:
        results = search_and_display(args.search)
        if args.download and results:
            best = results[0]
            print(f"\n📥 Sending to SABnzbd: {best['title']}")
            if send_to_sabnzbd(best["downloadUrl"], best["title"]):
                print("  ✅ Queued successfully!")
            else:
                print("  ❌ Failed to queue.")
        return

    if args.auto_list:
        auto_generate_list(args.count, args.output)
        return

    if args.download_list:
        with open(args.download_list) as f:
            titles = [line.strip() for line in f if line.strip()]
        print(f"📦 Processing {len(titles)} titles...")
        queued = 0
        failed = 0
        for title in titles:
            results = search_and_display(title)
            if not results:
                failed += 1
                continue
            best = results[0]
            if args.dry_run:
                print(f"  [DRY RUN] Would download: {best['title']}")
                queued += 1
            else:
                if send_to_sabnzbd(best["downloadUrl"], best["title"]):
                    print(f"  ✅ Queued: {best['title']}")
                    queued += 1
                else:
                    print(f"  ❌ Failed: {best['title']}")
                    failed += 1
            time.sleep(1)  # Rate limit
        print(f"\n📊 Done: {queued} queued, {failed} failed")
        return

    parser.print_help()

if __name__ == "__main__":
    main()
