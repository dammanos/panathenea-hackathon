# TopoTools

AI-powered property due diligence platform for Greek topographic engineers. Enter a KAEK (cadastral code) and get an instant professional report with building parameters, restrictions, FEK decrees, building permits, and survey diagrams — all sourced from live government data.

## How It Works

```
KAEK Input ─> Ktimatologio API ─> Parcel Centroid (lat/lon)
                                        │
                    ┌───────────────────┼───────────────────┐
                    ▼                   ▼                   ▼
            TEE UDM (34 layers)   Nominatim          Ktimatologio
            Building params       Reverse geocode    Parcel attributes
            Permits 2011-2018     Address/postcode   Area, KAEK, use
            FEK documents
            Survey diagrams
            Archaeological zones
            Natura 2000
            Forest map
            Shoreline
            ...
                    │                   │                   │
                    └───────────────────┼───────────────────┘
                                        ▼
                              Claude AI (Sonnet)
                              Generates professional
                              Greek property report
                                        │
                                        ▼
                              Markdown report with
                              FEK PDF links, permit
                              details, risk assessment
```

1. **KAEK Lookup** — The 12-digit cadastral code is sent to the National Cadastre (Ktimatologio) ArcGIS API. We get the parcel polygon, compute its centroid, and extract cadastral attributes (area, use, etc.).

2. **Parallel Data Fetch** — Using the centroid coordinates, we query **34 TEE (Technical Chamber of Greece) GIS layers** in a single parallel batch, plus Nominatim for address enrichment. This takes ~2-5 seconds. The layers include:
   - Building parameters (Σ.Δ., height, coverage, lot size, land use, building system)
   - Building permits 2011-2018 with heights, areas, and floors
   - FEK (Government Gazette) documents with direct PDF links
   - YPD building blocks with decree references and georeferenced diagrams
   - Environmental restrictions (Natura 2000, forest map, shoreline, streams)
   - Archaeological zones (5 subcategories)
   - Regulatory framework (ZOE, expropriation, PD protection)

3. **AI Report Generation** — All raw government data is formatted and sent to Claude Sonnet with a domain-specific system prompt. The AI generates a structured Greek report with sections for identification, building parameters, restrictions, permits, FEK references, risk assessment, and recommendations.

4. **Frontend Display** — The report is rendered as formatted markdown with clickable FEK PDF links, a metadata grid (KAEK, coordinates, area, address, postal code), restriction badges, and an interactive Leaflet map.

## Features

- **Property Report** — Full AI-generated due diligence report from a single KAEK code
- **Buildability (computed)** — Deterministic, no-AI computation of max floor area (Σ.Δ. × area), footprint (coverage × area), indicative floors, and the άρτιο/buildable-lot check; fed to the report as authoritative ground-truth
- **Objective Value** — Deterministic αντικειμενική αξία calculator for within-plan dwellings (ΠΟΛ.1149/1994), with every coefficient shown for auditability
- **Coordinate Converter** — Convert between EGSA87, WGS84, GGRS87, HTRS07, and TM07. Supports manual entry, file upload (TXT/CSV/TSV), and batch export
- **Bilingual UI** — Greek and English interface with dark/light theme

## Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend | Python, FastAPI, httpx (async) |
| AI | Anthropic Claude Sonnet |
| GIS Data | TEE UDM ArcGIS REST, Ktimatologio ArcGIS, Nominatim |
| Coordinates | Pure-math converter (no pyproj) — EGSA87/WGS84/GGRS87/TM07 |
| Frontend | Vanilla JS, Leaflet maps, single `index.html` |

## Running it locally

**Prerequisites:** Python 3.10+ and `git`. Report generation also needs an
Anthropic API key (`sk-ant-...`).

```bash
# 1. Clone and check out this branch
git clone https://github.com/dammanos/panathenea-hackathon.git
cd panathenea-hackathon
git checkout claude/project-review-vjSN2

# 2. Create a virtualenv and install deps
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Provide your Anthropic API key (needed for the AI report).
#    Either export it, or create a .env file (auto-loaded on startup):
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 4. Run the server
uvicorn backend.main:app --host 0.0.0.0 --port 8000

# 5. Open the app
#    http://localhost:8000
```

### What works without setup
- **Convert** tab — fully client-side, no key or network needed.
- **Value** tab — calls a local deterministic endpoint, no key needed.
- The **Report** tab needs: (a) the `ANTHROPIC_API_KEY` above, and (b) outbound
  internet access to the Greek government GIS (TEE / Κτηματολόγιο) and Nominatim.
  Try a known KAEK such as `050461527012`.

### Tests
```bash
python -m pytest tests/ -q          # 71 tests, no network/API key required
```

## API

```
POST /api/v1/report/generate
Body: { "kaek": "050830320012" }

Returns: {
  "kaek": "050830320012",
  "lat": 38.065745,
  "lon": 23.779146,
  "x": 480477.23,          // EGSA87
  "y": 4212844.77,
  "area_m2": 1208.38,
  "municipality": "ΔΗΜΟΣ ΛΥΚΟΒΡΥΣΗΣ - ΠΕΥΚΗΣ",
  "address": "Στρ.Μακρυγιάννη, Λυκόβρυση...",
  "postal_code": "141 23",
  "has_restrictions": true,
  "layers_queried": 34,
  "report_md": "# ΑΝΑΦΟΡΑ ΠΟΛΕΟΔΟΜΙΚΗΣ...",
  "buildability": {           // deterministically computed (no AI)
    "max_floor_area_m2": 966.7,
    "max_footprint_m2": 725.0,
    "indicative_max_floors": 3,
    "is_buildable_lot": true,
    "warnings": [], "assumptions": [ ... ]
  }
}

POST /api/v1/value/objective
Body: {                       // zone_price (Τ.Ζ.) from valuemaps.gsis.gr
  "zone_price": 1500, "area_m2": 100,
  "year_built": 2016, "has_frontage": true,
  "floor_coefficient": 1.0, "surface_coefficient": 1.0
}

Returns: {                    // every coefficient returned for auditability
  "objective_value": 120000.0,
  "coefficients": { "age": 0.8, "frontage": 1.0, ... },
  "warnings": [], "assumptions": [ ... ]
}
```

## Authors

- **Manos Damaskinakis**
- **Lefteris Tzokas**
- **Dimitris Kolias**

Built at the Panathenea Hackathon.
