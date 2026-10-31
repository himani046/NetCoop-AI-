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
