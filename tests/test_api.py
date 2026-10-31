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

def test_demo_campus_assignment_and_latest_state(client):
    reading={"device_id":"SW-CAMPUS","timestamp":"2026-10-31T10:00:00Z",
             "link_utilization_pct":94,"latency_ms":280,"queue_drops":160,"packet_loss_pct":12}
    assert client.post("/api/diagnose",json={"telemetry":reading}).status_code==200
    initial=client.get("/api/map/regions").json()
    assert initial["live"] is False
    assert all(r["status"]=="unmonitored" for r in initial["regions"])
    assert client.post("/api/map/assign",json={"device_id":"SW-CAMPUS","region_id":"labs"}).status_code==200
    state=client.get("/api/map/regions").json()
    labs=next(r for r in state["regions"] if r["id"]=="labs")
    assert labs["status"]=="fault"
    assert labs["devices"][0]["device_id"]=="SW-CAMPUS"
    assert client.post("/api/map/assign",json={"device_id":"SW-CAMPUS","region_id":"invalid"}).status_code==422
    assert client.post("/api/map/assign",json={"device_id":"NONEXISTENT","region_id":"labs"}).status_code==404
    assert client.post("/api/map/assign",json={"device_id":"SW-CAMPUS","region_id":None}).status_code==200
    cleared=client.get("/api/map/regions").json()
    assert next(r for r in cleared["regions"] if r["id"]=="labs")["status"]=="unmonitored"

def test_phase3_playback_sorting_and_investigation_trace(client):
    earlier={"device_id":"SW-PLAY","timestamp":"2026-10-31T10:00:00Z",
             "link_utilization_pct":94,"latency_ms":280,"packet_loss_pct":12,"queue_drops":160}
    later={"device_id":"SW-PLAY","timestamp":"2026-10-31T11:00:00Z",
           "link_utilization_pct":31,"latency_ms":14,"packet_loss_pct":0,"queue_drops":0}
    newest=client.post("/api/diagnose",json={"telemetry":later}).json()
    oldest=client.post("/api/diagnose",json={"telemetry":earlier}).json()
    response=client.get("/api/playback/events")
    assert response.status_code==200,response.text
    events=response.json()["events"]
    assert [x["record_id"] for x in events]==[oldest["record_id"],newest["record_id"]]
    assert events[0]["status"]=="diagnosed"
    assert len(client.get("/api/playback/events?limit=1").json()["events"])==1
    detail=client.get("/api/incidents/"+str(oldest["record_id"])+"/investigation")
    assert detail.status_code==200,detail.text
    body=detail.json()
    assert len(body["steps"])==5
    assert body["steps"][0]["id"]=="performance_agent"
    assert body["steps"][3]["id"]=="correlation_agent"
    assert body["report"]["suspected_root_cause"]=="link_congestion"
    assert any(s["messages"] for s in body["steps"])
    assert client.get("/api/incidents/999999/investigation").status_code==404
    assert client.get("/api/playback/events?limit=501").status_code==422

def test_phase3_playback_excludes_undated_records(client):
    r=client.post("/api/diagnose",json={"telemetry":{"device_id":"NO-TIME","latency_ms":20}})
    assert r.status_code==200,r.text
    response=client.get("/api/playback/events").json()
    assert response["events"]==[]
    assert response["excluded_undated"]==1

def test_phase4_spatial_playback_uses_timestamp_not_upload_order(client):
    newer={"device_id":"SW-MAP","timestamp":"2026-10-31T11:00:00Z",
           "link_utilization_pct":31,"latency_ms":14,"packet_loss_pct":0,"queue_drops":0}
    older={"device_id":"SW-MAP","timestamp":"2026-10-31T10:00:00Z",
           "link_utilization_pct":94,"latency_ms":280,"packet_loss_pct":12,"queue_drops":160}
    client.post("/api/diagnose",json={"telemetry":newer})
    client.post("/api/diagnose",json={"telemetry":older})
    assert client.post("/api/map/assign",json={"device_id":"SW-MAP","region_id":"labs"}).status_code==200
    result=client.get("/api/map/history")
    assert result.status_code==200,result.text
    frames=result.json()["frames"]
    assert len(frames)==2
    old_labs=next(x for x in frames[0]["regions"] if x["id"]=="labs")
    new_labs=next(x for x in frames[1]["regions"] if x["id"]=="labs")
    assert old_labs["status"]=="fault"
    assert frames[0]["observed_at"]=="2026-10-31T10:00:00+00:00"
    assert new_labs["status"]!="fault"
    assert next(x for x in frames[0]["regions"] if x["id"]=="main")["status"]=="unmonitored"
    assert "retroactively" in result.json()["assignment_policy"]
    assert client.get("/api/map/history?limit=501").status_code==422


def test_phase4_spatial_playback_no_assigned_devices(client):
    assert client.post("/api/diagnose",json={"telemetry":{
        "device_id":"AP-UNMAPPED","timestamp":"2026-10-31T10:00:00Z",
        "rssi_dbm":-85,"snr_db":7,"retransmissions_pct":38}}).status_code==200
    frames=client.get("/api/map/history").json()["frames"]
    assert len(frames)==1
    assert frames[0]["device_count"]==1
    assert frames[0]["mapped_device_count"]==0
    assert all(r["status"]=="unmonitored" for r in frames[0]["regions"])
