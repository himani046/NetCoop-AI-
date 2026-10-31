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
