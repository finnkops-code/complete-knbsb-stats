"""
DBL EasyScore Stats Scraper
Draait via GitHub Actions, slaat resultaten op in data/stats.json
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

API_BASE  = "https://api.easyscore.com/v2/stats"
YEAR      = 2026
LEAGUE_ID = 10147
DATA      = "data"
BASE = "https://stats.knbsbstats.nl/api/v1/stats/events/2026-lucky-day-hoofdklasse"
DATA = "data"
os.makedirs(DATA, exist_ok=True)

API_HEADERS = {
    "Accept":          "*/*",
    "Content-Type":    "application/json",
    "Origin":          "https://www.easyscore.com",
    "Referer":         "https://www.easyscore.com/",
    "X-Api-Key":       os.environ.get("EASYSCORE_API_KEY", "urxiKaOhuH6keoQBwC74a2mi0nsgcAkJ1VBlkIK6"),
    "User-Agent":      "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept-Language": "nl-NL,nl;q=0.9,en-US;q=0.8,en;q=0.7",
HEADERS = {
    "Accept": "application/json",
    "Referer": "https://stats.knbsbstats.nl/en/events/2026-lucky-day-hoofdklasse/stats",
    "User-Agent": "Mozilla/5.0 (compatible; HoofdklasseBot/2.0)",
}

CATEGORIES = {
    "batting":  "off",
    "pitching": "pit",
    "fielding": "fld",
TEAMS = {
    "Amsterdam Pirates":                           "39583",
    "Curaçao Neptunus":                            "39587",
    "HCAW":                                        "39584",
    "Kinheim":                                     "39586",
    "Worldwide Pharma Logistics Hoofddorp Pioniers":"39585",
    "Oosterhout Twins":                            "39588",
    "UVV":                                         "39589",
}

BATTING_HEADERS = [
    {"column":"Player",  "label":"Player",  "tooltip":"",                             "format":False},
    {"column":"Teamname","label":"Team",    "tooltip":"",                             "format":False},
    {"column":"G",       "label":"G",       "tooltip":"Games played",                 "format":False},
    {"column":"PA",      "label":"PA",      "tooltip":"Plate Appearances",            "format":False},
    {"column":"AB",      "label":"AB",      "tooltip":"At Bats",                      "format":False},
    {"column":"R",       "label":"R",       "tooltip":"Runs scored",                  "format":False},
    {"column":"H",       "label":"H",       "tooltip":"Hits",                         "format":False},
    {"column":"RBI",     "label":"RBI",     "tooltip":"Runs Batted In",               "format":False},
    {"column":"HR",      "label":"HR",      "tooltip":"Home Runs",                    "format":False},
    {"column":"2B",      "label":"2B",      "tooltip":"Doubles",                      "format":False},
    {"column":"3B",      "label":"3B",      "tooltip":"Triples",                      "format":False},
    {"column":"TB",      "label":"TB",      "tooltip":"Total Bases",                  "format":False},
    {"column":"SB",      "label":"SB",      "tooltip":"Stolen Bases",                 "format":False},
    {"column":"BB",      "label":"BB",      "tooltip":"Walks",                        "format":False},
    {"column":"SO",      "label":"SO",      "tooltip":"Strikeouts",                   "format":False},
    {"column":"HBP",     "label":"HBP",     "tooltip":"Hit by Pitch",                 "format":False},
    {"column":"BA",      "label":"BA",      "tooltip":"Batting Average",              "format":False},
    {"column":"OBP",     "label":"OBP",     "tooltip":"On Base Percentage",           "format":False},
    {"column":"SLG",     "label":"SLG",     "tooltip":"Slugging Percentage",          "format":False},
    {"column":"OPS",     "label":"OPS",     "tooltip":"On Base + Slugging",           "format":False},
    {"column":"wOBA",    "label":"wOBA",    "tooltip":"Weighted On Base Average",     "format":False},
    {"column":"BABIP",   "label":"BABIP",   "tooltip":"Batting Avg on Balls in Play", "format":False},
    {"column":"ISO",     "label":"ISO",     "tooltip":"Isolated Power",               "format":False},
    {"column":"BBPct",   "label":"BB%",     "tooltip":"Walk Percentage",              "format":False},
    {"column":"SOPct",   "label":"SO%",     "tooltip":"Strikeout Percentage",         "format":False},
    {"column":"RC",      "label":"RC",      "tooltip":"Runs Created",                 "format":False},
    {"column":"RISP",    "label":"RISP",    "tooltip":"Runners in Scoring Position",  "format":False},
    {"column":"SBPct",   "label":"SB%",     "tooltip":"Stolen Base Percentage",       "format":False},
SPLITS = [
    "", "last3", "last5", "last7", "home", "away",
    "day", "night",
    "0outs", "1out", "2outs",
    "vsleft", "vsright",
    "empty", "runner1", "runner2", "runner3",
    "runners12", "runners13", "runners23", "loaded",
    "scoring", "behind", "ahead",
]

PITCHING_HEADERS = [
    {"column":"Player",   "label":"Player",  "tooltip":"",                              "format":False},
    {"column":"Teamname", "label":"Team",    "tooltip":"",                              "format":False},
    {"column":"G",        "label":"G",       "tooltip":"Games pitched",                 "format":False},
    {"column":"GS",       "label":"GS",      "tooltip":"Games started",                 "format":False},
    {"column":"W",        "label":"W",       "tooltip":"Wins",                          "format":False},
    {"column":"L",        "label":"L",       "tooltip":"Losses",                        "format":False},
    {"column":"SV",       "label":"SV",      "tooltip":"Saves",                         "format":False},
    {"column":"IP",       "label":"IP",      "tooltip":"Innings Pitched",               "format":False},
    {"column":"BF",       "label":"BF",      "tooltip":"Batters Faced",                 "format":False},
    {"column":"HA",       "label":"H",       "tooltip":"Hits Allowed",                  "format":False},
    {"column":"ER",       "label":"ER",      "tooltip":"Earned Runs",                   "format":False},
    {"column":"BBA",      "label":"BB",      "tooltip":"Walks Allowed",                 "format":False},
    {"column":"K",        "label":"K",       "tooltip":"Strikeouts",                    "format":False},
    {"column":"HRA",      "label":"HR",      "tooltip":"Home Runs Allowed",             "format":False},
    {"column":"HBPA",     "label":"HBP",     "tooltip":"Hit Batters",                   "format":False},
    {"column":"ERA",      "label":"ERA",     "tooltip":"Earned Run Average",            "format":False},
    {"column":"WHIP",     "label":"WHIP",    "tooltip":"Walks + Hits per Inning",       "format":False},
    {"column":"FIP",      "label":"FIP",     "tooltip":"Fielding Independent Pitching", "format":False},
    {"column":"K9",       "label":"K/9",     "tooltip":"Strikeouts per 9 innings",      "format":False},
    {"column":"BBA9",     "label":"BB/9",    "tooltip":"Walks per 9 innings",           "format":False},
    {"column":"HA9",      "label":"H/9",     "tooltip":"Hits per 9 innings",            "format":False},
    {"column":"KPct",     "label":"K%",      "tooltip":"Strikeout Percentage",          "format":False},
    {"column":"BBAPct",   "label":"BB%",     "tooltip":"Walk Percentage",               "format":False},
    {"column":"KBB",      "label":"K/BB",    "tooltip":"Strikeout to Walk Ratio",       "format":False},
    {"column":"OppAVG",   "label":"OppAVG",  "tooltip":"Opponent Batting Average",      "format":False},
    {"column":"OppOPS",   "label":"OppOPS",  "tooltip":"Opponent OPS",                  "format":False},
    {"column":"OppBABIP", "label":"OppBABIP","tooltip":"Opponent BABIP",                "format":False},
    {"column":"QS",       "label":"QS",      "tooltip":"Quality Starts",                "format":False},
    {"column":"WPct",     "label":"W%",      "tooltip":"Win Percentage",                "format":False},
]
STAT_SECTIONS = ["batting", "pitching", "fielding"]

FIELDING_HEADERS = [
    {"column":"Player",        "label":"Player","tooltip":"",                              "format":False},
    {"column":"Teamname",      "label":"Team",  "tooltip":"",                              "format":False},
    {"column":"G",             "label":"G",     "tooltip":"Games played",                  "format":False},
    {"column":"Chances",       "label":"TC",    "tooltip":"Total Chances",                 "format":False},
    {"column":"Putout",        "label":"PO",    "tooltip":"Putouts",                       "format":False},
    {"column":"Assist",        "label":"A",     "tooltip":"Assists",                       "format":False},
    {"column":"Error",         "label":"E",     "tooltip":"Errors",                        "format":False},
    {"column":"DP",            "label":"DP",    "tooltip":"Double Plays",                  "format":False},
    {"column":"FPct",          "label":"FPCT",  "tooltip":"Fielding Percentage",           "format":False},
    {"column":"RangeFactor",   "label":"RF",    "tooltip":"Range Factor",                  "format":False},
    {"column":"InningsPlayed", "label":"IP",    "tooltip":"Innings Played in Field",       "format":False},
    {"column":"GamesatC",      "label":"C",     "tooltip":"Games at Catcher",              "format":False},
    {"column":"Gamesat1B",     "label":"1B",    "tooltip":"Games at First Base",           "format":False},
    {"column":"Gamesat2B",     "label":"2B",    "tooltip":"Games at Second Base",          "format":False},
    {"column":"Gamesat3B",     "label":"3B",    "tooltip":"Games at Third Base",           "format":False},
    {"column":"GamesatSS",     "label":"SS",    "tooltip":"Games at Shortstop",            "format":False},
    {"column":"GamesatOF",     "label":"OF",    "tooltip":"Games in Outfield",             "format":False},
    {"column":"GamesatP",      "label":"P",     "tooltip":"Games at Pitcher",              "format":False},
    {"column":"PB",            "label":"PB",    "tooltip":"Passed Balls",                  "format":False},
    {"column":"SBAtt",         "label":"SBA",   "tooltip":"Stolen Base Attempts against",  "format":False},
    {"column":"CSMade",        "label":"CS",    "tooltip":"Caught Stealing",               "format":False},
    {"column":"CSPct",         "label":"CS%",   "tooltip":"Caught Stealing Percentage",    "format":False},
]

HEADERS_MAP = {
    "batting":  BATTING_HEADERS,
    "pitching": PITCHING_HEADERS,
    "fielding": FIELDING_HEADERS,
}
def clean_name(html: str) -> str:
    """Verwijder HTML-tags uit naam-veld."""
    text = re.sub(r"<[^>]+>", " ", html)
    return " ".join(text.split()).strip()


def fetch_stats(cat_val):
    url = (
        f"{API_BASE}?yr={YEAR}&leagueID={LEAGUE_ID}"
        f"&round=0&cat={cat_val}&subcat=ind&sortdir=desc&sortcol=&filter=all&_=1"
    )
def fetch(url: str, params: dict = None) -> dict | None:
    """Doe een GET-verzoek met retry."""
for attempt in range(3):
try:
            r = requests.get(url, headers=API_HEADERS, timeout=30)
            if r.status_code == 200:
                data = r.json()
                rows = data if isinstance(data, list) else (data.get("data") or data.get("players") or [])
                for row in rows:
                    pid = row.get("PlayerID") or row.get("playerID")
                    row["link"] = f"https://www.easyscore.com/players/{pid}" if pid else ""
                return rows
            print(f"    Fout: HTTP {r.status_code} — {r.text[:200]}")
            r = requests.get(url, params=params, headers=HEADERS, timeout=20)
            r.raise_for_status()
            return r.json()
except Exception as e:
            print(f"    Poging {attempt + 1} mislukt: {e}")
        time.sleep(2 ** attempt)
    return []


def main():
    print(f"\nDBL Scraper — {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}\n")

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


def annotate_headers(headers: list) -> list:
    """
    Voeg format_type toe aan headers zodat de display-laag weet hoe te formatteren.

    Baseball-conventie:
    - Percentage-velden (AVG, OBP, SLG, FLDP, etc.) komen als integer uit de API:
      bijv. 333 = .333 | 1050 = 1.050 (OPS kan > 1 zijn)
    - Weergave: altijd als decimaal met leidende punt (.333), nooit als %
    - De API markeert dit met format: true
    - Wij slaan de ruwe integer op en laten de display-laag delen door 1000
    """
    for h in headers:
        if h.get("format"):
            h["format_type"] = "baseball_pct"  # integer / 1000 → .333 notatie
    return headers


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
        "headers": annotate_headers(result.get("headers", [])),
    }


def scrape_all_stats():
    """Scrape batting/pitching/fielding voor alle teams + splits."""
    print("📊 Scraping stats (alle teams, alle secties)…")
all_stats = {}
    for cat_key, cat_val in CATEGORIES.items():
        print(f"  {cat_key} ({cat_val})…")
        rows = fetch_stats(cat_val)
        all_stats[cat_key] = {
            "headers": HEADERS_MAP[cat_key],
            "data":    rows,
        }
        print(f"    {len(rows)} rijen")

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

    total = sum(len(v["data"]) for v in all_stats.values())
    print(f"\n✅ stats.json geschreven ({total} totaal rijen)\n")

def main():
    print(f"\n🚀 KNBSB Hoofdklasse Scraper — {datetime.now(timezone.utc):%Y-%m-%d %H:%M UTC}\n")
    stats    = scrape_all_stats()
    scrape_per_team()
    scrape_splits()
    scrape_standings()
    write_meta(stats)
    print("\n✅ Klaar! Alle data staat in /data/\n")


if __name__ == "__main__":
