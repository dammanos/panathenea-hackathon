# TopoTools - Product Requirements Document

## 1. Overview

TopoTools is a web-based surveying platform for Greek land surveyors and property professionals. It provides coordinate conversion and zoning compliance checks against Greece's official spatial data sources (TEE Unified Digital Map).

## 2. Problem Statement

Greek surveyors routinely need to:
- Convert coordinates between national (EGSA87, GGRS87, TM07) and international (WGS84) systems
- Check zoning regulations, building parameters, and environmental restrictions for parcels

These tasks currently require multiple disconnected tools, desktop GIS software, or manual lookups on government portals. TopoTools unifies them into a single, fast, mobile-friendly web app.

## 3. Target Users

- Licensed surveyors (topographers)
- Civil engineers and architects
- Real estate professionals
- Municipal planning officers
- Property owners researching parcels

## 4. Functional Requirements

### FR-1: Coordinate Conversion (Client-side)

| ID | Requirement |
|----|-------------|
| FR-1.1 | Support 6 coordinate systems: EGSA87, WGS84 DD, WGS84 DMS, GGRS87 Geographic, HTRS07 Geographic, TM07 |
| FR-1.2 | Convert single or multiple points (manual entry with add/delete rows) |
| FR-1.3 | Accept file upload (.txt, .csv, .tsv) with auto-detection of delimiter and header row |
| FR-1.4 | Display results in a color-coded scrollable table (max 500 rows initial render) |
| FR-1.5 | Export results as CSV, XLSX (TSV-based), or copy to clipboard |
| FR-1.6 | Reverse geocode single-point results via Nominatim |
| FR-1.7 | All math runs client-side (no backend dependency) |
| FR-1.8 | Hub conversion pattern: all inputs convert to GGRS87 geographic, then fan out to all outputs |

### FR-2: Zoning Check (Backend-dependent)

| ID | Requirement |
|----|-------------|
| FR-2.1 | Look up parcels by KAEK code (POST /api/v1/zoning/kaek) |
| FR-2.2 | Strip "KAEK" prefix variants from user input before lookup |
| FR-2.3 | Full zoning check by coordinates (POST /api/v1/zoning/check) |
| FR-2.4 | Query TEE ArcGIS layers: building params (7 layers), Natura 2000, archaeological (5 sublayers), forest maps, shoreline, ZOE |
| FR-2.5 | Fall back to static JSON zoning rules when TEE is unreachable |
| FR-2.6 | Return verdict (green/yellow/red) based on risk flag severity |
| FR-2.7 | Display: verdict card, meta grid, risk flags, building params grid, data source, disclaimer |
| FR-2.8 | Show Leaflet map with color-coded marker and 100m circle |
| FR-2.9 | Support intended use: residential, commercial, industrial, agricultural, tourism |

### FR-3: Internationalization

| ID | Requirement |
|----|-------------|
| FR-3.1 | Greek (default) and English languages |
| FR-3.2 | ~100 UI string keys per language |
| FR-3.3 | Language persisted to localStorage |
| FR-3.4 | data-i18n attribute system for text, HTML, and placeholder content |

### FR-4: Theme

| ID | Requirement |
|----|-------------|
| FR-4.1 | Dark theme (default) and light theme |
| FR-4.2 | Toggle via data-theme attribute on html element |
| FR-4.3 | CSS custom properties for all theme colors |

## 5. Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Single index.html frontend - no build tools, no framework |
| NFR-2 | CDN dependencies only: Google Fonts (IBM Plex), Leaflet 1.9.4 |
| NFR-3 | Responsive: 3 breakpoints (desktop, 680px, 460px) |
| NFR-4 | Backend: FastAPI + uvicorn, async HTTP via httpx |
| NFR-5 | All TEE API calls use 15s timeout |
| NFR-6 | Coordinate math must be surveying-grade (full Redfearn series, 6th-order expansion) |
| NFR-7 | CORS: allow all origins |
| NFR-8 | Disclaimer on all zoning results: "Preliminary assessment. Always consult a licensed surveyor." |

## 6. Architecture

```
project-root/
  index.html              # Single-file frontend (CSS + JS embedded)
  backend/
    __init__.py
    main.py               # FastAPI app, CORS, static mount, routers
    models/
      zoning.py           # Pydantic request/response models
    routers/
      zoning_checker.py   # /api/v1/zoning/* endpoints
    services/
      coordinate_converter.py  # EGSA87/WGS84/GGRS87/TM07 math
      tee_service.py           # ArcGIS REST client for TEE UDM
    data/
      zoning_rules.json
      natura2000_areas.json
      archaeological_zones.json
```

## 7. External Dependencies

| Dependency | Purpose |
|------------|---------|
| TEE UDM ArcGIS REST API | Building params, Natura, archaeology, forest, shoreline, ZOE |
| ArcGIS Feature Server (KAEK) | Parcel geometry lookup by KAEK code |
| Nominatim (OpenStreetMap) | Reverse geocoding for display addresses |
| Google Fonts CDN | IBM Plex Sans + Mono |
| Leaflet CDN | Interactive maps |

## 8. Data Sources

- **TEE Unified Digital Map** - Official Greek spatial planning data
- **Static JSON fallback** - 8 zoning rule templates, 8 Natura 2000 sites, 10 archaeological zones
- **Coordinate constants** - GRS80, WGS84 ellipsoid parameters; Greek Grid TM projection; Helmert GGRS87->WGS84 transform

## 9. Acceptance Criteria

1. Convert: EGSA87 (481000, 4205000) produces valid WGS84, GGRS87, TM07, DMS outputs
2. Convert: CSV file upload parses correctly and exports match
3. Zoning: KAEK "050461527012" returns parcel coordinates
4. Zoning: KAEK input "KAEK 050092643002" has prefix stripped
5. Zoning: Check returns verdict with params, risk flags, and map
6. i18n: All UI text toggles between Greek and English
7. Theme: Dark/light toggle works across all tabs
8. Mobile: Usable at 360px viewport width
