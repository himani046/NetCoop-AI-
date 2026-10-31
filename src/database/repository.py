"""Transactional incident persistence and history retrieval."""
import json
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from .models import AgentMessage, Device, Incident

def serialize(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)

def save_incident(session: Session, raw: dict, state: dict) -> int:
    """Insert one diagnostic run. Repeated incident IDs are allowed as separate runs."""
    report = state["final_report"]
    normalized = state["normalized_telemetry"]
    device_id = str(normalized.get("device_id") or "UNKNOWN")
    with session.begin():
        device = session.get(Device, device_id)
        if device is None:
            device = Device(device_id=device_id)
            session.add(device)
        device.site = normalized.get("site")
        device.parent_id = normalized.get("parent_id")
        incident = Incident(
            incident_id=state["incident_id"], device=device,
            status=report["status"], suspected_root_cause=report["suspected_root_cause"],
            confidence=float(report["confidence"]),
            raw_telemetry_json=serialize(raw),
            normalized_telemetry_json=serialize(normalized),
            report_json=serialize(report),
            markdown_report=state.get("markdown_report", ""),
            warnings_json=serialize(state.get("warnings", [])),
        )
        session.add(incident)
        session.flush()
        for order, message in enumerate(state.get("messages", [])):
            session.add(AgentMessage(
                incident_pk=incident.id, message_order=order,
                sender=str(message.get("sender", "unknown")),
                recipient=str(message.get("recipient", "unknown")),
                payload_json=serialize(message),
            ))
        pk = incident.id
    return pk

def list_incidents(session: Session, limit: int = 100) -> list[dict]:
    rows = session.scalars(select(Incident).order_by(Incident.id.desc()).limit(max(1,min(limit,1000)))).all()
    return [{"id":r.id,"incident_id":r.incident_id,"device_id":r.device_id,
             "status":r.status,"suspected_root_cause":r.suspected_root_cause,
             "confidence":r.confidence,"created_at":r.created_at.isoformat()} for r in rows]

def get_incident(session: Session, pk: int) -> dict | None:
    incident = session.get(Incident, pk)
    if incident is None:
        return None
    messages = session.scalars(select(AgentMessage).where(AgentMessage.incident_pk == pk).order_by(AgentMessage.message_order)).all()
    return {"id":pk,"incident_id":incident.incident_id,"device_id":incident.device_id,
            "raw_telemetry":json.loads(incident.raw_telemetry_json),
            "normalized_telemetry":json.loads(incident.normalized_telemetry_json),
            "report":json.loads(incident.report_json),
            "warnings":json.loads(incident.warnings_json),
            "markdown_report":incident.markdown_report,
            "messages":[json.loads(m.payload_json) for m in messages]}
