# NetCoop — Campus Network Operations frontend

This is a **frontend-only** Next.js/TypeScript UI for the existing NetCoop API. The Streamlit application, FastAPI backend, LangGraph workflow, SQLite database, and diagnosis rules are unchanged.

## Local startup

From the repository root, run your existing FastAPI service:

```sh
python -m uvicorn api.main:app --reload --port 8000
```

In a second terminal:

```sh
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000. Run `npm run lint` (TypeScript typecheck) and `npm run build` before deployment.

## Frontend routes

- `/`: command dashboard, health counts, geographic overview, root-cause priorities.
- `/satellite`: MapLibre map with status markers and current backend demo assignments.
- `/campus`: existing interactive Three.js campus representation and historical spatial playback (illustrative geometry).
- `/devices`: timestamp-aware inventory and metric history.
- `/incidents`: saved diagnostic report and evidence score explanation.
- `/events`: chronological recorded observations.
- `/playback`: saved device health over time.
- `/agents`: persisted multi-agent ACP investigation.
- `/courtroom`: evidence, limitations, and unmodified saved root cause verdict.
- `/experience`: guided human input for actual metrics, submitted to the existing diagnosis endpoint.
- `/investigation`: adaptive *test recommendations*, not automated device probing.
- `/diagnose`: raw telemetry diagnosis.
- `/import`: preflight review, JSON file import, persisted results.
- `/configure`: API readiness, saved inventory, demo mapping, and blank JSON template.
- `/technical`: raw incident/ACP records.

## Satellite imagery setup

MapLibre defaults to OpenStreetMap **street** tiles; OSM is not satellite imagery.

For imagery, select a **licensed satellite map provider** that explicitly permits public browser use, respects usage limits, and exposes a MapLibre-compatible style URL. Set `NEXT_PUBLIC_SATELLITE_STYLE_URL` in the frontend's environment (and redeploy, as this is a statically exported app). A provider such as MapTiler may offer free-tier keys, subject to quotas and attribution terms. **Restrict public map keys by HTTP origin.** Client-side public map keys cannot be treated as secret. Do not use scraped Google or Esri satellite tiles. The style URL will usually embed the provider's allowed browser key. Validate the provider's specific terms and attribution.

The existing API supplies *reference coordinates*, not surveyed building polygons. Status markers indicate the latest diagnosis of manually mapped **synthetic test devices**; they do not describe an actual physical building-wide outage. No geographic cable lines are fabricated without known endpoint coordinates.

## Operational integrity and constraints

- Actual diagnosis comes solely from `POST /api/diagnose`; the browser does not invent fault results.
- `/investigation` suggests measurements via frontend rules; it cannot execute remote network tests without backend support.
- `/configure` checks the existing API and offers a blank JSON template; it cannot auto-poll hardware, detect software upgrades, or generate authoritative telemetry.
- Evidence support scores are *fault evidence*, not health correctness probabilities.
- Free Render static hosting is supported; the free API's local SQLite file is ephemeral across restarts and redeployments, so durable hosted history requires a backend database migration.
- Authentication, rate limits, access control, paid API quotas, and real campus device permissions require separate backend work before production use.

All changes in this redesign are inside `frontend/`.

## 3D campus upgrade (OSM footprints)

The `/campus` view uses MapLibre WebGL with interactive geographic **OpenStreetMap building footprints** fetched client-side from a bounded IIT Bhubaneswar / Argul campus Overpass query. Footprints are extruded into 3D. Their real plan shape comes from OSM, but **building heights are illustrative** when no `building:levels` tag exists. A building is labeled by its OSM `name` tag when available; unnamed polygons are explicitly identified as unnamed. **Complete coverage of every IIT Bhubaneswar building cannot be guaranteed by OSM data.** Failed or blocked Overpass requests leave reference status markers accessible and display a geometry-unavailable warning.

The existing API's named campus reference points and device-region assignments are separate from OSM building polygons. Hovering a status marker shows the assigned region; the right inspector provides saved device diagnoses, up to five previous observations and available parent-device metadata. Clicking a building footprint reveals its OSM name and object ID, without falsely assigning network equipment by spatial proximity. Only explicitly configured device assignments may influence health colors.

The `/campus` route also includes a **logical upstream topology panel** based on available saved parent IDs; it does not draw fictitious network cabling on top of satellite images. Historical region status playback remains available through the existing API. Satellite imagery is optional via the same `NEXT_PUBLIC_SATELLITE_STYLE_URL` configuration; OSM standard raster tiles are a **street map**, not aerial images. Overpass availability and permitted usage depend on the public service.

The reference UI is an operations design direction and is not an actual accurate photogrammetric campus twin.

### IIT-campus-only satellite mode

The 3D canvas is constrained to the **approximate Argul-campus vicinity** with a fixed MapLibre pan boundary ([85.666,20.143]–[85.683,20.153]). These coordinates are a viewport boundary, **not an official surveyed campus land parcel**. A list displays every building name returned by the OSM building footprint query; unnamed or missing OSM buildings cannot be truthfully labeled. Geographically accurate complete coverage would require an official named-footprint dataset.

Set `NEXT_PUBLIC_MAPTILER_KEY` to a valid origin-restricted browser key in `frontend/.env.local` to select MapTiler's satellite-v4 style automatically, or use `NEXT_PUBLIC_SATELLITE_STYLE_URL` with a licensed compatible style. Map imagery is not bundled or used without an authorized provider. Restart Next.js after editing `.env.local`.

Blue dashed lines and labels between manually located demo regions indicate existing `parent_id` relationships **only when both endpoint devices have manual region assignments**. They are schematic connections between reference points, not known cable routes or automatic failure propagation. Hovering a mapped network region reveals the real saved diagnosis and history.

### Router fault alarm overlays (frontend-only)

Both `/satellite` and `/campus` now mark a manually assigned region **red** when the API reports a diagnosed fault for one of its assigned devices; inconclusive observations remain **yellow**, healthy observations **green**, and regions lacking assigned observations neutral. The rendered fault icon is a UI representation of saved synthetic/test telemetry, **not an active hardware alarm**.

Dashed topology lines are constructed only from saved `parent_id` relationships where *both* devices have manually assigned region coordinates. The link is colored **red** if either endpoint has a diagnosed fault, and blue otherwise. Red link coloring means an endpoint diagnosis, **not verified network propagation, physical cable geography, or proven downstream outage**. Unassigned relationships remain available in the separate logical topology list.

Map imagery is not a continuous live satellite video feed. A supported licensed imagery provider returns periodically updated raster imagery; actual live network status requires a real monitoring collector and backend ingestion integration, which this frontend-only change does not implement. Existing device history and scoring logic remain unchanged.
