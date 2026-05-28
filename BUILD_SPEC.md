# TopoTools - Complete Build Spec for AI construction

## Goal
Build the TopoTools surveying platform. This spec sheet contains everything needed. Follow the steps in order.

---

## Step 1: Project Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install fastapi uvicorn httpx pydantic pydantic-settings
pip freeze > requirements.txt
git init
mkdir -p backend/routers backend/services backend/data
```

---

## Step 2: Backend Files (create in this order)

### 2a. `backend/__init__.py` - empty file

### 2b. `backend/main.py`
FastAPI app serving:
- CORS middleware (allow all origins)
- `GET /` serves `index.html` from project root via `FileResponse`
- `GET /api/health` returns `{"status": "ok"}`
- Include zoning router
- Mount `/static` pointing to project root

### 2c. `backend/models/zoning.py`
Pydantic models:
- `ZoningRequest`: coord_system (str, default "egsa87"), lat/lon/x/y (optional floats), intended_use (str, default "residential"), area_m2 (optional float)
- `KaekLookupRequest`: kaek (str)
- `KaekLookupResponse`: found (bool), kaek (str), lat/lon/x/y (optional floats), area_m2 (optional float), description (str=""), main_use (str="")
- `RiskFlag`: category (str), level (str: high/medium/low), title (str), description (str)
- `BuildingParams`: coverage_ratio, building_factor, max_height_m, min_lot_size_m2, min_frontage_m, setback_front_m, setback_side_m (optional floats), max_floors (optional int), building_system/fek/fek_url (optional str)
- `ZoningReport`: verdict (str: green/yellow/red), verdict_summary (str), zone_name/zone_type/land_use/municipality (str=""), risk_flags (list[RiskFlag]=[]), building_params (optional BuildingParams), regulations_summary (str=""), data_source (str=""), disclaimer (str="Preliminary assessment. Always consult a licensed surveyor.")

### 2d. `backend/services/coordinate_converter.py`
Python port of EGSA87/WGS84/GGRS87/TM07 coordinate conversions. Key functions:
- `egsa87_to_wgs84(x, y) -> (lat, lon)`: TM reverse -> GGRS87 geographic -> Helmert to WGS84
- `wgs84_to_egsa87(lat, lon) -> (x, y)`: inverse Helmert -> TM forward
- `wgs84_to_tm07(lat, lon)` and `tm07_to_wgs84(x, y)`: same TM projection but on WGS84 datum

**Math constants:**
- GRS80: a=6378137.0, f=1/298.257222101
- WGS84: a=6378137.0, f=1/298.257223563
- Greek Grid TM: lon0=24deg, k0=0.9996, false_easting=500000, false_northing=0
- Helmert GGRS87->WGS84: dX=-199.87, dY=+74.79, dZ=+246.62

**Pipeline:** TM inverse (Redfearn) -> ECEF (3-param Helmert) -> geographic on target ellipsoid. The full Redfearn series with e1-e4 terms, footpoint latitude, and 6th-order expansion. Copy the exact math from the spec - this is surveying-grade code.

### 2e. `backend/services/tee_service.py`
ArcGIS REST API client for TEE's Unified Digital Map. Uses httpx async.

**Base URLs:**
- UDM: `https://sdigmap.tee.gov.gr/mapping/rest/services/UDM`
- KAEK: `https://services-eu1.arcgis.com/40tFGWzosjaLJpmn/ArcGIS/rest/services/GEOTEMAXIA_LEITOURGOUN_ON_gdb/FeatureServer/0`

**Layer IDs** (under UDM_SERVICE_POLEODOMIKI_PLIROFORIA/MapServer):
- sd (building factor): /20
- height: /16
- coverage: /18
- artiotita: /17
- land_use: /21
- zone_sector: /14
- building_system: /19
- shoreline: /1

**Other layers:**
- Natura 2000: UDM_SERVICE_NATURA_DASIKA/MapServer/0
- Forest maps: UDM_SERVICE_NATURA_DASIKA/MapServer/15
- Archaeological (5 sublayers): UDM_SERVICE_ARCHAIOLOGIKO/MapServer/ [3, 7, 11, 15, 18]
- ZOE: UDM_SERVICE_RYTHMISEIS_EXOASTIKOU_CHOROU/MapServer/1

**Query pattern** (point intersect):
```
GET {layer_url}/query?geometry={lon},{lat}&geometryType=esriGeometryPoint&inSR=4326&spatialRel=esriSpatialRelIntersects&outFields=*&returnGeometry=false&f=json
```
Buffer queries add: `distance={m}&units=esriSRUnit_Meter`

**Functions:**
- `get_building_params(lat, lon)`: queries 7 layers in parallel with asyncio.gather
- `get_natura_zones(lat, lon, buffer_m=1000)`
- `get_archaeological_zones(lat, lon, buffer_m=500)`: 5 layers in parallel, tags each with `_category`
- `get_forest_map(lat, lon)`, `get_shoreline(lat, lon, buffer_m=200)`, `get_zoe_zones(lat, lon)`
- `get_kaek_parcel(kaek)`: queries KAEK_BASE with `where=KAEK='{kaek}'`, returnGeometry=true, outSR=4326. Computes centroid from polygon rings.

All use 15s timeout.

### 2f. `backend/routers/zoning_checker.py`
Two endpoints:
- `POST /api/v1/zoning/kaek`: looks up parcel, converts centroid to EGSA87, returns KaekLookupResponse
- `POST /api/v1/zoning/check`: main zoning check. Converts coords if needed, queries TEE for building params + natura + archaeological + forest + shoreline + ZOE. Falls back to static JSON. Builds verdict (green/yellow/red based on risk flags), returns ZoningReport with regulations_summary.

### 2g. Static data files
Create these JSON files in `backend/data/`:

**`zoning_rules.json`**: 8 zones (General Residential, Dense Urban, Commercial, Mixed Use, Outside Plan Agricultural, Outside Plan Residential, Industrial, Tourism) with coverage_ratio, building_factor, max_height_m, min_lot_size_m2, setback values, max_floors.

**`natura2000_areas.json`**: ~8 Greek Natura 2000 sites (Ymittos, Parnitha, Penteli, Messolonghi, Axios Delta, Samaria, Olympus, Sounion) with code, name, center_lat/lon, protection_level, type, area_ha.

**`archaeological_zones.json`**: ~10 Greek archaeological sites (Acropolis, Ancient Agora, Kerameikos, Roman Agora, Sounion, Eleusis, Brauron, Amphiareion, Plato's Academy, Thorikos) with name, center_lat/lon, protection_level, type.

---

## Step 3: Frontend - Single `index.html`

One self-contained file with embedded CSS + JS. No build tools. CDN deps: IBM Plex Mono + Sans (Google Fonts), Leaflet 1.9.4.

### Design System
- Dark theme default with light toggle via `data-theme` on `<html>`
- CSS variables for both themes (dark: --bg:#0f1117, --surface:#181c27, --accent:#2563eb, --accent2:#0891b2, etc.)
- Grid background overlay via `body::before` with subtle colored gridlines
- IBM Plex Sans body, IBM Plex Mono for labels/data
- Cards with 12px radius, surface background, border, box-shadow
- Gradient buttons (accent->accent2 at 135deg)
- Green for positive values, yellow for warnings, red for errors

### Layout
- `.container` max-width 820px, centered
- Header: logo "TT" gradient box + title + version badge + EL/EN lang toggle + theme toggle
- Tab bar: 3 tabs (Convert, Area, Zoning) as pill-style buttons
- Responsive: 2 breakpoints at 680px and 460px

### i18n System
- `translations` object with `el` and `en` keys containing all UI strings (~100 keys each)
- `data-i18n` attributes on elements for text, `data-i18n-html` for innerHTML, `data-i18n-placeholder` for placeholders
- `setLanguage(lang)` updates all elements, persists to localStorage
- Greek is default language

### Tab 1: Convert (Coordinate Converter)
**ALL CLIENT-SIDE, no backend calls.**

Features:
- Input system selector: EGSA87, WGS84 DD, WGS84 DMS, GGRS87 Geographic, HTRS07 Geographic, TM07
- Output system selector: All systems or specific one
- Toggle: Manual entry / File upload
- Manual: multi-point list (add/delete rows), CONVERT button
- File upload: drag-and-drop zone, accepts .txt/.csv/.tsv
- File parsing: auto-detect delimiter (tab, semicolon, comma, space), detect header row, handle DMS format
- Results: scrollable table with color-coded columns (input=blue tint, output=green), capped at 500 rows
- Export: Download CSV, Export XLSX (TSV with BOM + .xls extension), Copy table
- Single-point: reverse geocode via Nominatim, show address
- Point counter badge

**JS coordinate math** - full port of the Python converter (identical constants, identical algorithms):
- `tmToGeoGreekGrid(easting, northing)` - Redfearn reverse
- `geoToTmGreekGrid(latDeg, lonDeg)` - Redfearn forward
- `geoToECEF(lat, lon, h, a, e2)` / `ecefToGeo(X, Y, Z, a, e2)`
- `ggrs87ToWgs84(lat, lon)` / `wgs84ToGgrs87(lat, lon)` - 3-param Helmert
- `parseDMS(str)` - regex: `/(-?\d+)\s*[°]\s*(\d+)\s*['']\s*([\d.]+)\s*[""]?\s*([NSEWnsew])?/`
- `toDMS(dd, dir)` - decimal to DMS string
- Validation: `isValidWgs84(lat, lon)` (34-42, 19-30), `isLikelyGreekGrid(x, y)` (100k-900k, 3.8M-4.7M)

**Hub pattern**: all conversions go through GGRS87 geographic as internal hub. Input->GGRS87->all outputs.

### Tab 2: Area (Polygon Area Calculator)
**ALL CLIENT-SIDE.**

Features:
- Coordinate system selector (same 6 systems)
- Toggle: Manual entry / File upload
- Manual: multi-point polygon vertices, CALCULATE AREA button
- Points converted to EGSA87 via `pointToEgsa87()`, then `shoelaceArea()` (Shoelace/Gauss formula)
- Results: big number in m2 (green, 28px), plus hectares + stremma (Greek unit, 1 stremma = 1000 m2)
- Interactive Leaflet map showing polygon with numbered markers
- EGSA87 points table (scrollable, sticky header)
- Reverse geocode polygon centroid
- Export: Copy result (formatted text), Download CSV report

### Tab 3: Zoning (Backend-dependent)

Features:
- KAEK input with FIND button (POST to /api/v1/zoning/kaek). Strip "KAEK " or "KAEK " prefix before sending. Button must have `width:auto` to override global `.btn { width:100% }`.
- Coordinate system toggle: EGSA87 or WGS84 (shows/hides input groups)
- Intended use selector: residential, commercial, industrial, agricultural, tourism
- Optional plot area input
- CHECK ZONING button (POST to /api/v1/zoning/check)
- Spinner during request
- Results: verdict card (green/yellow/red with emoji + summary), meta grid (municipality, land use, zone), risk flags (categorized cards with level badges), building params grid (coverage %, factor, height, floors, min lot, frontage, building system, FEK link), data source line, disclaimer
- Leaflet map with color-coded marker matching verdict + 100m circle
- Reverse geocode

### Shared Utilities
- `showToast(message)` - fixed bottom-right, fades in/out
- `reverseGeocode(lat, lon, targetId)` - Nominatim, respects current language
- `escapeHtml(str)` - via textContent/innerHTML trick
- `copyValue()`, `fallbackCopy()` - clipboard API with execCommand fallback
- `parseBulkCoordinates(text, inputSystem)` - shared between Convert file upload and Area file upload

---

## Step 4: Run & Verify

```bash
source venv/bin/activate
uvicorn backend.main:app --reload
# Open http://127.0.0.1:8000
```

**Test checklist:**
1. Convert tab: enter EGSA87 coords (e.g. 481000, 4205000), convert, verify all 6 output systems
2. Convert tab: upload a CSV file, verify table + export
3. Area tab: enter 4+ polygon points, verify area + map + numbered markers
4. Area tab: upload points file, verify same
5. Zoning tab: enter KAEK "050461527012", click FIND, verify coords auto-fill
6. Zoning tab: paste "KAEK 050092643002" with prefix, verify prefix stripped
7. Zoning tab: click CHECK ZONING, verify verdict + params + risk flags + map
8. Toggle EL/EN, verify all UI text changes
9. Toggle dark/light theme
10. Test on mobile viewport width

---

## Known Issues to Fix During Build
- Use `--muted` CSS var (not `--text-secondary` which is undefined) for secondary text
- Use `--accent` CSS var (not `--primary` which is undefined) for FEK links
- Scope `switchInputMode()` selector to `#tab-convert .input-mode-btn` to avoid leaking to Area tab
- "Show all rows" button re-renders with same 500 cap - either remove or fix to actually show all
