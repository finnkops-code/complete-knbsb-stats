"""
KNBSB Hoofdklasse Stats Scraper – API versie
Roept de JSON API rechtstreeks aan, geen browser nodig.
Resultaten worden opgeslagen in /data als JSON.
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

TEAMS = {
    "Amsterdam Pirates":                           "39583",
    "Curaçao Neptunus":                            "39587",
    "HCAW":                                        "39584",
    "Kinheim":                                     "39586",
    "Worldwide Pharma Logistics Hoofddorp Pioniers":"39585",
    "Oosterhout Twins":                            "39588",
    "UVV":                                         "39589",
}

SPLITS = [
    "", "last3", "last5", "last7", "home", "away",
    "day", "night",
    "0outs", "1out", "2outs",
    "vsleft", "vsright",
    "empty", "runner1", "runner2", "runner3",
    "runners12", "runners13", "runners23", "loaded",
    "scoring", "behind", "ahead",
]

STAT_SECTIONS = ["batting", "pitching", "fielding"]


def clean_name(html: str) -> str:
    """Verwijder HTML-tags uit naam-veld."""
    text = re.sub(r"<[^>]+>", " ", html)
    return " ".join(text.split()).strip()


def fetch(url: str, params: dict = None) -> dict | None:
    """Doe een GET-verzoek met retry."""
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
    """Maak namen leesbaar en voeg een 'player_id' veld toe."""
    out = []
    for row in data:
        row = dict(row)
        row["name"] = clean_name(row.get("name", ""))
        # Haal player-id uit de link
        link = row.get("link", "")
        m = re.search(r"/players/(\d+)$", link)
        row["player_id"] = m.group(1) if m else None
        out.append(row)
    return out


def scrape_section(section: str, team: str = "", split: str = "",
                   round_: str = "") -> dict | None:
    """Haal één stats-sectie op."""
    params = {
        "section": "players",
        "stats-section": section,
        "team": team,
        "round": round_,
        "split": split,
        "language": "en",
    }
    result = fetch(f"{BASE}/index", params)
    if not result:
        return None
    return {
        "data": clean_players(result.get("data", [])),
        "headers": result.get("headers", []),
    }


def scrape_all_stats():
    """Scrape batting/pitching/fielding voor alle teams + splits."""
    print("📊 Scraping stats (alle teams, alle secties)…")
    all_stats = {}

    for section in STAT_SECTIONS:
        print(f"  ↳ {section}…")
        result = scrape_section(section)
        if result:
            all_stats[section] = result
        time.sleep(0.5)

    # Sla op
    with open(f"{DATA}/stats.json", "w", encoding="utf-8") as f:
        json.dump(all_stats, f, ensure_ascii=False, indent=2)
    print(f"  ✅ stats.json ({sum(len(v['data']) for v in all_stats.values())} rijen)")
    return all_stats


def scrape_per_team():
    """Scrape alle stats per team apart."""
    print("👕 Scraping per team…")
    os.makedirs(f"{DATA}/teams", exist_ok=True)
    team_index = []

    for name, team_id in TEAMS.items():
        safe = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        team_data = {"name": name, "id": team_id, "sections": {}}

        for section in STAT_SECTIONS:
            result = scrape_section(section, team=team_id)
            if result:
                team_data["sections"][section] = result
            time.sleep(0.3)

        path = f"{DATA}/teams/{safe}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(team_data, f, ensure_ascii=False, indent=2)
        team_index.append({"name": name, "id": team_id, "file": f"teams/{safe}.json"})
        print(f"  ✅ {name}")

    with open(f"{DATA}/teams/index.json", "w", encoding="utf-8") as f:
        json.dump(team_index, f, ensure_ascii=False, indent=2)


def scrape_splits():
    """Scrape batting per split (thuis/uit/laatste N)."""
    print("🔀 Scraping splits…")
    interesting_splits = [
        ("last3", "Last 3 Games"),
        ("last5", "Last 5 Games"),
        ("last7", "Last 7 Games"),
        ("home",  "Home games"),
        ("away",  "Away games"),
    ]
    splits_data = {}

    for split_val, split_label in interesting_splits:
        result = scrape_section("batting", split=split_val)
        if result:
            splits_data[split_val] = {"label": split_label, **result}
        time.sleep(0.4)

    with open(f"{DATA}/splits.json", "w", encoding="utf-8") as f:
        json.dump(splits_data, f, ensure_ascii=False, indent=2)
    print(f"  ✅ splits.json ({len(splits_data)} splits)")


def scrape_standings():
    """Haal de stand op via de aparte standings URL."""
    print("🏆 Scraping standings…")
    url = "https://stats.knbsbstats.nl/api/v1/events/2026-lucky-day-hoofdklasse/standings"
    result = fetch(url)
    if not result:
        # Fallback: probeer alternatieve URL
        result = fetch(f"{BASE}/standings")
    if result:
        with open(f"{DATA}/standings.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print("  ✅ standings.json")
    else:
        print("  ⚠ Standings niet beschikbaar via API")
        # Schrijf leeg bestand zodat front-end niet crasht
        with open(f"{DATA}/standings.json", "w") as f:
            json.dump({}, f)


def write_meta(stats: dict):
    meta = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "source": "https://stats.knbsbstats.nl/api/v1/stats/events/2026-lucky-day-hoofdklasse/",
        "season": "2026 Lucky Day Hoofdklasse",
        "player_counts": {s: len(v["data"]) for s, v in stats.items()},
        "api_params": {
            "stat_sections": STAT_SECTIONS,
            "teams": TEAMS,
        },
    }
    with open(f"{DATA}/meta.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    print(f"  ✅ meta.json")


def main():
    print(f"\n🚀 KNBSB Hoofdklasse Scraper — {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}\n")
    stats    = scrape_all_stats()
    scrape_per_team()
    scrape_splits()
    scrape_standings()
    write_meta(stats)
    print("\n✅ Klaar! Alle data staat in /data/\n")


if __name__ == "__main__":
    main()
