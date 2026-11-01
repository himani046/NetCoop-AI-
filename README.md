# NetCoop AI — Multi-Agent Network Fault Diagnosis

Runnable five-role network diagnosis system built with LangGraph, LangChain and Pydantic v2. Three specialist agents run in parallel; the correlation agent resolves cross-agent evidence; the reporting agent emits structured JSON and a Markdown incident report.

## Quick start (Python 3.11+)

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
python main.py --scenario link_congestion
streamlit run app.py
```

On Windows activate with `.venv\Scripts\activate`.

## Six benchmark scenarios

`normal_operation`, `link_congestion`, `weak_wifi_signal`, `interface_fault`, `dhcp_dns_failure`, `malformed_and_missing_data`.

```bash
python main.py --scenario interface_fault --output incident.json
python main.py --file colab_sample.json
```

## Colab dataset

Here are some test cases if you see 0 in the dashsboard Please go to upload Tab https://netcoop-ui.onrender.com/import and paste these test cases and run 

[
  {
    "timestamp": "2026-11-01T01:18:34.242285Z",
    "device_id": "SW_CAMPUS_4",
    "metrics": {
      "cpu_utilization_pct": 19.15,
      "link_utilization_pct": 23.07,
      "packet_loss_pct": 0.0,
      "latency_ms": 10.05,
      "jitter_ms": 2.0,
      "queue_drops": 0
    }
  },
  {
    "timestamp": "2026-11-01T01:18:34.242325Z",
    "device_id": "SW_CAMPUS_7",
    "metrics": {
      "cpu_utilization_pct": 47.07,
      "link_utilization_pct": 62.32,
      "packet_loss_pct": 1.07,
      "latency_ms": 367.66,
      "jitter_ms": 40.21,
      "queue_drops": 47
    }
  },
  {
    "timestamp": "2026-11-01T01:18:34.242340Z",
    "device_id": "SW_CAMPUS_5",
    "metrics": {
      "cpu_utilization_pct": 99.9,
      "link_utilization_pct": 100.0,
      "packet_loss_pct": 25.92,
      "latency_ms": 764.66,
      "queue_drops": 12219,
      "interface_errors": 409
    }
  },
  {
    "timestamp": "2026-11-01T01:18:34.242351Z",
    "device_id": "SW_CAMPUS_3",
    "metrics": {
      "cpu_utilization_pct": 57.46,
      "link_utilization_pct": 40.89,
      "packet_loss_pct": 12.39,
      "latency_ms": 237.87,
      "jitter_ms": 46.84,
      "interface_errors": 55
    }
  },
  {
    "timestamp": "2026-11-01T01:18:34.242361Z",
    "device_id": "SW_CAMPUS_7",
    "metrics": {
      "cpu_utilization_pct": 78.98,
      "link_utilization_pct": 94.51,
      "packet_loss_pct": 2.95,
      "latency_ms": 230.89,
      "jitter_ms": 30.17,
      "queue_drops": 322
    }
  },
  {
    "timestamp": "2026-11-01T01:18:34.242370Z",
    "device_id": "HOSTEL_AP_3",
    "metrics": {
      "rssi_dbm": -78,
      "snr_db": 12,
      "retransmissions_pct": 53,
      "channel_utilization_pct": 90
    }
  }
]

Run the hackathon's synthetic telemetry generator, export an individual observation as a JSON object and pass it to `--file`. For example, if Colab exposes a pandas DataFrame named `df`:

```python
import json
from google.colab import files
row = df.iloc[0].where(df.iloc[0].notna(), None).to_dict()
with open("colab_sample.json", "w") as f:
    json.dump(row, f, default=str, indent=2)
files.download("colab_sample.json")
```

Check the actual notebook column names before use; the notebook contents were not accessible for schema verification. The normalizer accepts aliases for latency, utilization, queue drops, CPU, Wi-Fi, DNS and DHCP data. It converts units and reports missing fields.

## Architecture

```text
Telemetry JSON
    |
Normalize + validate
    |
    +--> Performance Agent ---+
    +--> Infrastructure Agent +--> Correlation Agent --> [Arbitration when necessary] --> Reporting Agent
    +--> Connectivity Agent --+
```

The protocol `src/protocol/models.py` defines immutable ACP v1.2.0 Pydantic messages, agent findings and report schemas. LangGraph controls the barrier join and optional bounded arbitration. No agent should claim an exact root cause from insufficient telemetry.

### Topology

Supply `topology: {"nodes":[{"id":"AP1","parent_id":"SW1","role":"ap","site":"Hostel"},...]}` plus `affected_device_ids` to evaluate a shared ancestor and blast radius. Unknown nodes and cycles produce warnings.

### Confidence

The report's `confidence` is an evidence support score, not a calibrated probability. For empirical calibration, fit `src/utils/calibration.fit_bins` using **independently labeled incidents**, serialize the resulting model as JSON, and set `NETCOOP_CALIBRATION_FILE`. The system abstains from returning a calibrated probability when a bin contains fewer than 20 labels. Synthetic fixture labels do not establish real-world calibration.

### Optional LLM second opinion

```bash
python -m pip install -e '.[test,llm-gemini]'
export GEMINI_API_KEY="your-key"
export NETCOOP_LLM_MODEL="gemini-2.5-flash"
```

An LLM is advisory: it can provide structured alternatives and explanations during arbitration/inconclusive cases, but cannot override deterministic findings. No API key is needed for the rule-based workflow.

## Acceptance and limitations

- Five functional diagnostic roles; three concurrent specialist agents.
- Cross-agent structured evidence, confidence scoring and conflict resolution.
- Malformed input handling and reproducible fixtures.
- Streamlit UI with downloadable JSON and post-mortem.
- Automatic tests using `pytest` and GitHub Actions.

**Not yet production-validated:** Real telemetry counter rates, empirical confidence calibration, LLM provider behavior, and security of ingestion pipelines require more work. No production campus configuration is modified. This implementation is a hackathon prototype.

## Demo (3–5 minutes)

1. Run link congestion to show utilization, queue drops and latency agreement.
2. Run interface fault to show CRC evidence winning over latency-only suspicion.
3. Run malformed input to expose normalization warnings.
4. Show agent messages, arbitration path and final JSON in Streamlit.

## Organizer Colab JSON (nested or flat)

The application accepts the original Colab shape directly, without a manual conversion step:

```json
{
  "timestamp": "2026-10-31T16:21:56.896760Z",
  "device_id": "SW_CAMPUS_8",
  "metrics": {
    "cpu_utilization_pct": 99.9,
    "link_utilization_pct": 100.0,
    "packet_loss_pct": 16.4,
    "latency_ms": 635.46,
    "queue_drops": 10730,
    "interface_errors": 160
  },
  "status": "Critical"
}
```

Save the object to `network_telemetry.json`, then run:

```bash
python main.py --file data/colab_original_nested.json
python main.py --file data/colab_sample.json
python -m pytest tests/test_colab_input.py -v
```

For Colab's generated Python variable `telemetry`, export without retyping values:

```python
import json
from google.colab import files
with open("network_telemetry.json", "w", encoding="utf-8") as f:
    json.dump(telemetry, f, indent=2, default=str)
files.download("network_telemetry.json")
```

If the notebook uses another variable name, replace `telemetry` with that variable. The top-level values override nested measurements with the same key, and generic `interface_errors` are **not** automatically classified as CRC faults. Input `status` is treated as an external label rather than diagnostic evidence.

## Batch telemetry diagnosis

Batch CLI accepts a JSON array, an object containing a `records` array, CSV, or JSON Lines. Each record is processed by the original five-role LangGraph workflow. Individual input errors are recorded without discarding other results.

```bash
python main.py --batch data/colab_batch.json --output reports/batch_results.json
python -m pytest tests/test_batch.py -v
```

The output contains summary counts, per-incident reports, validation warnings, and agent message histories. Use `--db data/netcoop.db` to persist runs to SQLite. The sample batch is an illustrative set of three cases rather than a collection exported from your Colab notebook.

## SQLite persistence and incident history

NetCoop AI stores completed workflow runs without changing the five-agent LangGraph architecture. The local SQLite database is initialized automatically when persistence is enabled.

```bash
python -m pip install -e '.[test]'
python main.py --batch data/colab_batch.json --db data/netcoop.db --output reports/latest.json
python main.py --history --db data/netcoop.db
python main.py --show-incident 1 --db data/netcoop.db
python -m pytest tests/test_database.py -v
streamlit run app.py
```

The dashboard supports saving diagnoses and browsing stored reports with agent-message history. Each execution has a unique internal database ID, even if external incident IDs repeat. Files ending in `.db` are intentionally excluded from Git. See `src/database/README.md` for the schema and limitations. SQLite is a local demonstration store, not an operational campus network monitoring service.

## Evidence-grounded AI advisory review (optional)

Install the provider integration and set an API key locally. The core five-agent system and all tests continue to work without a key.

```bash
python -m pip install -e '.[test,llm-gemini]'
export GEMINI_API_KEY="YOUR_KEY_FROM_PROVIDER"
export NETCOOP_LLM_MODEL="gemini-2.5-flash"
python main.py --scenario link_congestion
streamlit run app.py
```

Do not commit credentials. AI reviews are advisory Pydantic-validated structured outputs with suggested cause, explanation, alternative causes, an uncertainty flag and referenced metric names. Reviews cannot override the deterministic diagnosis or its evidence-support score. Invalid or unavailable API responses gracefully fall back to the normal result. The required final JSON retains its original hackathon schema; the review appears separately in the LangGraph diagnostic state, arbitration notes and Streamlit dashboard.

With the model configured, a review runs after correlation for ordinary cases and after bounded arbitration for conflicting cases. Without configuration, diagnostics remain offline and deterministic. Mocked tests in `tests/test_ai_reasoning.py` exercise success, disagreement and failure without contacting a provider.

**Caution:** The mock tests do not prove a live API model integration. Verify provider credentials, model availability, latency and billing before the demonstration.

## Offline diagnostic benchmark (no API key)

```bash
python benchmark.py --per-class 20 --seed 42 --output reports/benchmark.json
python -m pytest tests/test_benchmark.py -v
```

The script creates 120 seeded synthetic evaluations: 20 instances each of normal operation, link congestion, weak Wi-Fi, physical interface fault, DHCP fault and deliberately insufficient telemetry. It executes the existing five-agent LangGraph diagnosis without activating the optional LLM. It reports overall accuracy, macro F1, per-class precision/recall/F1, a confusion matrix, abstention rate, average and approximate p95 latency, and individual failure cases. The JSON report is reusable by demos or dashboards.

**Interpretation:** Labels are assigned by the generator from known fault templates with small noise; this measures reproducibility and performance *on synthetic fixtures*, not verified performance on independently labeled real campus incidents. An inconclusive result on a known normal record is scored as normal only if the specialist agents raise no fault hypotheses; this is a benchmark scoring convention. Run results are not predetermined and should never be advertised before executing the benchmark.

## Private API key setup via .env

The repo contains a safe `.env.example` template. Your real `.env` is already Git-ignored; **never push credentials**.

In Windows PowerShell, run from the cloned project folder:

```powershell
Copy-Item .env.example .env
notepad .env
python -m pip install -e ".[test,llm-gemini]"
python -m streamlit run app.py
```

Replace `replace_with_your_gemini_api_key` with your own key inside the local `.env`. The app loads it automatically through `python-dotenv`. Environment variables you set explicitly in the terminal take precedence. Do not use `git add -f .env`.

To confirm Git excludes the key file, run `git check-ignore .env`. It should print `.env`.

## Gemini-powered five-role workflow

**Provider:** Google Gemini Developer API via `langchain-google-genai`. Obtain a key from https://aistudio.google.com/apikey .

```powershell
git pull origin main
python -m pip install -e ".[test,llm-gemini]"
Copy-Item .env.example .env
notepad .env
python -m pytest -v
python -m streamlit run app.py
```

In your **local** `.env` file, configure:

```dotenv
GEMINI_API_KEY=your_private_google_ai_studio_key
NETCOOP_LLM_MODEL=gemini-2.5-flash
NETCOOP_GEMINI_AGENT_REVIEWS=1
```

The Performance, Infrastructure, and Connectivity agents run their established deterministic specialist analysis and optionally request **separate Gemini reviews**. Correlation requests a structured Gemini second opinion, and Reporting requests a Gemini operator summary. Gemini explanations never replace validated ACP findings, the deterministic root cause, evidence, confidence or canonical JSON. The UI presents the advisory reviews independently. Expect up to **five Gemini requests per incident**, which may consume quota and incur charges.

To reduce calls, set `NETCOOP_GEMINI_AGENT_REVIEWS=0` to skip specialist and reporting reviews; Correlation will still use Gemini. To run completely offline, leave `NETCOOP_LLM_MODEL` empty. The included benchmark forcibly disables Gemini, so measurements remain reproducible. Google API failures do not prevent the deterministic diagnosis.

**Before updating your existing local environment:** If you already created `.env` for OpenAI, edit that file manually, delete the OpenAI settings and add the Gemini settings above. `Copy-Item` must not overwrite a file containing secrets without checking it. Never commit `.env`; `git check-ignore .env` should confirm exclusion.

```powershell
python -m pytest tests/test_gemini_agents.py tests/test_ai_reasoning.py -v
```

The tests mock provider calls. They do not establish that a live Gemini API key has sufficient credits or requests per minute. Start the live demo with **one** incident before batch processing.

## Healthy outcomes and Gemini review validation

The final report has three explicit statuses: `diagnosed` for evidence-backed faults, `healthy` for complete normal snapshots where all three specialists report healthy, and `inconclusive` for insufficient or unreliable data. Healthy results do **not** imply a network-wide uptime guarantee; they describe only the observed snapshot. The `confidence` field remains the *fault-evidence support score*, so a healthy snapshot has a score of 0.

Gemini's alternative hypotheses stay in a separate `decision.ai_review` and cannot enter the canonical incident JSON without deterministic corroboration. Specialist reviews validate metric references and assign their identity from the calling agent; model-supplied conflicting identities and invented metrics are rejected. Validation warnings now include a short reason, without printing a configured API key.

Run targeted regression tests:

```powershell
git pull origin main
python -m pytest tests/test_health_and_reviews.py tests/test_scenarios.py tests/test_gemini_agents.py -v
python -m pytest -v
python -m streamlit run app.py
```

## Operator console (Streamlit)

The interface is now organized into four functional workspaces instead of displaying raw JSON on its primary pages:

- **Overview** — latest operator diagnosis, key metrics, evidence, actions and saved incident history.
- **Run diagnosis** — choose a built-in scenario or paste custom telemetry; run all five agents and review the readable results, including ACP collaboration and optional Gemini explanations.
- **Campus map** — an interactive geographic basemap of IIT Bhubaneswar's Argul permanent campus, with reference point-of-interest labels. **It does not monitor actual campus network infrastructure.** The user can explicitly map a *simulated incident device* to a known campus location for the demonstration; the selected place then receives a red warning marker when the synthetic diagnosis is `diagnosed`. Locations are not automatically inferred from device names and the demo mapping must not be represented as real network topology or a live alert.
- **Technical records** — raw final-report JSON, normalized telemetry, ACP envelopes, correlation data, Gemini review objects and saved incident JSON.

Run `python -m streamlit run app.py`. A working internet connection is needed for remote basemap tiles; the diagnosis engine itself operates with synthetic/local telemetry. The map references OpenStreetMap-based campus POI coordinates:
- IIT Bhubaneswar campus: https://mapcarta.com/W621537202
- Main Building: https://mapcarta.com/W1302319387
- Lalitgiri Lecture Hall: https://mapcarta.com/W1302319392
- Pushpagiri Lecture Hall: https://mapcarta.com/W1302319393
- Lab Complex: https://mapcarta.com/W1329357338
- IIT SHSSM: https://mapcarta.com/W1302319395

A true live campus network map requires authorized telemetry sources, audited device-to-location assignments, and validated link topology. The supplied hackathon problem statement explicitly permits synthetic telemetry and does not require production network access.

## Device telemetry import and latest-status inventory

Use **Import telemetry** in the sidebar to paste an individual JSON object, a JSON array of readings, an object with `records` / `telemetry` list, or JSONL, or upload a .json/.jsonl/.txt file. No scenario selection is necessary. An import can contain multiple device IDs and multiple observations for one device. Each record is independently normalized, diagnosed by the five functional agents, and persisted in SQLite with its full original and normalized telemetry, incident report, and agent-message history. Bulk imports default to deterministic offline analysis to prevent excessive Gemini API calls; optional Gemini reviews can be enabled.

For the **Campus map** device inventory, records are grouped by `device_id` and the latest valid **telemetry observation timestamp in UTC** is chosen, not the insertion time or the last processed record. Older uploads do not replace newer measurements. For equal timestamps, the most recently saved record takes precedence. Legacy records missing a parseable timestamp remain in history but are secondary to timestamped observations.

Imports require a nonempty known device ID and a timezone-aware ISO 8601 timestamp. Invalid imports are rejected before processing the batch; run failures during processing are listed per record. This is a test-data device dashboard, not a production campus monitoring feed. Map red/amber/green indicators are based on each mapped device's latest persisted result; building-to-device associations must be manually specified for demonstration, and are not verified network topology.

Run the tests with `python -m pytest tests/test_telemetry_inventory.py -v`.

### Per-device metric inspection on Campus map

Below **Latest telemetry by device ID**, expand **Device metrics & interpretations** for a device to review all 15 supported numeric fields from exactly the same latest-timestamp record used by the inventory. Metrics are grouped by Performance, Infrastructure, and Connectivity, showing observed values, units, and color-coded explanations: green normal, amber approaching a specialist anomaly threshold, red triggering a threshold, and grey missing/not assessed (including throughput where no capacity baseline is available). The amber thresholds are conservative display-only early warnings; red thresholds reflect the corresponding deterministic specialist checks. Missing metrics are never treated as normal. No real campus device status is implied by this synthetic telemetry UI.
