# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

TopoTools — AI-powered property due diligence platform for Greek topographic engineers. Single-page app with a FastAPI backend that queries Greek government GIS services (TEE, Ktimatologio) and generates professional property reports using Claude AI.

## Commands

```bash
# Setup
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Run server (requires ANTHROPIC_API_KEY for report generation)
ANTHROPIC_API_KEY=sk-... uvicorn backend.main:app --host 0.0.0.0 --port 8000

# Run all tests
python -m pytest tests/ -x -q

# Run a single test
python -m pytest tests/test_coordinate_converter.py -x -q
```

## Architecture

**Backend** (`backend/`): FastAPI app, entry point `main.py`.

- `routers/report.py` — Single API endpoint `POST /api/v1/report/generate`. Takes a KAEK (Greek cadastral ID), looks up the parcel in the national cadastre, queries 34 TEE GIS layers + Nominatim in parallel, then sends all data to Claude for AI report generation.
- `services/tee_service.py` — ArcGIS REST API client for TEE's Unified Digital Map. `get_all_layers(lat, lon)` queries all layers in one parallel batch. `get_kaek_parcel(kaek)` looks up parcels by cadastral code. Layers include building parameters, permits, environmental restrictions, archaeological zones, FEK documents, and survey diagrams.
- `services/ai_report.py` — Formats raw GIS data into structured text, sends to Claude Sonnet with a Greek surveyor system prompt. `_format_layer_data()` is the data preparation function; `generate_property_report()` calls the Anthropic API.
- `services/coordinate_converter.py` — Pure-math coordinate transforms between EGSA87, WGS84, GGRS87, HTRS07, and TM07. No external geo libraries. The Helmert 7-parameter transform is hardcoded for the Greek datum.

**Frontend** (`index.html`): Single-file vanilla JS app with two tabs:
- **Report** — KAEK input → AI property report with map, metadata grid, restriction badges
- **Convert** — Multi-point coordinate converter with file upload (TXT/CSV/TSV), manual entry, and export (CSV/XLSX)

Uses Leaflet for maps, IBM Plex fonts, dark/light theme toggle, Greek/English i18n.

## Key Patterns

- All TEE/GIS queries use `httpx.AsyncClient` with 15s timeout and return empty lists on failure (never raise).
- The report endpoint runs TEE queries and Nominatim reverse geocode in parallel via `asyncio.gather`.
- Coordinate converter is pure Python math (no pyproj) — precision-critical for surveying use.
- Frontend i18n: `translations` object with `el`/`en` keys, `t('key')` helper function, `data-i18n` attributes on elements.

## Environment Variables

- `ANTHROPIC_API_KEY` — Required for report generation (Claude Sonnet)
