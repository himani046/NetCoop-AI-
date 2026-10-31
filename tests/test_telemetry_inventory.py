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

def test_partial_normal_observation_is_described_without_false_healthy_claim():
    from src.database.telemetry_inventory import describe_observation
    label,detail=describe_observation("inconclusive",{"latency_ms":12,"cpu_pct":25})
    assert label=="NO FAULT DETECTED · LIMITED DATA"
    assert "unavailable" in detail
    assert describe_observation("inconclusive",{})[0]=="INSUFFICIENT DATA"

def test_previous_wifi_fault_not_verified_cleared(tmp_path,monkeypatch):
    monkeypatch.delenv("NETCOOP_LLM_MODEL",raising=False)
    db=tmp_path/"wifi_history.db"
    earlier={"device_id":"AP1","timestamp":"2026-10-31T10:00:00Z",
             "rssi_dbm":-86,"snr_db":8,"retransmissions_pct":42}
    later={"device_id":"AP1","timestamp":"2026-10-31T11:00:00Z",
           "cpu_pct":25,"latency_ms":15,"packet_loss_pct":0}
    for i,record in enumerate((earlier,later)):
        state=diagnose(record,incident_id=f"INC-WIFI-{i}")
        with session_factory(db)() as session:save_incident(session,record,state)
    with session_factory(db)() as session:current=latest_device_records(session)[0]
    assert current["status"]=="inconclusive"
    assert current["previous_fault"]=="weak_wifi_signal"
    assert current["display_status"]=="PREVIOUS FAULT · NOT VERIFIED CLEARED"

def test_metric_interpretation_color_and_missing_values():
    from src.database.telemetry_inventory import metric_interpretation
    assert metric_interpretation("link_utilization_pct", 35)[0] == "green"
    assert metric_interpretation("link_utilization_pct", 80)[0] == "yellow"
    assert metric_interpretation("link_utilization_pct", 94)[0] == "red"
    assert metric_interpretation("rssi_dbm", -86)[0] == "red"
    assert metric_interpretation("rssi_dbm", -72)[0] == "yellow"
    assert metric_interpretation("rssi_dbm", -53)[0] == "green"
    assert metric_interpretation("crc_errors", 12450)[0] == "red"
    assert metric_interpretation("dhcp_timeout_pct", 50)[0] == "red"
    assert metric_interpretation("cpu_pct", None)[0] == "gray"
    assert metric_interpretation("throughput_mbps", 120)[0] == "gray"

def test_latest_device_metric_detail_uses_correct_record(tmp_path, monkeypatch):
    from src.database.telemetry_inventory import latest_device_metrics
    monkeypatch.delenv("NETCOOP_LLM_MODEL", raising=False)
    db = tmp_path / "metric-details.db"
    readings = [
        {"device_id":"SW-METRICS","timestamp":"2026-10-31T12:00:00Z",
         "link_utilization_pct":94,"latency_ms":280,"queue_drops":160},
        {"device_id":"SW-METRICS","timestamp":"2026-10-31T11:00:00Z",
         "link_utilization_pct":35,"latency_ms":20,"queue_drops":0},
    ]
    for i, raw in enumerate(readings):
        with session_factory(db)() as session:
            save_incident(session, raw, diagnose(raw, incident_id=f"INC-METRICS-{i}"))
    with session_factory(db)() as session:
        current = latest_device_records(session)[0]
        detail = {row["metric"]:row for row in latest_device_metrics(session, current["record_id"])}
    assert detail["link_utilization_pct"]["value"] == 94
    assert detail["link_utilization_pct"]["level"] == "red"
    assert detail["crc_errors"]["level"] == "gray"
