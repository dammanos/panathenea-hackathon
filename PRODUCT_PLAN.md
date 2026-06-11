# TopoTools — Product Plan

From hackathon MVP to a sellable **Property Intelligence platform for Greek
surveying & civil engineers**.

> **Two anchoring decisions** (locked):
> 1. **Primary customer:** surveying / civil engineers (τοπογράφοι & πολιτικοί
>    μηχανικοί). Build the deepest professional product first; expand to
>    lawyers/notaries → banks → foreign buyers later.
> 2. **Data strategy:** pursue **sanctioned/official data access** before
>    selling. Scraped GIS endpoints are fine for a demo, not for a paid product.

---

## 1. Why now (the market thesis)

The wedge is not "a nicer report." It is the **mandatory, deadline-driven,
engineer-only paperwork** that is painful today and recurs on every property
transaction:

- **Ηλεκτρονική Ταυτότητα Κτιρίου (Electronic Building Identity)** — required
  for every property transfer, must be prepared by an engineer, fines from €200
  up to **10% of objective value**, deadlines rolling through 2026. High volume,
  recurring, currently done with clunky desktop tools.
- **Topographic diagrams** — mandatory for any registrable deed that changes
  geometry; e-signed and submitted to the Cadastre.
- **Property due diligence** for transfers — the same parcel intelligence,
  repackaged for the legal/buyer side later.

**Market:** TEE has 100k+ engineer members (surveying/rural is one of 13
disciplines). Competition is fragmented — service firms and legacy desktop
CAD/permit software. **No dominant cloud "property intelligence" SaaS.** That is
the opening.

---

## 2. Product vision: "Property Intelligence OS"

Single source of truth for everything legally relevant about a Greek parcel,
with three stacked layers: **know → assess → produce.**

### Pillar A — Data & integrations (the moat)
Defensibility = breadth + freshness of *official* data, not the AI.

| Source | What we get | Access path (Phase 0 workstream) |
|--------|-------------|----------------------------------|
| Κτηματολόγιο (Cadastre) | Parcel geometry, KAEK, area, ownership-adjacent attrs | Official engineer e-services / data.gov.gr cadastre API / EGSA87 shapefiles |
| ΑΑΔΕ / ΓΓΠΣ valuation | Objective value (αντικειμενική αξία), value zones, dynamic AVM | e-APAA, valuemaps, `getPropertyDetails` / `checkValueProperty` web services |
| e-Άδειες ΤΕΕ | Actual building permits (not just 2011–2018 layer) | Open permit info system / formal TEE agreement |
| TEE UDM (34 layers) | Zoning, forest, Natura, archaeological, FEK, shoreline | Already integrated — harden, expand, formalize |
| Stretch | Orthophotos/drone, GEMI (corporate owners), αυθαίρετα status | Later phases |

### Pillar B — Intelligence layer (trust)
- **RAG over the legal corpus** (ΝΟΚ articles, FEK decrees, ΓΠΣ/ΖΟΕ) — every
  claim **cited to a source**, never free narration. Seeds already exist
  (`nok_articles.json`, `fek_index.json`).
- **Buildability engine** — *deterministic* calculator (Σ.Δ. × area, coverage,
  height, setbacks, αρτιότητα). Numbers are computed, AI only explains them.
  This is the "what can I build here?" answer worth real money.
- **Risk scoring** — rule-based + evidence-linked traffic-light; AI for prose only.
- **AVM** — objective value now, comparable/market value later.

### Pillar C — Workflow & deliverables (the revenue)
- Generate **billable artifacts**: pre-filled Electronic Building Identity
  dossiers, branded e-signable due-diligence PDFs, topographic-diagram metadata.
- **Projects & clients**: saved parcels, versioned over time, team workspaces,
  full audit trail (who generated what, from which data snapshot — liability-critical).
- **"What-if" buildability scenarios** for developers.

### Pillar D — Survey/coordinate tools (the daily hook)
Productionize the converter: batch jobs, **DXF/CAD import-export**, GNSS/RINEX,
KML/GeoJSON, more datums, precision certs. Free tier → gets engineers in the door.

### Pillar E — SaaS productionization
Auth/SSO, multi-tenant, billing, rate limits, **caching of gov data**, queueing
for the layer fan-out, observability, public API (later), white-label.

### Pillar F — Trust, compliance, liability (non-negotiable)
- **Provenance + timestamps** on every field ("source: TEE UDM layer X, fetched
  2026-06-06").
- GDPR (KAEK/owner data), professional-liability disclaimers, human-in-the-loop
  sign-off, qualified e-signature.
- Legal review of every data-access ToS.

---

## 3. Monetization
- **Free:** coordinate converter + 1–2 sample reports (acquisition hook).
- **Pro (per-seat, ~€30–80/mo):** unlimited reports, projects, exports.
- **Credits / per-deliverable:** Building Identity dossier, full due-diligence
  PDF — the high-margin items.
- **Teams / white-label:** firm branding, seats, audit.
- **API / enterprise (later):** banks, law firms, PropTech — usage-based.

---

## 4. Roadmap (engineer-anchored, sanctioned-data-first)

### Phase 0 — Foundations & data access *(gate — must clear before selling)*
- **Data-access legal workstream**: formal agreements / sanctioned APIs for
  Κτηματολόγιο, ΑΑΔΕ valuation, e-Άδειες. Treat as a hard prerequisite.
- Productionize: auth, persistence (Postgres + PostGIS), caching layer for gov
  data, provenance stamping, real error handling, observability.
- *(Already started: CORS fix, dotenv, clickable report links, dead-file cleanup.)*

### Phase 1 — Commercial v1 for engineers
- **Buildability engine** (deterministic) + **cited legal RAG**.
- Branded, e-signable **due-diligence PDF** export.
- Saved **projects/clients**, audit trail.
- Stripe billing; Pro seats + free converter tier.

### Phase 2 — The revenue engine
- **Electronic Building Identity** workflow (pre-fill from cadastre + permits).
- **ΑΑΔΕ valuation** integration (objective value + AVM).
- Pro survey tools: DXF/CAD, batch, GNSS.

### Phase 3 — Platform & expansion
- Public API + white-label; expand to notaries/banks; market-value AVM.

---

## 5. Top risks
1. **Data-access legality (existential).** Scraping is fragile and likely
   ToS-violating for a paid product. Phase 0 gate exists for this reason.
2. **Professional liability.** A wrong AI claim on a stamped deliverable = lawsuit.
   Mitigate: citations, provenance, human sign-off, insurance, disclaimers.
3. **Hallucination on legal/numeric claims.** Make numbers deterministic; force
   citations; never let the LLM invent a Σ.Δ. or FEK number.
4. **Data freshness.** Gov data changes — cache with timestamps, re-validate.

---

## 6. Immediate next steps
1. Open the **data-access workstream** (identify the official API/agreement path
   for each source; this is the long pole).
2. Spike the **deterministic buildability engine** against real parcels (no AI).
3. Stand up **persistence + auth** (Postgres/PostGIS) and provenance stamping.
4. Prototype **cited legal RAG** over ΝΟΚ/FEK seeds with strict source-linking.
