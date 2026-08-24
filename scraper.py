#!/usr/bin/env python3
"""
KNBSB Hoofdklasse Stats Scraper
Identieke aanpak als de werkende Czech Extraliga scraper:
requests eerst, Playwright-fallback bij 403.
"""
import json
import os
import re
import sys
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Proxy (optioneel)
# ---------------------------------------------------------------------------
PROXY_URL = os.environ.get("PROXY_URL", "").strip() or None
REQUEST_PROXIES = {"http": PROXY_URL, "https": PROXY_URL} if PROXY_URL else None

# ---------------------------------------------------------------------------
# Configuratie
# ---------------------------------------------------------------------------
EVENT      = "2026-lucky-day-hoofdklasse"
LANGUAGE   = "en"
BASE_URL   = f"https://stats.knbsbstats.nl/api/v1/stats/events/{EVENT}/index"
STATS_PAGE = f"https://stats.knbsbstats.nl/en/events/{EVENT}/stats"
OUTPUT_DIR = Path(__file__).parent / "data"
SECTIES    = ["batting", "pitching", "fielding"]

BROWSER_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": STATS_PAGE,
    "X-Requested-With": "XMLHttpRequest",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
}
TIMEOUT = 30

STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
window.chrome = { runtime: {} };
const origQuery = window.navigator.permissions && window.navigator.permissions.query;
if (origQuery) {
    window.navigator.permissions.query = (params) => (
        params.name === 'notifications'
            ? Promise.resolve({ state: Notification.permission })
            : origQuery(params)
    );
}
"""

# ---------------------------------------------------------------------------
# URL-opbouw
# ---------------------------------------------------------------------------
def bouw_url(sectie: str) -> str:
    params = {
        "section": "players",
        "stats-section": sectie,
        "team": "",
        "round": "",
        "split": "",
        "language": LANGUAGE,
    }
    return BASE_URL + "?" + urllib.parse.urlencode(params)

# ---------------------------------------------------------------------------
# Naam opschonen
# ---------------------------------------------------------------------------
def schoon_naam(raw: str) -> str:
    if not raw:
        return ""
    txt = re.sub(r"<br\s*/?>", " ", raw)
    txt = re.sub(r"<[^>]+>", "", txt)
    return " ".join(txt.split())

def verwerk_payload(payload: dict) -> dict:
    data    = payload.get("data") or []
    headers = payload.get("headers") or []
    for rij in data:
        if "name" in rij:
            rij["name"] = schoon_naam(str(rij["name"]))
    return {"data": data, "headers": headers}

# ---------------------------------------------------------------------------
# Strategie 1: requests
# ---------------------------------------------------------------------------
def haal_via_requests(sessie: requests.Session, sectie: str) -> dict:
    resp = sessie.get(
        bouw_url(sectie), headers=BROWSER_HEADERS, timeout=TIMEOUT, proxies=REQUEST_PROXIES
    )
    resp.raise_for_status()
    return verwerk_payload(resp.json())

# ---------------------------------------------------------------------------
# Strategie 2: Playwright-fallback
# ---------------------------------------------------------------------------
def _playwright_proxy_config():
    if not PROXY_URL:
        return None
    parsed = urllib.parse.urlsplit(PROXY_URL)
    server = f"{parsed.scheme}://{parsed.hostname}" + (f":{parsed.port}" if parsed.port else "")
    config = {"server": server}
    if parsed.username:
        config["username"] = urllib.parse.unquote(parsed.username)
    if parsed.password:
        config["password"] = urllib.parse.unquote(parsed.password)
    return config

def _fetch_sectie_met_retries(page, sectie: str, pogingen: int = 3):
    laatste_fout = None
    for poging in range(1, pogingen + 1):
        url = bouw_url(sectie)
        try:
            payload = page.evaluate(
                """async (url) => {
                    const r = await fetch(url, {
                        headers: { 'Accept': 'application/json',
                                   'X-Requested-With': 'XMLHttpRequest' },
                        credentials: 'same-origin'
                    });
                    if (!r.ok) throw new Error('HTTP ' + r.status);
                    return await r.json();
                }""",
                url,
            )
            return verwerk_payload(payload)
        except Exception as e:
            laatste_fout = e
            print(f"    poging {poging}/{pogingen} voor {sectie} mislukt: {e}", file=sys.stderr)
            if poging < pogingen:
                page.wait_for_timeout(3_000 * poging)
    raise laatste_fout

def haal_alles_via_playwright() -> dict:
    from playwright.sync_api import sync_playwright
    max_pogingen = 2
    laatste_fout = None
    for poging in range(1, max_pogingen + 1):
        try:
            with sync_playwright() as p:
                proxy_config = _playwright_proxy_config()
                browser = p.chromium.launch(
                    headless=True,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-features=IsolateOrigins,site-per-process",
                    ],
                    proxy=proxy_config,
                )
                context = browser.new_context(
                    user_agent=BROWSER_HEADERS["User-Agent"],
                    locale="en-US",
                    viewport={"width": 1366, "height": 900},
                    extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
                )
                context.add_init_script(STEALTH_INIT_SCRIPT)
                page = context.new_page()
                print(f"  Playwright (poging {poging}/{max_pogingen}): stats-pagina laden...", flush=True)
                resp = page.goto(STATS_PAGE, wait_until="domcontentloaded", timeout=60_000)
                status = resp.status if resp else None
                print(f"  paginastatus: {status}", flush=True)
                page.wait_for_timeout(6_000)
                resultaat = {}
                for sectie in SECTIES:
                    print(f"  Playwright fetch: {sectie}...", flush=True)
                    resultaat[sectie] = _fetch_sectie_met_retries(page, sectie)
                    print(f"  {sectie}: {len(resultaat[sectie]['data'])} spelers")
                browser.close()
                return resultaat
        except Exception as e:
            laatste_fout = e
            print(f"  Playwright-poging {poging}/{max_pogingen} mislukt: {e}", file=sys.stderr)
            if poging < max_pogingen:
                import time
                time.sleep(10)
    raise laatste_fout

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stats     = {}
    fouten    = []
    geblokkeerd = False

    # Poging 1: requests
    sessie = requests.Session()
    for sectie in SECTIES:
        try:
            print(f"requests: {sectie}...", flush=True)
            stats[sectie] = haal_via_requests(sessie, sectie)
            print(f"  {len(stats[sectie]['data'])} spelers")
        except requests.HTTPError as e:
            code = e.response.status_code if e.response is not None else "?"
            print(f"  HTTP {code} bij {sectie}", file=sys.stderr)
            if code in (403, 429, 503):
                geblokkeerd = True
                break
            fouten.append(f"{sectie}: {e}")
        except Exception as e:
            fouten.append(f"{sectie}: {e}")
            print(f"  Fout bij {sectie}: {e}", file=sys.stderr)

    # Poging 2: Playwright-fallback
    if geblokkeerd or len(stats) < len(SECTIES):
        print("Fallback naar Playwright...", flush=True)
        try:
            stats  = haal_alles_via_playwright()
            fouten = []
        except Exception as e:
            fouten.append(f"playwright: {e}")
            print(f"  Playwright mislukt: {e}", file=sys.stderr)

    if not stats:
        print("Alle strategieen mislukt.", file=sys.stderr)
        return 1

    # Bestaande stats.json inlezen voor failsafe
    stats_pad  = OUTPUT_DIR / "stats.json"
    oude_stats = None
    if stats_pad.exists():
        try:
            oude_stats = json.loads(stats_pad.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Ontbrekende secties aanvullen
    for sectie in SECTIES:
        if sectie not in stats and oude_stats and sectie in oude_stats:
            stats[sectie] = oude_stats[sectie]
            print(f"  {sectie}: oude data hergebruikt")

    # Wijzigingsdetectie
    data_gewijzigd = True
    if oude_stats:
        nieuw = {s: stats.get(s, {}).get("data") for s in SECTIES}
        oud   = {s: oude_stats.get(s, {}).get("data") for s in SECTIES}
        data_gewijzigd = nieuw != oud

    # Meta
    meta_pad          = OUTPUT_DIR / "meta.json"
    oude_last_updated = None
    if meta_pad.exists():
        try:
            oude_last_updated = json.loads(meta_pad.read_text(encoding="utf-8")).get("last_updated")
        except Exception:
            pass

    nu   = datetime.now(timezone.utc).isoformat()
    meta = {
        "last_checked":         nu,
        "last_updated":         nu if (data_gewijzigd or not oude_last_updated) else oude_last_updated,
        "data_changed_this_run": data_gewijzigd,
        "event":                EVENT,
        "source":               STATS_PAGE,
        "counts":               {s: len(stats.get(s, {}).get("data", [])) for s in SECTIES},
        "errors":               fouten,
    }

    (OUTPUT_DIR / "stats.json").write_text(
        json.dumps(stats, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    (OUTPUT_DIR / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    status_txt = "nieuwe data" if data_gewijzigd else "geen wijzigingen"
    print(f"Klaar — {status_txt}. Counts: {meta['counts']}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
