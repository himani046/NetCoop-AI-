"""NetCoop API v1 — wraps existing LangGraph and SQLAlchemy modules."""
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import select

from src.database.models import Incident, Base
from api.campus import DemoAssignment, REGIONS, campus_snapshot
from src.database.repository import get_incident, list_incidents, save_incident
from src.database.session import session_factory
from src.database.telemetry_inventory import (
    latest_device_records, latest_device_metrics, parse_telemetry_batch, observation_time
)
from src.graph.workflow import diagnose
from src.protocol.normalizer import normalize
from src.utils.synthetic_data import scenarios

DATABASE = os.environ.get("NETCOOP_DB_PATH", "data/netcoop.db")
MAX_IMPORT = 500

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize tables as before; no schema changes to existing Streamlit database.
    session_factory(DATABASE)
    yield

app = FastAPI(title="NetCoop API", version="1.0.0", lifespan=lifespan,
              description="Evidence-first, synthetic network fault diagnostics.")
origins = [x.strip() for x in os.getenv("NETCOOP_CORS_ORIGINS", "http://localhost:3000").split(",") if x.strip()]
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET","POST"],
                   allow_headers=["Content-Type"], allow_credentials=False)

class DiagnosisInput(BaseModel):
    telemetry: dict
    save: bool = True
    include_trace: bool = True

class ImportInput(BaseModel):
    records: list[dict] = Field(min_length=1, max_length=MAX_IMPORT)

def db_session():
    return session_factory(DATABASE)()

def process_one(raw: dict, save: bool = True, trace: bool = True):
    state = diagnose(raw, incident_id="INC-" + uuid.uuid4().hex[:8].upper())
    record_id = None
    if save:
        with db_session() as session:
            record_id = save_incident(session, raw, state)
    result = {
        "record_id": record_id, "incident_id": state["incident_id"],
        "report": state["final_report"], "normalized_telemetry": state["normalized_telemetry"],
        "warnings": state.get("warnings", []),
    }
    if trace:
        result["agent_messages"] = state.get("messages", [])
        result["agent_reviews"] = state.get("gemini_agent_reviews", [])
        result["correlation"] = state.get("decision", {})
        result["report_review"] = state.get("gemini_report_review")
    return result

@app.get("/api/health")
def health():
    return {"status":"ok","source":"synthetic/test telemetry","live_monitoring":False}

@app.get("/api/scenarios")
def scenarios_route():
    return scenarios()

@app.get("/api/overview/summary")
def summary():
    with db_session() as session:
        devices=latest_device_records(session)
        total=session.query(Incident).count()
    return {
        "devices":len(devices),
        "healthy":sum(x["status"]=="healthy" for x in devices),
        "faulty":sum(x["status"]=="diagnosed" for x in devices),
        "unverified":sum(x["status"] not in ("healthy","diagnosed") for x in devices),
        "saved_observations":total, "live_monitoring":False,
    }

@app.get("/api/devices/latest")
def latest():
    with db_session() as session:
        return latest_device_records(session)

@app.get("/api/devices/{device_id}")
def device(device_id: str):
    with db_session() as session:
        match=next((x for x in latest_device_records(session) if x["device_id"]==device_id),None)
        if match is None:raise HTTPException(404,"Device not found")
        metrics=latest_device_metrics(session,match["record_id"])
    return {"device":match,"metrics":metrics}

@app.get("/api/devices/{device_id}/history")
def device_history(device_id: str, limit: int = Query(100,ge=1,le=500)):
    with db_session() as session:
        rows=session.scalars(select(Incident).where(Incident.device_id==device_id)).all()
    if not rows:raise HTTPException(404,"Device not found")
    import json
    values=[]
    for row in rows:
        t=json.loads(row.normalized_telemetry_json).get("timestamp")
        stamp=observation_time(t)
        values.append({"record_id":row.id,"incident_id":row.incident_id,
                       "timestamp":stamp.isoformat() if stamp else None,
                       "status":row.status,"root_cause":row.suspected_root_cause,
                       "evidence_support":row.confidence})
    values.sort(key=lambda x:(bool(x["timestamp"]),x["timestamp"] or "",x["record_id"]),reverse=True)
    return values[:limit]

@app.get("/api/incidents")
def incidents(limit: int = Query(100,ge=1,le=500)):
    with db_session() as session:
        return list_incidents(session,limit)

@app.get("/api/incidents/{record_id}")
def incident(record_id: int):
    with db_session() as session:
        found=get_incident(session,record_id)
    if not found:raise HTTPException(404,"Incident not found")
    return found

@app.get("/api/incidents/{record_id}/messages")
def messages(record_id: int):
    with db_session() as session:
        found=get_incident(session,record_id)
    if not found:raise HTTPException(404,"Incident not found")
    return found["messages"]

@app.post("/api/diagnose")
def diagnosis(input: DiagnosisInput):
    try:
        return process_one(input.telemetry, input.save, input.include_trace)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422,str(exc)) from exc

@app.post("/api/telemetry/import")
def import_records(input: ImportInput):
    prepared=[]
    for index, raw in enumerate(input.records, 1):
        norm, _ = normalize(raw)
        if norm.get("device_id") in (None,"UNKNOWN"):
            raise HTTPException(422,f"Record {index}: valid device_id required")
        if observation_time(norm.get("timestamp")) is None:
            raise HTTPException(422,f"Record {index}: timezone-aware ISO timestamp required")
        prepared.append(raw)
    results=[]
    for index, raw in enumerate(prepared, 1):
        try:
            x=process_one(raw,True,False)
            results.append({"index":index,"device_id":x["normalized_telemetry"]["device_id"],
                            "record_id":x["record_id"],"report":x["report"],"warnings":x["warnings"]})
        except Exception as exc:
            results.append({"index":index,"device_id":raw.get("device_id"),"error":type(exc).__name__})
    return {"count":len(results),"results":results}

class AssignmentInput(BaseModel):
    device_id: str = Field(min_length=1, max_length=200)
    region_id: str | None = None

@app.get("/api/map/regions")
def regions():
    with db_session() as session:
        return campus_snapshot(session, latest_device_records(session))

@app.post("/api/map/assign")
def assign_region(input: AssignmentInput):
    if input.region_id is not None and input.region_id not in {r["id"] for r in REGIONS}:
        raise HTTPException(422, "Unknown campus reference region")
    with db_session() as session:
        if not any(d["device_id"] == input.device_id for d in latest_device_records(session)):
            raise HTTPException(404, "Device not found in telemetry inventory")
        with session.begin_nested():
            stored = session.get(DemoAssignment, input.device_id)
            if input.region_id is None:
                if stored: session.delete(stored)
            elif stored:
                stored.region_id = input.region_id
            else:
                session.add(DemoAssignment(device_id=input.device_id, region_id=input.region_id))
        session.commit()
    return {"device_id": input.device_id, "region_id": input.region_id, "mode": "manual_demo_only"}
