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
python -m pip install -e '.[test,llm-openai]'
export OPENAI_API_KEY="your-key"
export NETCOOP_LLM_MODEL="openai:gpt-4o-mini"
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

The output contains summary counts, per-incident reports, validation warnings, and agent message histories. This is file-based batch processing; SQLite persistence is **not yet implemented**. The sample batch is an illustrative set of three cases rather than a collection exported from your Colab notebook.

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
python -m pip install -e '.[test,llm-openai]'
export OPENAI_API_KEY="YOUR_KEY_FROM_PROVIDER"
export NETCOOP_LLM_MODEL="openai:gpt-5-mini"
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
python -m pip install -e ".[test,llm-openai]"
python -m streamlit run app.py
```

Replace `replace_with_your_openai_api_key` with your own key inside the local `.env`. The app loads it automatically through `python-dotenv`. Environment variables you set explicitly in the terminal take precedence. Do not use `git add -f .env`.

To confirm Git excludes the key file, run `git check-ignore .env`. It should print `.env`.
