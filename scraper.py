"""
KNBSB Hoofdklasse Stats Scraper – vereenvoudigd
Schrijft alleen data/stats.json en data/meta.json.
Draait via GitHub Actions.
"""

import json
import os
import re
import time
from datetime import datetime, timezone

import requests

BASE = "https://stats.knbsbstats.nl/api/v1/stats/events/2026-lucky-day-hoofdklasse"
DATA = "data"
os.makedirs(DATA, exist_ok=True)

HEADERS = {
    "Accept": "application/json",
    "Referer": "https://stats.knbsbstats.nl/en/events/2026-lucky-day-hoofdklasse/stats",
    "User-Agent": "Mozilla/5.0 (compatible; HoofdklasseBot/2.0)",
}

STAT_SECTIONS = ["batting", "pitching", "fielding"]


def clean_name(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return " ".join(text.split()).strip()


def fetch(url: str, params: dict = None) -> dict | None:
    for attempt in range(3):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            print(f"  ⚠ Poging {attempt+1} mislukt ({url}): {e}")
            time.sleep(2 ** attempt)
    return None


def clean_players(data: list) -> list:
    out = []
    for row in data:
        row = dict(row)
        row["name"] = clean_name(row.get("name", ""))
        link = row.get("link", "")
        m = re.search(r"/players/(\d+)$", link)
        row["player_id"] = m.group(1) if m else None
        out.append(row)
    return out


def annotate_headers(headers: list) -> list:
    for h in headers:
        if h.get("format"):
            h["format_type"] = "baseball_pct"
    return headers


def scrape_section(section: str) -> dict | None:
    params = {
        "section": "players",
        "stats-section": section,
        "language": "en",
    }
    result = fetch(f"{BASE}/index", params)
    if not result:
        return None
    return {
        "data":    clean_players(result.get("data", [])),
        "headers": annotate_headers(result.get("headers", [])),
    }


def main():
    print(f"\nHoofdklasse Scraper — {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}\n")

    all_stats = {}
    for section in STAT_SECTIONS:
        print(f"  {section}…")
        result = scrape_section(section)
        if result:
            all_stats[section] = result
            print(f"    {len(result['data'])} rijen")
        else:
            print(f"    ⚠ Geen data")
        time.sleep(0.5)

    meta = {
        "last_updated":  datetime.now(timezone.utc).isoformat(),
        "source":        BASE,
        "season":        "Lucky Day Hoofdklasse 2026",
        "player_counts": {s: len(v["data"]) for s, v in all_stats.items()},
    }

    with open(f"{DATA}/stats.json", "w", encoding="utf-8") as f:
        json.dump(all_stats, f, ensure_ascii=False, indent=2)
    with open(f"{DATA}/meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    total = sum(len(v["data"]) for v in all_stats.values())
    print(f"\n✅ Klaar ({total} totaal rijen)\n")


if __name__ == "__main__":
    main()
