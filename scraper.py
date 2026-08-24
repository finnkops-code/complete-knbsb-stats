"""
KNBSB Hoofdklasse Stats Scraper – probeert meerdere slugs
Werkt automatisch voor regulier seizoen én playoffs.
"""

import json
import os
import re
import time
from datetime import datetime, timezone

import requests

API_BASE = "https://stats.knbsbstats.nl/api/v1/stats/events"
DATA     = "data"
os.makedirs(DATA, exist_ok=True)

HEADERS = {
    "Accept":     "application/json",
    "Referer":    "https://stats.knbsbstats.nl/en/calendar",
    "User-Agent": "Mozilla/5.0 (compatible; HoofdklasseBot/2.0)",
}

STAT_SECTIONS = ["batting", "pitching", "fielding"]

# Alle mogelijke slugs voor 2026, van meest naar minst waarschijnlijk
YEAR = datetime.now(timezone.utc).year
SLUG_CANDIDATES = [
    f"{YEAR}-lucky-day-hoofdklasse",
    f"{YEAR}-lucky-day-hoofdklasse-honkbal",
    f"{YEAR}-lucky-day-hoofdklasse-playoffs",
    f"{YEAR}-lucky-day-hoofdklasse-play-offs",
    f"{YEAR}-lucky-day-hoofdklasse-holland-series",
    f"{YEAR}-hoofdklasse-honkbal",
    f"{YEAR}-hoofdklasse-baseball",
    f"{YEAR}-knbsb-hoofdklasse",
]


def find_working_slug():
    """Probeer slugs één voor één totdat er data terugkomt."""
    print("  Zoeken naar werkende slug...")
    for slug in SLUG_CANDIDATES:
        url = f"{API_BASE}/{slug}/index"
        params = {"section": "players", "stats-section": "batting", "language": "en"}
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                rows = data.get("data", []) if isinstance(data, dict) else []
                if rows:
                    print(f"  Werkende slug gevonden: {slug} ({len(rows)} batting rijen)")
                    return slug
                else:
                    print(f"    {slug} → leeg")
            else:
                print(f"    {slug} → HTTP {r.status_code}")
        except Exception as e:
            print(f"    {slug} → fout: {e}")
        time.sleep(0.5)

    # Niets gevonden — gebruik de meest logische als fallback
    print(f"  Geen werkende slug gevonden, gebruik fallback: {SLUG_CANDIDATES[0]}")
    return SLUG_CANDIDATES[0]


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

    slug = find_working_slug()
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
        "season":        f"Lucky Day Hoofdklasse {YEAR}",
        "player_counts": {s: len(v["data"]) for s, v in all_stats.items()},
    }

    with open(f"{DATA}/stats.json", "w", encoding="utf-8") as f:
        json.dump(all_stats, f, ensure_ascii=False, indent=2)
    with open(f"{DATA}/meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\nKlaar — {sum(len(v['data']) for v in all_stats.values())} rijen via '{slug}'\n")


if __name__ == "__main__":
    main()
