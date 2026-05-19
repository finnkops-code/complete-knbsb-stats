# ⚾ Hoofdklasse Stats Dashboard

Volledig automatisch statistieken dashboard voor de KNBSB Honkbal Hoofdklasse 2026.

---

## 📁 Structuur

```
├── .github/
│   └── workflows/
│       └── scrape-stats.yml   ← GitHub Action (automatisch scrapen)
├── scraper.py                 ← Python scraper (Playwright)
├── data/                      ← Auto-gegenereerd door scraper
│   ├── meta.json
│   ├── stats.json
│   ├── standings.json
│   ├── schedule.json
│   └── teams/
│       ├── amsterdam_pirates.json
│       └── ...
└── elementor-widget.html      ← Plak dit in Elementor
```

---

## 🚀 Installatie

### Stap 1 — GitHub repository aanmaken

1. Maak een **nieuwe public repository** op GitHub (bijv. `hoofdklasse-stats`)
2. Upload alle bestanden naar de repo
3. Zorg dat de `data/` map bestaat (maak een leeg bestand `data/.gitkeep`)

### Stap 2 — GitHub Actions inschakelen

De scraper draait automatisch via `.github/workflows/scrape-stats.yml`:
- **Automatisch**: 4× per dag (06:00, 12:00, 18:00, 23:00 UTC)
- **Handmatig**: via Actions tab → "Run workflow"

Geen extra secrets nodig — de `GITHUB_TOKEN` is automatisch beschikbaar.

### Stap 3 — Elementor widget instellen

1. Open je WordPress pagina in Elementor
2. Voeg een **"HTML"** of **"Custom HTML"** widget toe
3. Plak de volledige inhoud van `elementor-widget.html`
4. Pas regel 3 aan (bovenaan het `<script>`):

```javascript
const DATA_URL = 'https://raw.githubusercontent.com/JOUW_GEBRUIKERSNAAM/JOUW_REPO/main/data/';
```

Vervang `JOUW_GEBRUIKERSNAAM` en `JOUW_REPO` door jouw GitHub gegevens.

5. Sla op en publiceer ✅

---

## 🔧 Eerste keer data laden

Voer de scraper handmatig uit via GitHub Actions:
1. Ga naar je repo → **Actions** tab
2. Klik op **"Scrape Hoofdklasse Stats"**
3. Klik **"Run workflow"** → **"Run workflow"**
4. Wacht ~3-5 minuten

Of lokaal testen:
```bash
pip install playwright
playwright install chromium
python scraper.py
```

---

## ✨ Features van het dashboard

| Feature | Beschrijving |
|---|---|
| 📊 Overzicht | Samenvattingskaarten + top batters & pitchers |
| 🏏 Batting | Volledige batting stats met sortering & paginering |
| ⚾ Pitching | Volledige pitching stats |
| 🧤 Fielding | Veldspel statistieken |
| 🏆 Stand | Reguliere competitie + winpercentage grafiek |
| 👕 Teams | Teamoverzicht met klikbare detail-view |
| 📅 Speelschema | Wedstrijden en resultaten |
| 🔍 Zoeken | Zoek op spelersnaam |
| 🔽 Filteren | Filter op team, split (thuis/uit, laatste N wedstrijden) |
| ↕ Sorteren | Klik op kolomkop om te sorteren |
| 📄 Paginering | 25/50/100 rijen per pagina |
| 📈 Grafieken | Wins per team, winpercentage donut |
| 🔄 Auto-update | 4× per dag automatisch ververst |

---

## 🎨 Aanpassen

Het dashboard heeft een donker thema passend bij de KNBSB stijl.
CSS variabelen bovenaan het widget staan voor eenvoudige aanpassing:

```css
--hk-accent: #f78166;   /* Accentkleur (rood) */
--hk-accent2: #58a6ff;  /* Secundaire accentkleur (blauw) */
--hk-bg: #0d1117;       /* Achtergrond */
```

---

## ⚠️ Opmerkingen

- De stats-pagina van KNBSB laadt data via JavaScript — daarom gebruikt de scraper **Playwright** (echte browser)
- Als de sitestructuur verandert, pas dan `scraper.py` aan
- Data wordt opgeslagen als JSON in de `data/` map van je repo
- De Elementor widget haalt data op via **GitHub raw** (gratis, geen server nodig)
