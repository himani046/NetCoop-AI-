"""Timestamp-oriented, read-only playback and persisted ACP investigation projection."""
import json
from datetime import datetime, timezone
from sqlalchemy import select
from src.database.models import Incident
from src.database.telemetry_inventory import observation_time

AGENTS = [
 ("performance_agent", "Performance", "Specialist"),
 ("infrastructure_agent", "Infrastructure", "Specialist"),
 ("connectivity_agent", "Connectivity", "Specialist"),
 ("correlation_agent", "Correlation", "Arbitration"),
 ("reporting_agent", "Reporting", "Synthesis"),
]

def playback_events(session, limit: int = 500):
    # Read persisted records, not synthesized live events; sort by observation time.
    rows=session.scalars(select(Incident).order_by(Incident.id.desc()).limit(5000)).all()
    events=[]
    for item in rows:
        data=json.loads(item.normalized_telemetry_json)
        observed=observation_time(data.get("timestamp"))
        events.append({"record_id":item.id,"device_id":item.device_id,
                       "observed_at":observed.isoformat() if observed else None,
                       "status":item.status,"root_cause":item.suspected_root_cause,
                       "evidence_support":item.confidence})
    # Undated observations are explicitly excluded from time-based playback.
    dated=[e for e in events if e["observed_at"]]
    dated.sort(key=lambda e:(e["observed_at"],e["record_id"]))
    return {"events":dated[-limit:],"excluded_undated":len(events)-len(dated),
            "truncated_source":len(rows)==5000,"source":"saved synthetic diagnostic observations"}

def investigation(incident):
    messages=incident["messages"]
    steps=[]
    for agent_id,label,role in AGENTS:
        incoming=[m for m in messages if m.get("sender")==agent_id]
        findings=[m.get("payload",{}) for m in incoming if isinstance(m.get("payload"),dict)]
        steps.append({"id":agent_id,"name":label,"role":role,
                      "messages":incoming,"findings":findings,
                      "present":bool(incoming)})
    return {"record_id":incident["id"],"incident_id":incident["incident_id"],
            "device_id":incident["device_id"],"report":incident["report"],
            "warnings":incident["warnings"],"steps":steps,
            "messages":messages,"note":"Persisted ACP messages are an investigation replay, not a real-time execution trace."}
