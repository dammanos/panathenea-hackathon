"""AI property report generation using Anthropic Claude."""

import os
from dataclasses import asdict

import anthropic


def _extract_label(features: list) -> str | None:
    if features and isinstance(features, list) and len(features) > 0:
        attrs = features[0].get("attributes", {})
        return attrs.get("LABEL") or attrs.get("label")
    return None


def _extract_all_attrs(features: list) -> list[dict]:
    out = []
    for f in features:
        attrs = f.get("attributes", {})
        clean = {k: v for k, v in attrs.items()
                 if v and k not in ("OBJECTID", "Shape", "SHAPE", "Shape_Length", "Shape_Area", "GlobalID")}
        if clean:
            out.append(clean)
    return out


def _format_layer_data(all_layers: dict, kaek_info: dict) -> str:
    """Format all TEE layer data into a comprehensive text block for the AI."""
    parts = []

    # --- Parcel identity ---
    parts.append("=== PARCEL IDENTITY ===")
    parts.append(f"KAEK: {kaek_info.get('kaek', 'N/A')}")
    if kaek_info.get("area_m2"):
        parts.append(f"Cadastre Area: {kaek_info['area_m2']:.2f} m²")
    if kaek_info.get("lat") and kaek_info.get("lon"):
        parts.append(f"WGS84: {kaek_info['lat']:.6f}, {kaek_info['lon']:.6f}")
    if kaek_info.get("x") and kaek_info.get("y"):
        parts.append(f"EGSA87: {kaek_info['x']:.2f}, {kaek_info['y']:.2f}")

    # Cadastre attributes
    cad = kaek_info.get("cadastre_attrs", {})
    if cad:
        for k, v in cad.items():
            if v and k not in ("OBJECTID", "Shape", "GlobalID", "SHAPE"):
                parts.append(f"  Cadastre.{k}: {v}")

    # --- Municipality ---
    muni = all_layers.get("municipality", [])
    if muni:
        parts.append("\n=== MUNICIPALITY (ELSTAT 2021) ===")
        for a in _extract_all_attrs(muni):
            for k, v in a.items():
                parts.append(f"  {k}: {v}")

    # --- Plan status ---
    parts.append("\n=== PLAN STATUS ===")
    settlement = all_layers.get("settlement_boundary", [])
    outside = all_layers.get("outside_plan", [])
    city_plan = all_layers.get("city_plan_boundary", [])

    if city_plan:
        parts.append("Within APPROVED CITY PLAN boundary (Εντός εγκεκριμένου σχεδίου)")
        for a in _extract_all_attrs(city_plan):
            for k, v in a.items():
                parts.append(f"  {k}: {v}")
    elif settlement:
        parts.append("Within SETTLEMENT BOUNDARY (Εντός ορίου οικισμού)")
        for a in _extract_all_attrs(settlement):
            for k, v in a.items():
                parts.append(f"  {k}: {v}")
    elif outside:
        parts.append("OUTSIDE CITY PLAN (Εκτός σχεδίου)")
        for a in _extract_all_attrs(outside):
            for k, v in a.items():
                parts.append(f"  {k}: {v}")
    else:
        parts.append("Plan status: Could not determine from TEE data")

    # --- Building parameters ---
    parts.append("\n=== BUILDING PARAMETERS (TEE UDM) ===")
    param_map = {
        "sd": "Building Factor (Σ.Δ.)",
        "height": "Max Height / Floors",
        "coverage": "Coverage Ratio (Κάλυψη)",
        "artiotita": "Min Lot Size (Αρτιότητα)",
        "land_use": "Land Use (Χρήσεις Γης ΕΡΣ)",
        "land_use_gps": "Land Use GPS (Χρήσεις Γης ΓΠΣ)",
        "zone_sector": "Zone / Sector (Πολεοδομική Ενότητα)",
        "building_system": "Building System (Οικοδομικό Σύστημα)",
    }
    for key, label in param_map.items():
        features = all_layers.get(key, [])
        lbl = _extract_label(features)
        if lbl:
            parts.append(f"  {label}: {lbl}")
        if features:
            for a in _extract_all_attrs(features):
                for k, v in a.items():
                    if k not in ("LABEL", "label"):
                        parts.append(f"    {k}: {v}")

    # --- Environmental restrictions ---
    parts.append("\n=== ENVIRONMENTAL RESTRICTIONS ===")

    natura = all_layers.get("natura", [])
    if natura:
        parts.append(f"NATURA 2000: {len(natura)} zone(s) within 1km:")
        for a in _extract_all_attrs(natura):
            name = a.get("SITE_NAME") or a.get("SITENAME") or "Unknown"
            code = a.get("SITECODE", "")
            parts.append(f"  - {name} ({code})")
    else:
        parts.append("NATURA 2000: None within 1km")

    forest = all_layers.get("forest", [])
    if forest:
        parts.append(f"FOREST MAP (Δασικός Χάρτης): OVERLAP FOUND ({len(forest)} feature(s))")
        for a in _extract_all_attrs(forest):
            for k, v in a.items():
                parts.append(f"  {k}: {v}")
    else:
        parts.append("FOREST MAP: No overlap")

    shoreline = all_layers.get("shoreline", [])
    if shoreline:
        parts.append(f"SHORELINE (Αιγιαλός/Παραλία): Within 200m buffer")
        for a in _extract_all_attrs(shoreline):
            for k, v in a.items():
                parts.append(f"  {k}: {v}")
    else:
        parts.append("SHORELINE: Not within 200m")

    streams = all_layers.get("streams", [])
    if streams:
        parts.append(f"DELINEATED STREAMS (Οριοθετημένα Ρέματα): {len(streams)} within 200m")
        for a in _extract_all_attrs(streams):
            for k, v in a.items():
                parts.append(f"  {k}: {v}")

    env_streams = all_layers.get("env_streams", [])
    if env_streams:
        parts.append(f"ENVIRONMENTAL STREAMS: {len(env_streams)} within 200m")

    # --- Archaeological restrictions ---
    parts.append("\n=== ARCHAEOLOGICAL RESTRICTIONS ===")
    arch_poleo = all_layers.get("arch_zone_poleo", [])
    arch_keys = [k for k in all_layers if k.startswith("arch_")]
    all_arch = []
    for k in arch_keys:
        for f in all_layers.get(k, []):
            cat = k.replace("arch_", "")
            f["_category"] = cat
            all_arch.append(f)
    if arch_poleo:
        all_arch.extend(arch_poleo)

    if all_arch:
        parts.append(f"ARCHAEOLOGICAL: {len(all_arch)} zone(s) within 500m:")
        for f in all_arch:
            a = f.get("attributes", {})
            cat = f.get("_category", "unknown")
            name = a.get("NAME") or a.get("ONOMASIA") or a.get("LABEL") or "Unknown"
            parts.append(f"  - [{cat}] {name}")
    else:
        parts.append("ARCHAEOLOGICAL: None within 500m")

    # --- Regulatory framework ---
    parts.append("\n=== REGULATORY FRAMEWORK ===")
    zoe = all_layers.get("zoe", [])
    if zoe:
        parts.append(f"ZOE (Ζώνη Οικιστικού Ελέγχου): {len(zoe)} zone(s)")
        for a in _extract_all_attrs(zoe):
            for k, v in a.items():
                parts.append(f"  {k}: {v}")
    else:
        parts.append("ZOE: Not within any ZOE zone")

    pd_prot = all_layers.get("pd_protection", [])
    if pd_prot:
        parts.append(f"PD PROTECTION (Π.Δ. Προστασίας): {len(pd_prot)} zone(s)")
        for a in _extract_all_attrs(pd_prot):
            for k, v in a.items():
                parts.append(f"  {k}: {v}")

    expropriation = all_layers.get("expropriation", [])
    if expropriation:
        parts.append(f"EXPROPRIATION ZONE (Απαλλοτρίωση): YES — {len(expropriation)} zone(s)")
        for a in _extract_all_attrs(expropriation):
            for k, v in a.items():
                parts.append(f"  {k}: {v}")

    # --- Other ---
    public = all_layers.get("public_spaces", [])
    if public:
        parts.append(f"\nPUBLIC/COMMON SPACES (Κοινόχρηστοι): Overlaps with {len(public)} zone(s)")
        for a in _extract_all_attrs(public):
            for k, v in a.items():
                parts.append(f"  {k}: {v}")

    protected_bldg = all_layers.get("protected_buildings", [])
    if protected_bldg:
        parts.append(f"\nPROTECTED BUILDINGS (Διατηρητέα): {len(protected_bldg)} within 200m")
        for a in _extract_all_attrs(protected_bldg):
            for k, v in a.items():
                parts.append(f"  {k}: {v}")

    # --- Building Permits ---
    permits = all_layers.get("building_permits", [])
    if permits:
        parts.append(f"\n=== BUILDING PERMITS 2011-2018 (within 500m) ===")
        parts.append(f"Total permits found: {len(permits)}")
        for f in permits:
            a = f.get("attributes", {})
            clean = {k: v for k, v in a.items()
                     if v and k not in ("OBJECTID", "Shape", "SHAPE", "Shape_Length", "Shape_Area", "GlobalID")}
            if clean:
                permit_no = a.get("PERMIT_NO") or a.get("AR_ADEIAS") or a.get("ARITHMOS") or "N/A"
                parts.append(f"  --- Permit: {permit_no} ---")
                for k, v in clean.items():
                    parts.append(f"    {k}: {v}")

    # --- YPD Building Block (Οικοδομικά Τετράγωνα) ---
    ypd_blocks = all_layers.get("ypd_blocks", [])
    if ypd_blocks:
        parts.append(f"\n=== YPD BUILDING BLOCK (Οικοδομικό Τετράγωνο) ===")
        for a in _extract_all_attrs(ypd_blocks):
            for k, v in a.items():
                parts.append(f"  {k}: {v}")

    # --- YPD Density (Σ.Δ.) ---
    ypd_density = all_layers.get("ypd_density", [])
    if ypd_density:
        parts.append(f"\n=== YPD BUILDING DENSITY (Σ.Δ. from YPD) ===")
        for a in _extract_all_attrs(ypd_density):
            for k, v in a.items():
                parts.append(f"  {k}: {v}")

    # --- YPD Settlement Boundary ---
    ypd_settlement = all_layers.get("ypd_settlement", [])
    if ypd_settlement:
        parts.append(f"\n=== YPD SETTLEMENT BOUNDARY ===")
        for a in _extract_all_attrs(ypd_settlement):
            for k, v in a.items():
                parts.append(f"  {k}: {v}")

    # --- FEK Documents ---
    fek_docs = all_layers.get("fek_documents", [])
    if fek_docs:
        parts.append(f"\n=== FEK DOCUMENTS (within 500m) ===")
        parts.append(f"Total FEK documents found: {len(fek_docs)}")
        for f in fek_docs:
            a = f.get("attributes", {})
            clean = {k: v for k, v in a.items()
                     if v and k not in ("OBJECTID", "Shape", "SHAPE", "Shape_Length", "Shape_Area", "GlobalID")}
            if clean:
                fek_ref = a.get("FEK_NO") or a.get("FEK") or a.get("ARITHMOS_FEK") or "N/A"
                parts.append(f"  --- FEK: {fek_ref} ---")
                for k, v in clean.items():
                    parts.append(f"    {k}: {v}")

    # --- Survey Diagrams ---
    diagrams = all_layers.get("survey_diagrams", [])
    if diagrams:
        parts.append(f"\n=== SURVEY DIAGRAMS (within 500m) ===")
        parts.append(f"Total diagrams found: {len(diagrams)}")
        for f in diagrams:
            a = f.get("attributes", {})
            clean = {k: v for k, v in a.items()
                     if v and k not in ("OBJECTID", "Shape", "SHAPE", "Shape_Length", "Shape_Area", "GlobalID")}
            if clean:
                parts.append(f"  --- Diagram ---")
                for k, v in clean.items():
                    parts.append(f"    {k}: {v}")

    # --- Address (Nominatim) ---
    address = kaek_info.get("address", {})
    if address:
        parts.append("\n=== ADDRESS (Nominatim) ===")
        for k, v in address.items():
            if v:
                parts.append(f"  {k}: {v}")

    # --- FEK references ---
    fek_found = []
    for key, features in all_layers.items():
        for f in (features if isinstance(features, list) else []):
            attrs = f.get("attributes", {})
            for k, v in attrs.items():
                if k.upper() in ("FEK", "FEK_NO", "NOMOS_FEK", "ΦΕΚ", "FEK_NUMBER", "FEK_AR", "ARITHMOS_FEK") and v:
                    fek_found.append(f"  {key}: {v}")
    if fek_found:
        parts.append("\n=== FEK REFERENCES FOUND ===")
        parts.extend(fek_found)

    return "\n".join(parts)


SYSTEM_PROMPT = """You are an expert Greek property surveyor (Τοπογράφος Μηχανικός) assistant. Based on the following comprehensive government data retrieved from TEE (Technical Chamber of Greece) Unified Digital Map and the National Cadastre, generate a professional property due diligence report in Greek.

The report MUST include ALL of the following sections:

## Περίληψη
Executive summary: 3-4 sentences covering property location, plan status (εντός/εκτός σχεδίου), key building params, and any critical restrictions.

## Ταυτότητα Ακινήτου
KAEK, municipality, coordinates (EGSA87 + WGS84), cadastre area, plan status.

## Πολεοδομικά Στοιχεία
- Zone/sector name
- Building factor (Σ.Δ.), coverage (κάλυψη), max height, min lot size (αρτιότητα)
- Building system (continuous/detached)
- Land use designation (from both ΕΡΣ and ΓΠΣ if available)
- Whether inside approved city plan, settlement boundary, or outside plan

## Περιβαλλοντικοί Περιορισμοί
- Natura 2000 (with site names/codes)
- Forest map overlap (δασικός χάρτης)
- Shoreline/coastal zone (αιγιαλός/παραλία)
- Streams (ρέματα)
- Protected buildings nearby

## Αρχαιολογικοί Περιορισμοί
List all archaeological zones with categories (declared, buffer, historical, traditional settlement).

## Οικοδομικές Άδειες (εντός 500μ)
List each building permit found: permit number, property area, building area, height, floors, year, permit type. This shows what has been built nearby.

## ΦΕΚ & Διαγράμματα
- FEK documents with direct PDF links (use the URLs as-is from the data)
- YPD building block decree (FEK reference, dates, decree type)
- Survey diagrams with links and accuracy (RMS)
- Include all URLs — the surveyor will click them

## Κανονιστικό Πλαίσιο
- ZOE zones and their terms
- PD protection zones
- Expropriation zones
- FEK references found in the data
- Public/common use space overlaps

## Εκτίμηση Κινδύνου
Traffic-light assessment: GREEN (no issues), YELLOW (minor concerns), RED (significant restrictions).
List each risk with severity.

## Συστάσεις
Specific, actionable next steps for the property owner/buyer/engineer.

IMPORTANT RULES:
- Be specific: use exact numbers, zone names, and site codes from the data
- If a section has no data, explicitly state "Δεν βρέθηκαν δεδομένα από τις υπηρεσίες ΤΕΕ"
- Use markdown formatting with ## headers
- This is for a PROFESSIONAL surveyor — use technical terminology correctly
- Note the data sources (TEE UDM, Κτηματολόγιο)
- If YPD BUILDING DENSITY data is available, prefer it over the POLEODOMIKI Σ.Δ. — it is more reliable
- Include ALL FEK PDF URLs and diagram URLs as clickable links — these are high-value for surveyors
- For building permits, list each one with specific numbers (area, height, floors) — don't just summarize
- If address data is available, include it in the Ταυτότητα Ακινήτου section
- A "COMPUTED BUILDABILITY" section may be provided. Those values are calculated
  deterministically by the system from the planning parameters. You MUST use those
  exact numbers in the Πολεοδομικά Στοιχεία section (max δόμηση, max κάλυψη,
  ενδεικτικοί όροφοι, αρτιότητα). Do NOT recompute, round differently, or invent
  buildability figures. Repeat any warnings it contains."""


def _format_buildability(bld: dict | None) -> str:
    """Render the deterministically-computed buildability as an authoritative block."""
    if not bld:
        return ""
    lines = ["=== COMPUTED BUILDABILITY (authoritative — use these exact values) ==="]
    if bld.get("max_floor_area_m2") is not None:
        lines.append(f"Max buildable floor area (δόμηση): {bld['max_floor_area_m2']} m²")
    if bld.get("max_footprint_m2") is not None:
        lines.append(f"Max ground footprint (κάλυψη): {bld['max_footprint_m2']} m²")
    if bld.get("indicative_max_floors") is not None:
        lines.append(f"Indicative max floors: {bld['indicative_max_floors']}")
    if bld.get("is_buildable_lot") is not None:
        lines.append(f"Buildable lot (άρτιο & οικοδομήσιμο): {'ΝΑΙ' if bld['is_buildable_lot'] else 'ΟΧΙ'}")
    if bld.get("inputs_used"):
        lines.append(f"Inputs used: {bld['inputs_used']}")
    for w in bld.get("warnings", []):
        lines.append(f"WARNING: {w}")
    for a in bld.get("assumptions", []):
        lines.append(f"ASSUMPTION: {a}")
    return "\n".join(lines)


async def generate_property_report(all_layers: dict, kaek_info: dict, buildability=None) -> str:
    """Generate an AI property due diligence report using Claude.

    ``buildability`` is the deterministically-computed result (a dataclass or
    dict); when provided it is prepended as authoritative ground-truth so the
    model explains real numbers instead of guessing them.
    """
    if buildability is not None and not isinstance(buildability, dict):
        buildability = asdict(buildability)

    layer_data = _format_layer_data(all_layers, kaek_info)
    bld_block = _format_buildability(buildability)
    if bld_block:
        layer_data = bld_block + "\n\n" + layer_data

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY not set."

    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4000,
            temperature=0.2,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": "RAW GOVERNMENT DATA:\n" + layer_data}
            ],
        )
        return message.content[0].text
    except anthropic.RateLimitError:
        return "Error: Claude API rate limited. Try again in a moment."
    except anthropic.APIError as e:
        return f"Error: Claude API returned {e.status_code}: {str(e)[:200]}"
    except Exception as e:
        return f"Error calling Claude API: {str(e)}"
