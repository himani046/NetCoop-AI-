"""Read-only analytics based on saved NetCoop incidents; no new diagnostic claims."""
import json
from sqlalchemy import select
from src.database.models import Incident
from src.database.telemetry_inventory import observation_time
from src.utils.confidence import WEIGHTS, SEVERITY

def device_trends(session, device_id, limit=100):
    rows=session.scalars(select(Incident).where(Incident.device_id==device_id).order_by(Incident.id.desc()).limit(2000)).all()
    if not rows:return None
    points=[]
    for row in rows:
        t=json.loads(row.normalized_telemetry_json)
        stamp=observation_time(t.get("timestamp"))
        if stamp is None:continue
        metrics={k:v for k,v in t.items() if isinstance(v,(int,float)) and not isinstance(v,bool)}
        points.append({"record_id":row.id,"observed_at":stamp.isoformat(),
                       "status":row.status,"root_cause":row.suspected_root_cause,
                       "metrics":metrics})
    points.sort(key=lambda p:(p["observed_at"],p["record_id"]))
    return {"device_id":device_id,"points":points[-limit:],
            "excluded_undated":len(rows)-len(points),"source_limit_reached":len(rows)==2000}

def evidence_explanation(incident):
    report=incident["report"]
    if report["status"]!="diagnosed":
        return {"applicable":False,"reason":"Evidence support measures fault evidence, not health certainty.",
                "score":None,"items":[]}
    cause=report["suspected_root_cause"]
    # Evidence items are persisted by specialists in ACP envelopes.
    evidence=[]
    for message in incident["messages"]:
        payload=message.get("payload")
        if isinstance(payload,dict):
            for item in payload.get("supporting_evidence",[]):
                if isinstance(item,dict):evidence.append(item)
    from src.agents.correlation import CAUSE_METRICS
    expected=CAUSE_METRICS.get(cause,set())
    # Mirror correlation: include each relevant evidence occurrence from each specialist.
    selected=[e for e in evidence if e.get("metric") in expected and e.get("severity") in SEVERITY]
    contributions=[{"metric":e["metric"],"observed_value":e.get("observed_value"),
                    "severity":e["severity"],"severity_factor":SEVERITY[e["severity"]],
                    "weight":WEIGHTS.get(e["metric"],0.5),
                    "weighted_value":round(WEIGHTS.get(e["metric"],0.5)*SEVERITY[e["severity"]],4)}
                   for e in selected]
    total=sum(e["weight"] for e in contributions)
    base=(sum(e["weighted_value"] for e in contributions)/total) if total else None
    normalized=incident["normalized_telemetry"]
    present=sum(normalized.get(k) is not None for k in expected)
    missing_penalty=round(.2*(1-present/len(expected)),4) if expected else 0
    # ACP records persist the final score, but not the arbitration flag.
    # Never reverse-engineer or fabricate a conflict penalty.
    return {"applicable":True,"score":report["confidence"],
            "raw_weighted_severity":round(base,4) if base is not None else None,
            "missing_evidence_penalty":missing_penalty,
            "conflict_penalty":"not persisted",
            "score_cap":.95,"items":contributions,
            "note":"Stored final score is authoritative. Exact conflict/arbitration penalties were not saved separately; this breakdown is explanatory, not a guaranteed reconstruction."}

def incident_brief(session, limit=100):
    rows=session.scalars(select(Incident).order_by(Incident.id.desc()).limit(limit)).all()
    return [{"record_id":r.id,"incident_id":r.incident_id,"device_id":r.device_id,
             "created_at":r.created_at.isoformat(),"status":r.status,
             "root_cause":r.suspected_root_cause,"evidence_support":r.confidence,
             "report":json.loads(r.report_json)} for r in rows]
