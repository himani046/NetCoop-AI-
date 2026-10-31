# NetCoop SQLite persistence

This folder implements storage for the *existing* five-agent LangGraph workflow. SQLite captures completed executions, without replacing agent-to-agent ACP messaging or the final report schema.

The schema has three tables:

- `devices`: device identity, site and upstream identifier
- `incidents`: each execution, raw and normalized telemetry, final report, warnings and Markdown
- `agent_messages`: sender, recipient, ordered complete message JSON, linked to incident rows

All incident/message writes take place in one transaction. Multiple runs may reuse the same external incident ID and remain individually addressable by database primary key.

## Example

```bash
python main.py --batch data/colab_batch.json --db data/netcoop.db --output reports/latest.json
python main.py --history --db data/netcoop.db
python main.py --show-incident 1 --db data/netcoop.db
```

Local SQLite files are ignored by Git. The database is optional: CLI workflows without `--db` continue to work.

SQLite is suitable for a local hackathon demo, not a shared multi-host production ingestion service. Database encryption, migrations, access controls, archival and retention policies remain future work.
