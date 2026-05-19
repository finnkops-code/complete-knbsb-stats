"""
KNBSB Hoofdklasse Stats Scraper
Haalt batting, pitching en fielding stats op via Playwright (JS-rendered)
en slaat alles op als JSON in de /data map.
"""

import json
import os
import re
import time
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright

BASE_URL = "https://stats.knbsbstats.nl/en/events/2026-lucky-day-hoofdklasse"
DATA_DIR = "data"

TEAMS = {
    "Amsterdam Pirates": "39583",
    "Curaçao Neptunus": "39587",
    "HCAW": "39584",
    "Kinheim": "39586",
    "Worldwide Pharma Logistics Hoofddorp Pioniers": "39585",
    "Oosterhout Twins": "39588",
    "UVV": "39589",
}

SPLITS = [
    "All Splits",
    "Last 3 Games",
    "Last 5 Games",
    "Last 7 Games",
    "Home games",
    "Away games",
]

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(f"{DATA_DIR}/teams", exist_ok=True)


def wait_for_table(page, timeout=15000):
    """Wacht tot een stats-tabel zichtbaar is."""
    try:
        page.wait_for_selector("table tbody tr", timeout=timeout)
        page.wait_for_timeout(800)  # Extra wacht voor lazy-loaded data
    except Exception:
        pass


def parse_table(page, label):
    """Haal alle rijen + headers uit een visible tabel."""
    try:
        tables = page.query_selector_all("table")
        results = []
        for table in tables:
            headers = [th.inner_text().strip() for th in table.query_selector_all("thead th")]
            if not headers:
                continue
            rows = []
            for tr in table.query_selector_all("tbody tr"):
                cells = [td.inner_text().strip() for td in tr.query_selector_all("td")]
                if cells and len(cells) == len(headers):
                    rows.append(dict(zip(headers, cells)))
            if rows:
                results.append({"label": label, "headers": headers, "rows": rows})
        return results
    except Exception as e:
        print(f"  ⚠️  Fout bij parsen tabel '{label}': {e}")
        return []


def click_tab(page, tab_text):
    """Klik op een tab-knop (Batting / Pitching / Fielding)."""
    try:
        tab = page.get_by_role("tab", name=re.compile(tab_text, re.IGNORECASE))
        if not tab.count():
            tab = page.locator(f"text={tab_text}").first
        tab.click()
        page.wait_for_timeout(1200)
    except Exception as e:
        print(f"  ⚠️  Kon tab '{tab_text}' niet klikken: {e}")


def select_filter(page, filter_name, value):
    """Selecteer een filter (Team / Split) via de dropdown."""
    try:
        # Probeer select-element
        sel = page.locator(f"select:near(:text('{filter_name}'))").first
        if sel.count():
            sel.select_option(label=value)
            page.wait_for_timeout(1000)
            return True
        # Probeer listbox / dropdown-knop
        btn = page.locator(f"button:has-text('{filter_name}'), [aria-label*='{filter_name}']").first
        if btn.count():
            btn.click()
            page.wait_for_timeout(500)
            option = page.locator(f"text={value}").first
            option.click()
            page.wait_for_timeout(1200)
            return True
    except Exception:
        pass
    return False


def scrape_stats_page(page):
    """Scrape alle stats-tabbladen op de stats-pagina."""
    page.goto(f"{BASE_URL}/stats", wait_until="networkidle", timeout=30000)
    wait_for_table(page)

    all_data = {
        "batting": [],
        "pitching": [],
        "fielding": [],
    }

    for tab in ["Batting", "Pitching", "Fielding"]:
        click_tab(page, tab)
        wait_for_table(page)
        tables = parse_table(page, f"All Teams - All Rounds - {tab}")
        all_data[tab.lower()].extend(tables)

    return all_data


def scrape_team_stats(page, team_name, team_id):
    """Scrape stats per team."""
    url = f"{BASE_URL}/teams/{team_id}"
    try:
        page.goto(url, wait_until="networkidle", timeout=30000)
        wait_for_table(page)
        data = {"team": team_name, "id": team_id, "batting": [], "pitching": [], "fielding": []}
        for tab in ["Batting", "Pitching", "Fielding"]:
            click_tab(page, tab)
            wait_for_table(page)
            tables = parse_table(page, f"{team_name} - {tab}")
            data[tab.lower()].extend(tables)
        return data
    except Exception as e:
        print(f"  ⚠️  Fout bij team {team_name}: {e}")
        return None


def scrape_standings(page):
    """Haal de standenlijst op."""
    page.goto(f"{BASE_URL}/standings", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    tables = parse_table(page, "Standings")
    return tables


def scrape_schedule(page):
    """Haal speelschema + resultaten op."""
    page.goto(f"{BASE_URL}/schedule-and-results", wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(2000)
    # Probeer wedstrijden via tekst te scrapen
    games = []
    try:
        rows = page.query_selector_all(".game-row, .schedule-row, tr[data-game-id], .event-row")
        for row in rows:
            text = row.inner_text().strip()
            if text:
                games.append({"raw": text})
    except Exception:
        pass
    tables = parse_table(page, "Schedule")
    return {"tables": tables, "games": games}


def scrape_leaderboard(page):
    """Haal de leaderboard op (top spelers per categorie)."""
    page.goto(f"{BASE_URL}/stats", wait_until="networkidle", timeout=30000)
    wait_for_table(page)
    # Zoek Leader board tab
    try:
        lb_tab = page.locator("text=Leader board, text=Leaderboard").first
        if lb_tab.count():
            lb_tab.click()
            page.wait_for_timeout(1500)
    except Exception:
        pass
    tables = parse_table(page, "Leaderboard")
    return tables


def main():
    print(f"🚀 Start scrapen – {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (compatible; HoofdklasseBot/1.0)",
        )
        page = ctx.new_page()

        # ── Standings ──────────────────────────────────────────────
        print("📋 Scraping standings...")
        standings = scrape_standings(page)
        with open(f"{DATA_DIR}/standings.json", "w", encoding="utf-8") as f:
            json.dump(standings, f, ensure_ascii=False, indent=2)

        # ── Algemene stats ─────────────────────────────────────────
        print("📊 Scraping algemene stats...")
        general_stats = scrape_stats_page(page)
        with open(f"{DATA_DIR}/stats.json", "w", encoding="utf-8") as f:
            json.dump(general_stats, f, ensure_ascii=False, indent=2)

        # ── Leaderboard ────────────────────────────────────────────
        print("🏆 Scraping leaderboard...")
        leaderboard = scrape_leaderboard(page)
        with open(f"{DATA_DIR}/leaderboard.json", "w", encoding="utf-8") as f:
            json.dump(leaderboard, f, ensure_ascii=False, indent=2)

        # ── Schedule ───────────────────────────────────────────────
        print("📅 Scraping schedule...")
        schedule = scrape_schedule(page)
        with open(f"{DATA_DIR}/schedule.json", "w", encoding="utf-8") as f:
            json.dump(schedule, f, ensure_ascii=False, indent=2)

        # ── Per team ───────────────────────────────────────────────
        team_summary = []
        for team_name, team_id in TEAMS.items():
            print(f"⚾  Scraping team: {team_name}...")
            team_data = scrape_team_stats(page, team_name, team_id)
            if team_data:
                safe_name = team_name.lower().replace(" ", "_").replace("ç", "c")
                with open(f"{DATA_DIR}/teams/{safe_name}.json", "w", encoding="utf-8") as f:
                    json.dump(team_data, f, ensure_ascii=False, indent=2)
                team_summary.append({"name": team_name, "id": team_id, "file": f"teams/{safe_name}.json"})

        # ── Meta / index ───────────────────────────────────────────
        meta = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "source": BASE_URL,
            "season": "2026 Lucky Day Hoofdklasse",
            "teams": team_summary,
            "files": {
                "standings": "standings.json",
                "stats": "stats.json",
                "leaderboard": "leaderboard.json",
                "schedule": "schedule.json",
            },
        }
        with open(f"{DATA_DIR}/meta.json", "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        ctx.close()
        browser.close()

    print(f"✅ Klaar! Data opgeslagen in /{DATA_DIR}/")


if __name__ == "__main__":
    main()
