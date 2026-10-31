# NetCoop web app — Phase 1

The original Streamlit **app.py is unchanged**. This is a separate user interface and FastAPI adapter, backed by the **same** `src.graph.workflow.diagnose`, SQLAlchemy repository, telemetry normalizer, and timestamp-aware device inventory.

## Local development

Requirements: Python 3.11+, Node.js 20+ (Next.js 15), npm.

Terminal A from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[api,test]"
# For optional Gemini, additionally install -e ".[llm-gemini]" and configure .env
export NETCOOP_LLM_MODEL=""
export NETCOOP_DB_PATH="data/netcoop.db"
export NETCOOP_CORS_ORIGINS="http://localhost:3000"
python -m uvicorn api.main:app --reload --port 8000
```

On Windows, activate `.venv\\Scripts\\activate` and use PowerShell `$env:NETCOOP_LLM_MODEL=""`.

Terminal B:

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000. The API docs are at http://localhost:8000/docs. Run the API smoke suite from the root with `python -m pytest tests/test_api.py -v`.

## Phase 1 frontend routes

- `/`: latest-per-device operational overview and counts
- `/devices`: device inventory and color-coded metrics
- `/diagnose`: run the existing five-agent workflow against a custom JSON object
- `/import`: upload or paste multiple JSON telemetry readings, retaining per-device history
- `/campus`: geographic reference POIs (no fake network topology)
- `/technical`: separate saved incident JSON and ACP message log

The static web app is a connected skeleton, not the completed 3D campus experience. Phase 2 can add 3D / MapLibre graphics and validated device-location associations.

## API endpoints

`GET /api/health`, `/api/scenarios`, `/api/overview/summary`, `/api/devices/latest`,
`/api/devices/{device_id}`, `/api/devices/{device_id}/history`,
`/api/incidents`, `/api/incidents/{record_id}`, `/api/incidents/{record_id}/messages`,
`/api/map/regions`, `POST /api/diagnose`, `POST /api/telemetry/import`.

Imports accept `{"records":[{...},{...}]}`. The API prevalidates all device IDs and timestamp fields before importing. It returns per-record failures rather than silently discarding records. Existing Streamlit imports accept JSONL/arrays separately; these endpoints are designed for a browser client.

## Free Render deployment

`render.yaml` provisions a **Python free web service** and a **static Next.js export**. Configure `NETCOOP_CORS_ORIGINS` to the published frontend URL (no trailing slash), and `NEXT_PUBLIC_API_URL` to the public API URL; redeploy the frontend when changing its public API URL since it is baked into the static build.

**Important persistence caveat:** Render's free web-service filesystem is ephemeral. SQLite at `/tmp/netcoop.db` is wiped when the service restarts, redeploys or migrates; instances may sleep. That is acceptable for a *disposable demonstration only*, **not** for a durable multi-user deployment. For durable free hosting, connect a suitable managed relational database and implement/test the corresponding persistence migration before promising retained history. Do not claim Render free provides a persistent SQLite disk.

**Security:** Phase 1 has no user authentication or abuse protection. Never expose private telemetry or real campus network data on a public API, and avoid enabling billable Gemini calls for unauthenticated public requests. Deploy with `NETCOOP_LLM_MODEL` empty by default, or add authentication, rate limits and request budgets first.

CORS limits browser origins but **is not authentication**. No actual IIT Bhubaneswar network access or live monitoring is implied.

## Phase 2 — interactive campus scene

The web UI now uses an editorial architectural design language: limestone backgrounds, charcoal sidebar, terracotta actions, ochre warnings and forest-green healthy states (no neon/cyan AI-dashboard styling).

The `/campus` view uses **React Three Fiber, Three.js and Drei** to render a fully interactive, orbitable/zoomable illustrative campus scene. Region labels are derived from named geographic reference locations, but **building geometry and spacing are abstract illustrations, not surveyed IIT Bhubaneswar building footprints or actual network topology**. Each region starts neutral. A user can select a device from the database and explicitly assign it to one region for a simulated demonstration. Region state uses the most recent observation per mapped device, with precedence fault > inconclusive > healthy, and displays a red animated alert for faults. The region inspector lists the devices and their diagnoses.

New API:
- `GET /api/map/regions` — region metadata, assigned devices and computed state
- `POST /api/map/assign` — JSON `{"device_id":"SW1","region_id":"labs"}`, or `"region_id":null` to remove an assignment

Mappings are stored in `demo_campus_assignments`, an additional local SQLite table. Existing Streamlit UI, `app.py`, agent logic and original tables are unchanged. Free Render service restarts **will erase** local SQLite mapping and incident data.

Run `python -m pytest tests/test_api.py -v` and `cd frontend && npm install && npm run build`. The static Next.js build can deploy to a free Render Static Site, but the 3D view requires browser WebGL support. UI verification in a local browser is still necessary. For rendering performance, the 3D scene caps device pixel ratio and supports orbit/zoom. Reduced-motion user settings disable CSS transitions; full 3D animation reduction remains future enhancement.

**Do not expose** the unauthenticated Phase 2 demo mapping endpoints or telemetry ingestion to sensitive real network information. Phase 2 illustrates possible operations visualization and does not claim a live campus feed.

## Phase 3 — forensic timeline and saved multi-agent investigations

Two pages are available in the new Next.js frontend:

- `/playback`: a play/pause timeline of *actual stored* telemetry timestamps (UTC), with a scrubber, device condition counts, and one latest-known diagnosis per device as of each selected timepoint. Device cards open the corresponding investigation.
- `/agents`: a selectable incident, five-stage workflow navigator, actual saved ACP messages, specialist evidence (when stored), final root cause, support score, and recommendations.

API: `GET /api/playback/events?limit=500` (at most 500 dated historical records from a scan of the 5,000 most recently saved incidents, sorted by observation timestamp; undated rows are excluded and counted) and `GET /api/incidents/{record_id}/investigation`. This is a **historical visualization**, not a live timing trace: because specialists run in parallel, the five steps represent the logical workflow, not measured execution ordering or durations. Only persisted messages and findings are displayed; no Gemini responses or inter-agent conclusions are invented.

For local verification run `python -m pytest tests/test_api.py -v` in the project root and `npm run build` in `frontend/`. On Render static hosting there is no paid map dependency; API and persistent data limitations from Phases 1–2 still apply. Existing Streamlit code was not changed.

## Phase 4 — spatial playback inside the interactive 3D campus

Open `/campus` and enable **Historical mode**. Play, pause, or scrub the saved telemetry timepoints. The same Three.js 3D regions now recompute their condition for each historical frame, using the last available diagnosed observation per device at or before that time. Red denotes one or more diagnosed faults, ochre denotes an inconclusive assessment with no diagnosed fault, and forest green denotes all mapped devices healthy. Unmapped or not-yet-observed regions remain stone-neutral. Device details in the region inspector follow the same frame.

`GET /api/map/history?limit=500` responds with timestamped `frames`, each containing the region states and the per-device observation that produced them. The endpoint reuses the existing bounded `playback_events` history and the saved manual demo assignments; no extra database tables or changes to `app.py` were required.

**Historical mapping caveat:** Only current manual assignments are stored. They are applied retroactively during replay; the app does not store historical device moves, real building footprints, or real network topology. A sequence can also be incomplete when records exceed the 500-event window or 5,000-record scan cap. Importantly, there is **no automatic region assignment** based solely on device IDs.

Tests: `python -m pytest tests/test_api.py -v` now covers out-of-order uploads, time-based region transitions, unmapped devices, and endpoint input bounds. From `frontend/`, run `npm install && npm run build` and verify WebGL interaction in a browser. Free Render hosting limitations and API authentication warnings from previous phases remain in force.

## Phase 5 — network intelligence and incident command

New routes on the **separate Next.js** frontend:

- `/incidents`: an incident command desk with status filters, latest saved root-cause report, actionable recommendations, limitations, a link to the original ACP investigation, and a severity-weighted fault-evidence explanation.
- `/devices`: clicking **Inspect** additionally displays a per-metric historical trend chart. The historical measurements are read from each saved normalized telemetry snapshot and sorted by observation timestamp, not upload order. Charts omit missing samples rather than plotting misleading zeros; lines are visual aids between discrete samples.

Read-only API routes:

- `GET /api/intelligence/incidents?limit=100` (maximum 200): summarized saved incident reports.
- `GET /api/incidents/{record_id}/evidence`: weighted evidence inputs, missing-metric penalty, and stored authoritative final support score.
- `GET /api/devices/{device_id}/trends?limit=100` (maximum 500): timestamped numerical metric series for a device.

**Scoring integrity:** The original engine computes the final score. The audit does not invent a healthy percentage or claim fault support is a statistically calibrated probability. Stored ACP messages contain specialist severity evidence but not a separate persisted arbitration/conflict-penalty parameter. Therefore the audit identifies the conflict penalty as *not persisted* and does not claim its breakdown always exactly reconstructs the final score.

This phase adds no map services, paid libraries, or new data stores; the Render free-tier caveats and unauthenticated-API limitations from previous phases remain. Existing Streamlit `app.py` is unchanged.

Validation: run `python -m pytest tests/test_api.py -v` and `cd frontend && npm install && npm run build`; browser verification remains required before publishing.
