"""Bulk JSON inputs and per-device latest observation selection."""
from datetime import datetime
import json
import pytest
from src.database.telemetry_inventory import parse_telemetry_batch, latest_device_records
from src.database.session import session_factory
from src.database.repository import save_incident
from src.graph.workflow import diagnose

def test_input_shapes():
    item={"device_id":"SW1","timestamp":"2026-10-31T10:00:00Z"}
    assert parse_telemetry_batch(json.dumps(item)) == [item]
    assert parse_telemetry_batch(json.dumps([item,item])) == [item,item]
    assert parse_telemetry_batch(json.dumps({"records":[item]})) == [item]
    assert parse_telemetry_batch(json.dumps(item)+"\n"+json.dumps(item)) == [item,item]

def test_non_object_and_excess_rejected():
    with pytest.raises(ValueError):parse_telemetry_batch('[1,2]')
    with pytest.raises(ValueError):parse_telemetry_batch('[]')
    with pytest.raises(ValueError):parse_telemetry_batch('['+','.join(['{}']*501)+']')

def test_latest_selected_by_observation_not_import_order(tmp_path,monkeypatch):
    monkeypatch.delenv("NETCOOP_LLM_MODEL",raising=False)
    db=tmp_path/"inventory.db"
    values=[
        {"device_id":"SW1","timestamp":"2026-10-31T12:00:00Z","link_utilization_pct":94,"latency_ms":280,"queue_drops":160},
        {"device_id":"SW2","timestamp":"2026-10-31T10:00:00Z","latency_ms":24},
        {"device_id":"SW1","timestamp":"2026-10-31T11:00:00Z","link_utilization_pct":35,"latency_ms":24,"queue_drops":0},
        {"device_id":"SW1","link_utilization_pct":35,"latency_ms":24,"queue_drops":0},
    ]
    for i,raw in enumerate(values):
        state=diagnose(raw,incident_id=f"INC-TEST-{i}")
        with session_factory(db)() as session:
            save_incident(session,raw,state)
    with session_factory(db)() as session:
        rows=latest_device_records(session)
    assert [r["device_id"] for r in rows] == ["SW1","SW2"]
    assert rows[0]["timestamp"]=="2026-10-31T12:00:00+00:00"
    assert rows[0]["status"]=="diagnosed"
    assert rows[0]["root_cause"]=="link_congestion"
    assert rows[1]["device_id"]=="SW2"
