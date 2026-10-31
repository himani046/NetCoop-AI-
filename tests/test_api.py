"""FastAPI adapter smoke tests. Existing Streamlit code is not involved."""
import os
import pytest
from fastapi.testclient import TestClient
import api.main as api

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "DATABASE", str(tmp_path/"api.db"))
    monkeypatch.setenv("NETCOOP_LLM_MODEL", "")
    with TestClient(api.app) as client:
        yield client

def test_health_and_empty_inventory(client):
    res=client.get("/api/health")
    assert res.status_code==200
    assert res.json()["live_monitoring"] is False
    assert client.get("/api/overview/summary").json()["devices"]==0
    assert client.get("/api/devices/latest").json()==[]

def test_diagnosis_persists_and_reuses_existing_agent_workflow(client):
    raw={"device_id":"SW-TEST","timestamp":"2026-10-31T10:00:00Z",
         "link_utilization_pct":94,"latency_ms":280,
         "packet_loss_pct":12,"queue_drops":160}
    result=client.post("/api/diagnose",json={"telemetry":raw})
    assert result.status_code==200, result.text
    data=result.json()
    assert data["report"]["suspected_root_cause"]=="link_congestion"
    assert len(data["agent_messages"])==5
    device=client.get("/api/devices/SW-TEST")
    assert device.status_code==200
    assert device.json()["device"]["status"]=="diagnosed"
    assert len(device.json()["metrics"])==15
    record=client.get("/api/incidents/"+str(data["record_id"]))
    assert record.json()["raw_telemetry"]==raw
    assert len(record.json()["messages"])==5

def test_bulk_import_is_timestamp_aware(client):
    observations=[
      {"device_id":"AP1","timestamp":"2026-10-31T11:00:00Z",
       "rssi_dbm":-85,"snr_db":7,"retransmissions_pct":40},
      {"device_id":"AP1","timestamp":"2026-10-31T10:00:00Z",
       "rssi_dbm":-52,"snr_db":30,"retransmissions_pct":1},
      {"device_id":"SW2","timestamp":"2026-10-31T10:00:00Z","latency_ms":20},
    ]
    res=client.post("/api/telemetry/import",json={"records":observations})
    assert res.status_code==200,res.text
    assert res.json()["count"]==3
    latest={x["device_id"]:x for x in client.get("/api/devices/latest").json()}
    assert len(latest)==2
    assert latest["AP1"]["timestamp"]=="2026-10-31T11:00:00+00:00"
    assert latest["AP1"]["root_cause"]=="weak_wifi_signal"
    assert len(client.get("/api/devices/AP1/history").json())==2

def test_import_rejects_missing_device_or_timestamp(client):
    response=client.post("/api/telemetry/import",json={"records":[{"latency_ms":5}]})
    assert response.status_code==422
    assert client.get("/api/devices/latest").json()==[]
