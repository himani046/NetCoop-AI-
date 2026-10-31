# NetCoop AI — Five-Agent LangGraph Network Diagnosis

The full runnable source archive was generated and delivered as **netcoop-ai.zip** in the ChatGPT conversation. Extract that archive to obtain the complete modular project.

## Local setup
```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m pytest -q
python main.py --scenario link_congestion
streamlit run app.py
```

## Architecture
Five functional roles: Performance, Infrastructure, Connectivity, Fault Correlation/Arbitration, Reporting. LangGraph executes three diagnostic agents in parallel, joins findings at a barrier, optionally arbitrates, and returns JSON plus an incident Markdown report.

## Synthetic telemetry
Run the organizer's Colab generator, export a single row to JSON, then invoke `python main.py --file telemetry.json`. Field aliases and units are normalized with warnings; diagnostic uncertainty is reported explicitly.

> This is the initial repository setup document. The modular code is supplied separately in the downloadable source archive; it has **not** been synchronized into individual GitHub files yet.
