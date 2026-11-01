# NetCoop AI — Campus Network Intelligence

**Evidence-first multi-agent network fault diagnosis, with an interactive IIT Bhubaneswar campus operations dashboard and optional Google Gemini explanations.**

**[Live frontend](https://netcoop-ui.onrender.com)** · **[Backend health](https://netcoop-api.onrender.com/api/health)** · **[Frontend technical guide](frontend/README.md)**

> **Prototype status:** Uses manually uploaded synthetic/test network telemetry. It does **not** poll IIT Bhubaneswar routers, detect verified physical cable outages, receive live satellite video, or monitor production campus infrastructure. Campus device assignments are demo mappings. No authentication or tenant isolation is implemented.

## Contents

1. [Problem and solution](#problem-and-solution)
2. [What the application includes](#what-the-application-includes)
3. [Five-agent architecture](#five-agent-architecture)
4. [How telemetry JSON works](#how-telemetry-json-works)
5. [Run locally](#run-locally)
6. [REST API reference](#rest-api-reference)
7. [Gemini configuration and limitations](#gemini-configuration-and-limitations)
8. [Campus maps and topology](#campus-maps-and-topology)
9. [Database, privacy and hosting](#database-privacy-and-hosting)
10. [Testing and 5-minute demo](#testing-and-5-minute-demo)
11. [Project layout and roadmap](#project-layout-and-roadmap)

## Problem and solution

Large networks produce measurements from switches, routers, Wi-Fi access points and services. Operators need to determine whether degraded performance comes from **congestion, packet loss, latency spikes, interface faults, weak Wi-Fi signals, DHCP/DNS problems or device overload**. A dashboard that only says “red” is insufficient: an operator needs observed metrics, competing explanations, confidence/limitations and next steps.

**NetCoop AI** accepts telemetry as JSON, normalizes it, evaluates independent specialist findings, correlates their evidence, produces a structured diagnostic report, and offers guided investigation. The web frontend visualizes saved observations, inventory, incident history and manually mapped campus reference locations.

### Implemented vs. not implemented

| Capability | Current behavior |
| --- | --- |
| Five-role LangGraph diagnostic workflow | Implemented |
| Parallel Performance, Infrastructure and Connectivity analysis | Implemented |
| Root-cause correlation, bounded arbitration, structured report | Implemented |
| Optional Gemini specialist reviews, advisory second opinion and report review | Implemented; dependent on API access, quota and structured-output support |
| JSON single diagnosis and batch import | Implemented |
| Device inventory, incident command, evidence, timeline, history and trends | Implemented using saved observations |
| IIT Bhubaneswar 2D and tilted 3D map | Implemented using geographical reference points and OSM building footprints where mapped |
| Satellite basemap | Optional; requires an appropriate configured imagery provider |
| Physical router polling, real-time outage detection, verified fiber paths | **Not implemented** |
| Login, user isolation, persistent free-tier cloud SQLite | **Not implemented** |

## What the application includes

The **Next.js operations frontend** provides:

- **Command Center** — observed device count, latest healthy/diagnosed/review conditions, incident overview and embedded campus map.
- **Satellite Campus** — interactive reference regions and device inspection, with optional licensed satellite basemap.
- **3D Campus** — MapLibre tilted view with available OpenStreetMap footprints, labeled buildings, status markers, timeline playback and demo device-region assignments.
- **Device Inventory** — last saved observation per device, health/fault status and detail pages.
- **Incident Command / Agent Collaboration / Fault Courtroom** — evidence, diagnostic decisions, multi-agent messages and explanations.
- **Events & History** — stored observations, chronological review, per-device history and historical campus playback.
- **Network Experience / Adaptive Investigation** — operator-driven suggested checks and measured-value entry; missing measurements are not silently treated as zero.
- **Upload JSON / Diagnose / Technical Records / Configure** — ingestion, single diagnosis, trace inspection and technical details.

The repository also retains its **original Streamlit operator application** (app.py) and command-line runner (main.py). The Next.js frontend does not replace or modify those entry points.

## Five-agent architecture

~~~text
JSON observation / operator measurements
                |
     Normalize & validate keys, units, missing fields
                |
     LangGraph parallel specialist fan-out
        /              |               \
Performance Agent  Infrastructure    Connectivity Agent
 latency, loss,    Agent             RSSI, SNR, DHCP,
 jitter, queues    interface/CPU     DNS, network access
        \              |               /
        Structured ACP agent findings (Pydantic)
                         |
                 Correlation Agent
      compare evidence, select supported cause,
          optional bounded conflict arbitration
                         |
                  Reporting Agent
       canonical report + supported actions
                         |
        FastAPI / SQLite / dashboard / history
~~~

**Role details:**

1. **Performance Agent** evaluates utilization, round-trip latency, jitter, packet loss and queue drops.
2. **Infrastructure Agent** analyzes evidence such as CPU utilization, memory and interface/CRC errors when supplied.
3. **Connectivity Agent** examines wireless RSSI/SNR, retransmissions and DHCP/DNS indicators where available.
4. **Correlation Agent** compares hypotheses with measurement-specific evidence, resolves conflicts and can abstain where evidence is insufficient.
5. **Reporting Agent** creates the final structured diagnosis, evidence list, limitations and recommended actions.

Three specialists run in parallel; the graph joins their results before correlation. Inter-agent messages use validated Pydantic-based ACP-style envelopes. The root cause is **deterministic and evidence-grounded**: Gemini is an **optional advisory reviewer**, never the final authority.

**Result statuses:** diagnosed (supported fault), healthy (sufficient device-appropriate normal measurements), or inconclusive (missing/conflicting/insufficient evidence). The numeric confidence field describes **evidence support**, *not* an empirically calibrated probability of correctness.

## How telemetry JSON works

### A. Single diagnosis: minimal realistic example

Paste this **JSON object** in the Diagnose page, or send it under the telemetry key in the REST request below:

~~~json
{
  "timestamp": "2026-11-01T02:00:18Z",
  "device_id": "SW_CAMPUS_1",
  "site": "Demo Campus",
  "parent_id": "CORE_SWITCH_01",
  "metrics": {
    "cpu_utilization_pct": 61.71,
    "link_utilization_pct": 60.32,
    "packet_loss_pct": 1.2,
    "latency_ms": 204.07,
    "jitter_ms": 70.75,
    "queue_drops": 4
  },
  "status": "Warning"
}
~~~

- timestamp is an ISO-8601 observation time; batch import requires a timezone-aware timestamp.
- device_id identifies a logical monitored device; site and parent_id are supplied metadata, **not verified GIS/cable coordinates**.
- metrics contains observed numerical values. Aliases such as cpu_utilization_pct are normalized to canonical names such as cpu_pct.
- A top-level status such as Warning is an **untrusted external label**, not proof of a fault.
- Missing metrics remain missing; an absent value is **not** assumed to equal zero.
- This latency/jitter example supports a latency-spike diagnosis under the current deterministic rules; specific reports depend on the supplied data.

### B. REST JSON for POST /api/diagnose

~~~json
{
  "telemetry": {
    "timestamp": "2026-11-01T02:00:18Z",
    "device_id": "SW_CAMPUS_1",
    "site": "Demo Campus",
    "parent_id": "CORE_SWITCH_01",
    "metrics": {
      "cpu_utilization_pct": 61.71,
      "link_utilization_pct": 60.32,
      "packet_loss_pct": 1.2,
      "latency_ms": 204.07,
      "jitter_ms": 70.75,
      "queue_drops": 4
    }
  },
  "save": true,
  "include_trace": true
}
~~~

Example PowerShell request (locally running backend):

~~~powershell
$body = Get-Content .\single-diagnosis.json -Raw
Invoke-RestMethod -Method Post -Uri http://localhost:8000/api/diagnose -ContentType application/json -Body $body
~~~

Save the **wrapped** JSON from section B as single-diagnosis.json. Use save=false to avoid saving an incident; include_trace=true returns agent messages, optional agent_reviews, correlation detail, and optional report_review.

### C. Example response (illustrative, shortened)

~~~json
{
  "record_id": 1,
  "incident_id": "INC-EXAMPLE",
  "report": {
    "incident_id": "INC-EXAMPLE",
    "status": "diagnosed",
    "suspected_root_cause": "latency_spike",
    "confidence": 0.7136,
    "affected_devices": ["SW_CAMPUS_1"],
    "supporting_evidence": [
      {"metric": "latency_ms", "value": 204.07, "interpretation": "Round-trip time exceeds 150 ms"},
      {"metric": "jitter_ms", "value": 70.75, "interpretation": "Elevated latency variation"}
    ],
    "alternative_causes": [],
    "recommended_actions": [
      "Compare latency and jitter across the path",
      "Check congestion, queueing, and upstream latency",
      "Capture repeat measurements to determine whether the spike persists"
    ],
    "evidence_sources": ["performance_agent"],
    "limitations": []
  },
  "normalized_telemetry": {
    "device_id": "SW_CAMPUS_1",
    "latency_ms": 204.07,
    "jitter_ms": 70.75
  },
  "warnings": [],
  "agent_messages": [],
  "agent_reviews": [],
  "correlation": {},
  "report_review": null
}
~~~

**Important:** This is a condensed illustration, not a literal full response. The actual normalized_telemetry contains more keys (many null); agent_messages and correlation contain structured details when include_trace=true; real warnings/reviews and scores can differ. record_id is null if save=false. Gemini explanatory output, when available, is advisory and is returned separately or referenced in report limitations.

### D. Batch import JSON

The **Upload JSON** page accepts a JSON array of observation objects. Example:

~~~json
[
  {
    "timestamp": "2026-11-01T03:00:00Z",
    "device_id": "SW_DEMO_HEALTHY",
    "metrics": {
      "link_utilization_pct": 20,
      "latency_ms": 12,
      "packet_loss_pct": 0,
      "queue_drops": 0
    }
  },
  {
    "timestamp": "2026-11-01T03:01:00Z",
    "device_id": "AP_DEMO_WEAK",
    "metrics": {
      "rssi_dbm": -82,
      "snr_db": 9,
      "retransmissions_pct": 42
    }
  },
  {
    "timestamp": "2026-11-01T03:02:00Z",
    "device_id": "SW_DEMO_CONGESTED",
    "metrics": {
      "link_utilization_pct": 95,
      "latency_ms": 260,
      "packet_loss_pct": 11,
      "queue_drops": 180
    }
  }
]
~~~

For the REST API the same observations must be **wrapped**:

~~~json
{
  "records": [
    {"timestamp": "2026-11-01T03:00:00Z", "device_id": "SW_DEMO_HEALTHY", "metrics": {"link_utilization_pct": 20, "latency_ms": 12, "packet_loss_pct": 0, "queue_drops": 0}},
    {"timestamp": "2026-11-01T03:01:00Z", "device_id": "AP_DEMO_WEAK", "metrics": {"rssi_dbm": -82, "snr_db": 9, "retransmissions_pct": 42}}
  ]
}
~~~

Call POST /api/telemetry/import with Content-Type: application/json. The backend validates that each record has a device ID and timestamp, processes up to **500 records** per request, persists successful diagnoses, and returns count plus per-record results or errors. The endpoint can invoke Gemini once or several times *per record* depending on configuration: large batch uploads can exhaust provider quotas.

### E. How the analysis is generated

1. The API accepts telemetry, extracts top-level and nested metrics, resolves recognized aliases and units, and records warnings for missing or invalid fields.
2. The specialist agents independently inspect **only provided evidence** and produce findings via Pydantic message schemas.
3. Correlation selects a supportable cause, performs bounded arbitration where needed, or returns healthy/inconclusive when appropriate.
4. Reporting produces a canonical JSON report and next investigative steps.
5. If configured, Gemini generates separate constrained reviews/second opinions. A Gemini failure (rate limit, unavailable model, parsing error) **does not discard the deterministic result**.
6. With save=true or a batch import, the API writes an incident and agent messages to SQLite; other pages read the saved records.

### Input schema and normalization notes

Recognized metrics include link_utilization_pct, queue_drops, latency_ms, jitter_ms, packet_loss_pct, throughput_mbps, cpu_pct (alias cpu_utilization_pct), memory_pct, crc_errors, rssi_dbm, snr_db, retransmissions_pct, dns_latency_ms, dhcp_timeout_pct and gateway_ping_ms. Certain nested values and friendly aliases are accepted. Special metadata includes timestamp, device_id, site, parent_id and optional topology information.

A generic interface_errors measurement is **not** automatically equivalent to crc_errors. The system does not infer or manufacture missing hardware measurements.

**Built-in scenarios:** normal_operation, link_congestion, weak_wifi_signal, interface_fault, dhcp_dns_failure, malformed_and_missing_data. Retrieve examples with GET /api/scenarios or run them via the CLI.

## Run locally

Requirements: Python **3.11+** (Render is configured for **3.12.11**), Node.js/npm for the web frontend, and an optional Google Gemini API key. SQLite is created locally.

### Windows PowerShell

~~~powershell
git clone https://github.com/himani046/NetCoop-AI-.git
cd NetCoop-AI-
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[api,test,llm-gemini]"
python -m pytest -q
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
~~~

In another PowerShell terminal:

~~~powershell
cd NetCoop-AI-\frontend
npm install
Copy-Item .env.example .env.local
# Set NEXT_PUBLIC_API_URL=http://localhost:8000 in .env.local
npm run dev
~~~

Open http://localhost:3000 and http://localhost:8000/api/health.

### macOS / Linux

~~~bash
git clone https://github.com/himani046/NetCoop-AI-.git
cd NetCoop-AI-
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[api,test,llm-gemini]'
uvicorn api.main:app --reload --port 8000
# In another shell:
cd frontend
npm install
cp .env.example .env.local
npm run dev
~~~

Other entry points:

~~~bash
python main.py --scenario link_congestion
python main.py --scenario interface_fault --output incident.json
python main.py --batch data/colab_batch.json --db data/netcoop.db --output reports/batch.json
streamlit run app.py
~~~

## REST API reference

FastAPI serves JSON at http://localhost:8000 (locally), with interactive documentation at /docs.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | /api/health | Health and source/mode |
| GET | /api/scenarios | Example diagnostic observations |
| POST | /api/diagnose | Run one diagnosis; save and trace optional |
| POST | /api/telemetry/import | Batch process up to 500 timestamped observations |
| GET | /api/overview/summary | Dashboard counts |
| GET | /api/devices/latest | Latest saved record for each device |
| GET | /api/devices/{device_id} | Device detail and measurements |
| GET | /api/devices/{device_id}/history | Device observation timeline |
| GET | /api/devices/{device_id}/trends | Historical metric trends |
| GET | /api/incidents | Saved incident list |
| GET | /api/incidents/{record_id} | Full saved incident |
| GET | /api/incidents/{record_id}/messages | ACP agent messages |
| GET | /api/incidents/{record_id}/investigation | Investigative narrative |
| GET | /api/incidents/{record_id}/evidence | Evidence details |
| GET | /api/intelligence/incidents | Incident intelligence summary |
| GET | /api/playback/events | Chronological saved events |
| GET | /api/map/regions | Reference regions, statuses and assignments |
| GET | /api/map/history | Historical map frames |
| POST | /api/map/assign | Manually place/unplace a test device in a reference region |

**Example demo assignment body:** {"device_id":"SW_CAMPUS_1","region_id":null} removes an assignment. To assign a region, first retrieve its exact ID from GET /api/map/regions. These assignments reflect **demo placement**, not discovered real device coordinates.

## Gemini configuration and limitations

Gemini integration is optional. The Python package is installed by the Render Blueprint via pip install -e ".[api,llm-gemini]". To enable locally, create a root .env based on the **root .env.example**:

~~~dotenv
GEMINI_API_KEY=YOUR_PRIVATE_KEY
NETCOOP_LLM_MODEL=gemini-3.5-flash-lite
NETCOOP_GEMINI_AGENT_REVIEWS=1
NETCOOP_GEMINI_TIMEOUT_SECONDS=20
~~~

This model value is an example previously used in testing; use an exact currently available model ID for your Google project. **Do not commit .env, paste a secret into a frontend NEXT_PUBLIC_ variable, or store it in an uploaded JSON file.**

- NETCOOP_LLM_MODEL empty: no Gemini calls; deterministic five-agent workflow still works.
- NETCOOP_GEMINI_AGENT_REVIEWS=0: skips Gemini specialist and reporting reviews, **but may still call Gemini for a correlation advisory second opinion** if a model is configured.
- NETCOOP_GEMINI_AGENT_REVIEWS=1: can call Gemini for three specialist reviews, a correlation second opinion, and final-report review—**up to roughly five calls per incident**.
- Structured-output integration uses explicit native json_schema mode with Pydantic validation. Advisory labels include latency_spike and packet_loss.
- Missing metrics, invented references, conflicting identities and invalid outputs are rejected or flagged. Gemini **never changes the deterministic final cause**.
- Provider quotas, 429 rate limits, model availability, and parser errors can affect reviews. Avoid batch Gemini reviews on a low quota. Only a fresh, populated agent_reviews / report_review or advisory second-opinion response proves the relevant AI path worked.

For a cost-controlled demonstration, disable Gemini during large imports and run a single selected diagnosis with Gemini enabled. The public API currently has no user authentication or rate-limiting: do **not** expose a billable key on an unprotected production endpoint without adding safeguards.

## Campus maps and topology

**2D Satellite Campus** and **3D Campus** use MapLibre GL JS. The 3D view fetches mapped OSM building footprints via Overpass, extrudes polygons using recorded or estimated heights, displays available building names, and restricts navigation to an approximate IIT Bhubaneswar vicinity.

Device-region associations are manually selected from existing backend reference locations. A red region marker means an assigned device has a **saved diagnosed fault**; yellow signals review/limited evidence; green means an observed healthy condition; gray denotes unmonitored/unassigned. Markers are **not verified outage polygons**.

Where a saved device has a parent_id and both devices have assigned reference regions, the UI draws a logical connection. Red indicates a diagnosed endpoint fault, **not proven propagation** to every downstream building or the path of buried fiber.

**Satellite imagery is optional** and is not continuously live. The default no-credentials fallback is an OpenStreetMap street basemap. Configure one of these frontend settings in frontend/.env.local or the Render static-site environment:

~~~dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
# Optional Sentinel Hub WMS configuration (public browser-side instance ID)
NEXT_PUBLIC_SENTINEL_INSTANCE_ID=
NEXT_PUBLIC_SENTINEL_LAYER=NATURAL-COLOR
NEXT_PUBLIC_SENTINEL_WMS_BASE=copernicus
NEXT_PUBLIC_SENTINEL_TIME=
# OR an authorized MapTiler browser key / licensed MapLibre style
NEXT_PUBLIC_MAPTILER_KEY=
NEXT_PUBLIC_SATELLITE_STYLE_URL=
~~~

Sentinel-2 imagery is periodically acquired and typically too low-resolution for the crisp individual-building aerial photograph seen in some mockups. A provider license, suitable imagery resolution and API configuration are required for higher-resolution satellite/aerial imagery. **No satellite API can reveal router health without network telemetry.**

## Database, privacy and hosting

### Storage

The app uses **SQLAlchemy + SQLite** for saved incidents, messages and demo region assignments. Local default is data/netcoop.db, which persists as long as the file is retained.

The included root render.yaml defines:

- **netcoop-api**: FastAPI Python service, builds with Gemini extra, runs Uvicorn, uses Python 3.12.11.
- **netcoop-ui**: Next.js static export from frontend/out, with NEXT_PUBLIC_API_URL pointing to the API.
- **NETCOOP_DB_PATH=/tmp/netcoop.db** on the Render free backend.

**Render free-instance filesystem storage is ephemeral.** Database content can vanish when the backend spins down, restarts or redeploys. A successful re-upload can be lost later. This is **not age-based retention of individual incidents**. For reliable persistence, migrate to an external persistent database with appropriate backend support or use a persistent disk on a suitable paid service.

### Privacy and multi-user behavior

**There is no login, tenant_id, per-user ownership filtering, or authenticated authorization.** All visitors to the same API share the same saved database. One visitor's stored diagnoses can appear in another visitor's dashboard, inventory or incident history. **Do not upload confidential or actual campus operational telemetry to the public demo.** CORS is not an authentication mechanism.

The root code currently exposes unauthenticated diagnosis, telemetry import and demo mapping assignment. Add authentication, per-user ownership enforcement, rate limits, secure ingestion and durable hosting before real-world use.

### Render environment variables

Backend netcoop-api:

~~~dotenv
PYTHON_VERSION=3.12.11
NETCOOP_DB_PATH=/tmp/netcoop.db
NETCOOP_CORS_ORIGINS=https://netcoop-ui.onrender.com
GEMINI_API_KEY=YOUR_SECRET_IN_RENDER_ONLY
NETCOOP_LLM_MODEL=
NETCOOP_GEMINI_AGENT_REVIEWS=0
NETCOOP_GEMINI_TIMEOUT_SECONDS=20
~~~

The model is intentionally blank and agent reviews off in this safe example. Set the model explicitly **only when you intend Gemini usage**. Frontend netcoop-ui:

~~~dotenv
NEXT_PUBLIC_API_URL=https://netcoop-api.onrender.com
# Optional imagery settings from the preceding section
~~~

Actual service URLs may differ. Render Blueprint may apply its own configured defaults; confirm the service Environment tab and redeploy after changes. Next.js static environment variables are injected **at build time**, so a new frontend build is needed after editing them.

### Production-readiness gaps

This is a functional hackathon prototype, not a secure enterprise monitoring service. No verified campus device polling or authorized production telemetry collector exists. The system has not established independent real-world confidence calibration, durable multi-user storage, authentication, or physical network topology. Dependency audit warnings must be reviewed before production use.

## Testing and 5-minute demo

~~~bash
python -m pytest -q
python -m pytest tests/test_gemini_agents.py tests/test_ai_reasoning.py -v
python benchmark.py --per-class 20 --seed 42 --output reports/benchmark.json
cd frontend
npm run lint
npm run build
~~~

Mocked Gemini tests do not consume API quota; they do not prove a live Google project has remaining requests. The benchmark uses seeded synthetic data and reports accuracy, class scores and abstentions **for those synthetic fixtures only**, not independently validated campus performance.

**Suggested five-minute walkthrough:**

| Time | Show | Narration |
| --- | --- | --- |
| 0:00–0:35 | Command Center | Campus network troubleshooting problem and project objective |
| 0:35–1:20 | Agent Collaboration | Three specialists in parallel; Correlation then Reporting; optional Gemini advice |
| 1:20–2:05 | Upload JSON / Diagnose | Demonstrate a single telemetry record becoming an evidence-based fault report |
| 2:05–2:50 | Satellite + 3D Campus | Color-coded demo reference regions and mapped building footprints |
| 2:50–3:35 | Device Inventory + Incidents | Trace source measurements and past observations |
| 3:35–4:20 | Fault Courtroom + Network Experience | Explain confidence, limitations and operator-suggested measurements |
| 4:20–5:00 | Architecture + closing | Distinguish implemented prototype from live network monitoring roadmap |

**Closing:** *NetCoop AI doesn't just flag a network anomaly—it helps operators understand which evidence supports a diagnosis, what remains unknown, and what to investigate next.*

## Project layout and roadmap

~~~text
app.py                 Original Streamlit console
main.py                CLI and batch processing
api/                   FastAPI routes, campus mapping, history, intelligence
src/agents/            Performance, Infrastructure, Connectivity, Correlation, Reporting, Gemini reviews
src/graph/             LangGraph workflow and state
src/protocol/          Normalization, validation and ACP/Pydantic contracts
src/database/          SQLAlchemy/SQLite models and incident repository
src/utils/             Synthetic scenarios, confidence, calibration
frontend/              Next.js dashboard, MapLibre maps and static export
tests/                 Python regression and mocked integration tests
benchmark.py           Seeded synthetic benchmark
render.yaml            Render backend + static frontend Blueprint
~~~

**Next steps:** authenticated per-user workspaces; persistent database; rate-limited/on-demand Gemini reviews; approved SNMP/syslog/telemetry ingestion; validated topology and device-to-building geolocation; richer campus coverage and licensed high-resolution imagery; stronger operational/security testing.

For implementation-specific details, see [frontend/README.md](frontend/README.md) and [src/database/README.md](src/database/README.md).

---

**NetCoop AI is a synthetic/test telemetry demonstration. A red map marker is a saved diagnostic inference, not an independently verified live IIT Bhubaneswar outage.**
