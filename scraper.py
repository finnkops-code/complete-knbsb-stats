"""
KNBSB Hoofdklasse Stats Scraper – automatische slug detectie
Detecteert automatisch het actieve baseball event op stats.knbsbstats.nl
zodat je de slug nooit handmatig hoeft aan te passen.
"""

import json
import os
import re
import time
from datetime import datetime, timezone

import requests

CALENDAR_URL = "https://stats.knbsbstats.nl/api/v1/events?language=en"
API_BASE     = "https://stats.knbsbstats.nl/api/v1/stats/events"
DATA         = "data"
os.makedirs(DATA, exist_ok=True)

HEADERS = {
    "Accept":     "application/json",
    "Referer":    "https://stats.knbsbstats.nl/en/calendar",
    "User-Agent": "Mozilla/5.0 (compatible; HoofdklasseBot/2.0)",
}

STAT_SECTIONS = ["batting", "pitching", "fielding"]

KEYWORDS = ["hoofdklasse", "honkbal", "lucky-day", "baseball"]
EXCLUDE  = ["softbal", "softball", "vrouwen", "women", "jeugd", "youth"]


def find_active_slug():
    """Detecteer automatisch de actieve slug via de API of HTML kalender."""
    print("  Zoeken naar actieve slug...")

    # Probeer API kalender
    try:
        r = requests.get(CALENDAR_URL, headers=HEADERS, timeout=15)
        if r.status_code == 200:
            data = r.json()
            events = data if isinstance(data, list) else (
                data.get("events") or data.get("data") or []
            )
            candidates = []
            for ev in events:
                slug   = ev.get("slug") or ev.get("id") or ""
                name   = (ev.get("name") or ev.get("title") or "").lower()
                slug_l = slug.lower()
                if any(k in slug_l or k in name for k in KEYWORDS) \
                        and not any(x in slug_l or x in name for x in EXCLUDE):
                    candidates.append(slug)
                    print(f"    Kandidaat: {slug}")
            if candidates:
                candidates.sort(reverse=True)
                print(f"  Gekozen: {candidates[0]}")
                return candidates[0]
    except Exception as e:
        print(f"  API kalender mislukt: {e}")

    # Fallback: HTML kalender
    try:
        r = requests.get(
            "https://stats.knbsbstats.nl/en/calendar",
            headers={**HEADERS, "Accept": "text/html"},
            timeout=15
        )
        if r.status_code == 200:
            slugs = list(set(re.findall(r'/events/([\w-]+)/stats', r.text)))
            candidates = [s for s in slugs
                          if any(k in s.lower() for k in KEYWORDS)
                          and not any(x in s.lower() for x in EXCLUDE)]
            if candidates:
                candidates.sort(reverse=True)
                print(f"  Gekozen (HTML): {candidates[0]}")
                return candidates[0]
    except Exception as e:
        print(f"  HTML kalender mislukt: {e}")

    # Laatste fallback
    year = datetime.now(timezone.utc).year
    fallback = f"{year}-lucky-day-hoofdklasse"
    print(f"  Fallback: {fallback}")
    return fallback


def clean_name(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split()).strip()


def fetch(url, params=None):
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"  Poging {attempt+1} mislukt: {e}")
            time.sleep(2 ** attempt)
    return None


def clean_players(data):
    out = []
    for row in data:
        row = dict(row)
        row["name"] = clean_name(row.get("name", ""))
        m = re.search(r"/players/(\d+)$", row.get("link", ""))
        row["player_id"] = m.group(1) if m else None
        out.append(row)
    return out


def annotate_headers(headers):
    for h in headers:
        if h.get("format"):
            h["format_type"] = "baseball_pct"
    return headers


def scrape_section(base, section):
    result = fetch(f"{base}/index", {
        "section": "players", "stats-section": section, "language": "en"
    })
    if not result:
        return None
    return {
        "data":    clean_players(result.get("data", [])),
        "headers": annotate_headers(result.get("headers", [])),
    }


def main():
    print(f"\nHoofdklasse Scraper — {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}\n")

    slug = find_active_slug()
    base = f"{API_BASE}/{slug}"
    print(f"  Base: {base}\n")

    all_stats = {}
    for section in STAT_SECTIONS:
        print(f"  {section}...")
        result = scrape_section(base, section)
        if result:
            all_stats[section] = result
            print(f"    {len(result['data'])} rijen")
        else:
            print(f"    Geen data")
        time.sleep(0.5)

    meta = {
        "last_updated":  datetime.now(timezone.utc).isoformat(),
        "source":        base,
        "slug":          slug,
        "season":        f"Lucky Day Hoofdklasse {datetime.now(timezone.utc).year}",
        "player_counts": {s: len(v["data"]) for s, v in all_stats.items()},
    }

    with open(f"{DATA}/stats.json", "w", encoding="utf-8") as f:
        json.dump(all_stats, f, ensure_ascii=False, indent=2)
    with open(f"{DATA}/meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\nKlaar — {sum(len(v['data']) for v in all_stats.values())} rijen via '{slug}'\n")


if __name__ == "__main__":
    main()
