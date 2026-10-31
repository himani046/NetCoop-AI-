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
