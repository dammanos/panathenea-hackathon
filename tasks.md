# TopoTools - Task Breakdown (TDD)

Each task follows: **Write tests -> Implement -> Verify tests pass -> Refactor if needed.**

---

## Phase 0: Project Scaffolding

### Task 0.1: Initialize project structure
- [ ] Create virtual environment and install dependencies (fastapi, uvicorn, httpx, pydantic, pydantic-settings, pytest, pytest-asyncio, httpx for test client)
- [ ] Create directory structure: `backend/`, `backend/models/`, `backend/routers/`, `backend/services/`, `backend/data/`, `tests/`
- [ ] Create `backend/__init__.py`, `backend/models/__init__.py`, `backend/routers/__init__.py`, `backend/services/__init__.py`
- [ ] Create `requirements.txt`
- [ ] Create `pytest.ini` or `pyproject.toml` with test config
- [ ] Verify: `pytest` runs with 0 tests collected, no errors

---

## Phase 1: Coordinate Converter (Backend)

### Task 1.1: Coordinate converter - EGSA87 to WGS84
- [ ] **Test**: `tests/test_coordinate_converter.py`
  - Test `egsa87_to_wgs84(481000, 4205000)` returns known lat/lon (approx 37.97, 23.73 for Athens area)
  - Test round-trip: `wgs84_to_egsa87(*egsa87_to_wgs84(x, y))` returns original x, y within 0.001m
  - Test edge cases: extreme north/south/east/west of Greece
- [ ] **Implement**: `backend/services/coordinate_converter.py`
  - GRS80 and WGS84 ellipsoid constants
  - Greek Grid TM parameters (lon0=24deg, k0=0.9996, FE=500000)
  - Helmert GGRS87->WGS84 parameters (dX=-199.87, dY=74.79, dZ=246.62)
  - `tmToGeo()` - Redfearn reverse with full 6th-order series
  - `geoToTm()` - Redfearn forward
  - `geoToECEF()` / `ecefToGeo()` - ellipsoid <-> cartesian
  - 3-parameter Helmert transform
  - `egsa87_to_wgs84(x, y)` and `wgs84_to_egsa87(lat, lon)`
- [ ] **Verify**: All tests pass

### Task 1.2: Coordinate converter - TM07 conversions
- [ ] **Test**: Add to `tests/test_coordinate_converter.py`
  - Test `wgs84_to_tm07(lat, lon)` and `tm07_to_wgs84(x, y)` with known points
  - Test round-trip accuracy
- [ ] **Implement**: TM07 functions (same TM projection on WGS84 datum)
- [ ] **Verify**: All tests pass

---

## Phase 2: Pydantic Models

### Task 2.1: Zoning models
- [ ] **Test**: `tests/test_models.py`
  - Test ZoningRequest with defaults (coord_system="egsa87", intended_use="residential")
  - Test ZoningRequest with all optional fields
  - Test KaekLookupRequest/Response serialization
  - Test RiskFlag validation (level must be high/medium/low)
  - Test BuildingParams with partial fields
  - Test ZoningReport verdict values (green/yellow/red)
  - Test ZoningReport default disclaimer text
- [ ] **Implement**: `backend/models/zoning.py` - all Pydantic models per spec
- [ ] **Verify**: All tests pass

---

## Phase 3: Static Data

### Task 3.1: Zoning rules JSON
- [ ] **Test**: `tests/test_static_data.py`
  - Test file loads as valid JSON
  - Test 8 zones present
  - Test each zone has required keys: coverage_ratio, building_factor, max_height_m, min_lot_size_m2, setback values, max_floors
  - Test value ranges are reasonable (e.g. coverage 0-1, height > 0)
- [ ] **Implement**: `backend/data/zoning_rules.json`
- [ ] **Verify**: All tests pass

### Task 3.2: Natura 2000 and archaeological zones JSON
- [ ] **Test**: Add to `tests/test_static_data.py`
  - Test natura2000_areas.json: valid JSON, ~8 entries, each has code/name/center_lat/center_lon/protection_level/type/area_ha
  - Test archaeological_zones.json: valid JSON, ~10 entries, each has name/center_lat/center_lon/protection_level/type
  - Test coordinates are within Greece bounds (34-42 lat, 19-30 lon)
- [ ] **Implement**: `backend/data/natura2000_areas.json`, `backend/data/archaeological_zones.json`
- [ ] **Verify**: All tests pass

---

## Phase 4: TEE Service

### Task 4.1: TEE service - building params query
- [ ] **Test**: `tests/test_tee_service.py`
  - Mock httpx responses for all 7 building param layers
  - Test `get_building_params(lat, lon)` parses ArcGIS JSON response correctly
  - Test timeout handling (15s)
  - Test empty/error responses return graceful defaults
- [ ] **Implement**: `backend/services/tee_service.py`
  - Base URLs and layer ID constants
  - Point intersect query builder
  - `get_building_params(lat, lon)` with asyncio.gather for 7 layers
- [ ] **Verify**: All tests pass

### Task 4.2: TEE service - environmental & restriction layers
- [ ] **Test**: Add to `tests/test_tee_service.py`
  - Mock responses for Natura, archaeological (5 sublayers), forest, shoreline, ZOE
  - Test buffer query parameter generation
  - Test `_category` tagging on archaeological results
  - Test `get_kaek_parcel(kaek)` centroid computation from polygon rings
- [ ] **Implement**: Remaining TEE service functions
  - `get_natura_zones(lat, lon, buffer_m=1000)`
  - `get_archaeological_zones(lat, lon, buffer_m=500)`
  - `get_forest_map(lat, lon)`
  - `get_shoreline(lat, lon, buffer_m=200)`
  - `get_zoe_zones(lat, lon)`
  - `get_kaek_parcel(kaek)`
- [ ] **Verify**: All tests pass

---

## Phase 5: FastAPI App & Routers

### Task 5.1: FastAPI app skeleton
- [ ] **Test**: `tests/test_main.py`
  - Test `GET /api/health` returns `{"status": "ok"}`
  - Test CORS headers present in response
  - Test `GET /` returns 200 (once index.html exists)
- [ ] **Implement**: `backend/main.py`
  - FastAPI app with CORS middleware (allow all)
  - Health endpoint
  - Static mount at `/static`
  - Root serves `index.html`
  - Include zoning router
- [ ] **Verify**: All tests pass

### Task 5.2: Zoning router - KAEK lookup
- [ ] **Test**: `tests/test_zoning_router.py`
  - Mock TEE service `get_kaek_parcel`
  - Test `POST /api/v1/zoning/kaek` with valid KAEK returns KaekLookupResponse
  - Test KAEK not found returns found=false
  - Test centroid is converted to EGSA87
- [ ] **Implement**: `backend/routers/zoning_checker.py` - KAEK endpoint
- [ ] **Verify**: All tests pass

### Task 5.3: Zoning router - full zoning check
- [ ] **Test**: Add to `tests/test_zoning_router.py`
  - Mock all TEE service functions
  - Test `POST /api/v1/zoning/check` with EGSA87 coords
  - Test `POST /api/v1/zoning/check` with WGS84 coords (conversion occurs)
  - Test verdict logic: no risk flags -> green, medium flags -> yellow, high flags -> red
  - Test fallback to static JSON when TEE fails
  - Test regulations_summary is populated
  - Test response matches ZoningReport schema
- [ ] **Implement**: Full zoning check endpoint
  - Coordinate conversion based on input coord_system
  - Parallel TEE queries
  - Risk flag generation from layer results
  - Verdict computation
  - Static JSON fallback
  - Build and return ZoningReport
- [ ] **Verify**: All tests pass

---

## Phase 6: Frontend - Structure & Theme

### Task 6.1: HTML skeleton with theme system
- [ ] **Test**: Manual browser test (no automated frontend tests for single-file app)
  - Dark theme renders with correct background (#0f1117)
  - Light theme toggles via button
  - Grid overlay visible
  - IBM Plex fonts load
  - Layout centered at max-width 820px
  - Responsive at 680px and 460px breakpoints
- [ ] **Implement**: `index.html`
  - HTML boilerplate with CDN links (Google Fonts, Leaflet)
  - CSS custom properties for dark and light themes
  - Grid background overlay (body::before)
  - Container, header (logo, title, version badge, lang toggle, theme toggle)
  - Tab bar (Convert, Zoning) as pill buttons
  - Card base styles, button styles, responsive breakpoints
- [ ] **Verify**: Visual check in browser

### Task 6.2: i18n system
- [ ] **Test**: Browser console verification
  - `setLanguage('en')` updates all `data-i18n` elements
  - `setLanguage('el')` reverts to Greek
  - Language persists in localStorage
- [ ] **Implement**: In index.html JS section
  - `translations` object with el and en keys (~100 strings each)
  - `setLanguage(lang)` function
  - data-i18n / data-i18n-html / data-i18n-placeholder attribute processing
  - Language toggle button wired up
- [ ] **Verify**: Toggle works, all text changes

---

## Phase 7: Frontend - Convert Tab

### Task 7.1: Client-side coordinate math (JS)
- [ ] **Test**: Browser console tests (define a `runConverterTests()` function)
  - `egsa87ToAll(481000, 4205000)` returns valid WGS84
  - Round-trip EGSA87 -> WGS84 -> EGSA87 within 0.001m
  - `parseDMS("37 58' 12.5\" N")` returns correct decimal
  - `toDMS(37.97, 'lat')` returns valid DMS string
  - `isValidWgs84(37.97, 23.73)` returns true
  - `isValidWgs84(50, 23)` returns false (outside Greece)
  - `isLikelyGreekGrid(481000, 4205000)` returns true
- [ ] **Implement**: JS coordinate functions in index.html
  - Full port of Python converter (identical constants and algorithms)
  - Hub pattern: input -> GGRS87 geographic -> all outputs
  - parseDMS, toDMS, validation functions
- [ ] **Verify**: Console tests pass, results match Python backend

### Task 7.2: Convert tab UI and interaction
- [ ] **Test**: Manual browser test
  - Input system selector shows correct fields
  - Add/delete point rows works
  - CONVERT button produces result table
  - Color-coded columns (blue input, green output)
  - Point counter badge updates
  - Single point triggers reverse geocode
- [ ] **Implement**: Convert tab HTML + JS
  - Input/output system selectors
  - Manual entry mode with multi-point list
  - Convert button handler
  - Results table renderer (max 500 rows)
- [ ] **Verify**: Enter EGSA87 (481000, 4205000), verify 6 output systems

### Task 7.3: Convert tab file upload and export
- [ ] **Test**: Manual browser test
  - Toggle to file upload mode shows drag-and-drop zone
  - Upload .csv file, verify parsing (auto-detect delimiter, header)
  - Upload .txt with DMS format, verify parsing
  - Download CSV export matches displayed table
  - Export XLSX produces valid file
  - Copy table works
- [ ] **Implement**:
  - File upload toggle and drop zone
  - `parseBulkCoordinates()` - delimiter detection, header detection, DMS handling
  - Export functions: CSV download, XLSX (TSV+BOM), clipboard copy
- [ ] **Verify**: Upload test file, export, re-import

---

## Phase 8: Frontend - Zoning Tab

### Task 8.1: Zoning tab KAEK lookup
- [ ] **Test**: Manual + backend running
  - Enter KAEK "050461527012", click FIND, coords auto-fill
  - Enter "KAEK 050092643002" with prefix, verify prefix stripped
  - FIND button has `width:auto` (doesn't stretch full width)
  - Not-found KAEK shows appropriate message
- [ ] **Implement**: Zoning tab HTML + JS
  - KAEK input + FIND button
  - Prefix stripping logic
  - POST to /api/v1/zoning/kaek
  - Auto-fill coordinate fields from response
- [ ] **Verify**: KAEK lookup works end-to-end

### Task 8.2: Zoning tab full check
- [ ] **Test**: Manual + backend running
  - Select EGSA87, enter coords, select intended use, click CHECK ZONING
  - Spinner shows during request
  - Verdict card displays with correct color and emoji
  - Meta grid shows municipality, land use, zone
  - Risk flags displayed as categorized cards with level badges
  - Building params grid: coverage %, factor, height, floors, min lot, frontage, building system, FEK link
  - Data source line shown
  - Disclaimer shown
  - Leaflet map with color-coded marker + 100m circle
  - Reverse geocode address shown
- [ ] **Implement**:
  - Coordinate system toggle (EGSA87/WGS84 field visibility)
  - Intended use selector
  - Optional area input
  - CHECK ZONING button handler with spinner
  - POST to /api/v1/zoning/check
  - Result rendering: verdict, meta, risk flags, building params, map
- [ ] **Verify**: Full zoning check flow works

---

## Phase 9: Integration & Polish

### Task 9.1: Known issues fixes
- [ ] Fix `--muted` CSS var usage (not `--text-secondary`)
- [ ] Fix `--accent` CSS var for FEK links (not `--primary`)
- [ ] Scope `switchInputMode()` selector to `#tab-convert .input-mode-btn`
- [ ] Fix or remove "Show all rows" button (either show all or remove)

### Task 9.2: Cross-tab integration testing
- [ ] **Test**: Full flow with backend running
  - Convert: single point, multi-point, file upload, all exports
  - Zoning: KAEK lookup, full check, fallback when TEE is down
  - i18n: toggle EL/EN on every tab, verify all strings
  - Theme: toggle dark/light on every tab
  - Mobile: test at 360px viewport
- [ ] Fix any issues found

### Task 9.3: Shared utilities verification
- [ ] `showToast()` displays and fades correctly
- [ ] `reverseGeocode()` respects current language
- [ ] `escapeHtml()` prevents XSS
- [ ] `copyValue()` / `fallbackCopy()` work across browsers
- [ ] Error states: TEE timeout, invalid coordinates, network failure

---

## Summary

| Phase | Tasks | Focus |
|-------|-------|-------|
| 0 | 1 | Scaffolding |
| 1 | 2 | Coordinate math (backend) |
| 2 | 1 | Pydantic models |
| 3 | 2 | Static JSON data |
| 4 | 2 | TEE service (mocked) |
| 5 | 3 | FastAPI app + routers |
| 6 | 2 | Frontend skeleton + i18n |
| 7 | 3 | Convert tab (client-side) |
| 8 | 2 | Zoning tab (backend-dependent) |
| 9 | 3 | Polish + integration |
| **Total** | **21 tasks** | |
