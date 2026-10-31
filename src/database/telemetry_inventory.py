"""Bulk telemetry input and timestamp-aware latest-per-device lookup."""
import json
from datetime import datetime, timezone
from sqlalchemy import select
from .models import Incident

MAX_RECORDS = 500

def parse_telemetry_batch(text: str) -> list[dict]:
    """Accept one object, an array, an object with records/telemetry, or JSONL."""
    if not text or not text.strip():
        raise ValueError("Provide at least one JSON telemetry record")
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        records = []
        for line_number, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at line {line_number}: {exc.msg}") from exc
        value = records
    if isinstance(value, dict):
        for key in ("records", "telemetry", "devices"):
            if isinstance(value.get(key), list):
                value = value[key]
                break
        else:
            value = [value]
    if not isinstance(value, list) or not value:
        raise ValueError("Expected a nonempty JSON object, JSON array, or JSONL")
    if len(value) > MAX_RECORDS:
        raise ValueError(f"Maximum {MAX_RECORDS} telemetry records per import")
    for i, record in enumerate(value, 1):
        if not isinstance(record, dict):
            raise ValueError(f"Record {i} must be a JSON object")
    return value


def observation_time(timestamp):
    """Normalize explicit timestamps to UTC; unknown timestamps sort last."""
    if not isinstance(timestamp, str) or not timestamp.strip():
        return None
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        return None
    return dt.astimezone(timezone.utc)


def describe_observation(status: str, normalized: dict, report: dict | None = None) -> tuple[str, str]:
    """Operator-facing explanation; never upgrades incomplete evidence to healthy."""
    if status == "diagnosed":
        return "FAULT DETECTED", "Measurements support a fault hypothesis."
    if status == "healthy":
        return "HEALTHY", "No fault detected across required telemetry domains in this snapshot."
    if status != "inconclusive":
        return "UNKNOWN", "Diagnostic status is not recognized."
    from src.protocol.normalizer import METRICS
    present = [k for k in METRICS if normalized.get(k) is not None]
    if not present:
        return "INSUFFICIENT DATA", "No usable diagnostic measurements were supplied."
    missing = [k for k in METRICS if normalized.get(k) is None]
    if report and report.get("supporting_evidence"):
        return "INCONCLUSIVE", "Anomalies exist but evidence is insufficient to establish their cause."
    return ("NO FAULT DETECTED · LIMITED DATA",
            f"No confirmed fault in {len(present)} supplied metrics; {len(missing)} other measurements are unavailable.")


def latest_device_records(session) -> list[dict]:
    """One latest observation per device, plus context from older fault reports."""
    rows = session.scalars(select(Incident).order_by(Incident.id.desc())).all()
    by_device = {}
    for row in rows:
        normalized = json.loads(row.normalized_telemetry_json)
        measured = observation_time(normalized.get("timestamp"))
        by_device.setdefault(row.device_id, []).append((measured, row.id, row, normalized))
    output = []
    for device_id, observations in by_device.items():
        observations.sort(key=lambda item: (item[0] is not None,
                         item[0] or datetime.min.replace(tzinfo=timezone.utc), item[1]), reverse=True)
        measured, _, latest, normalized = observations[0]
        latest_report = json.loads(latest.report_json)
        label, detail = describe_observation(latest.status, normalized, latest_report)
        prior_fault = next((x for x in observations[1:]
                            if x[2].status == "diagnosed" and
                            (measured is None or x[0] is None or x[0] < measured)), None)
        previous_fault = None
        if prior_fault:
            prior_report = json.loads(prior_fault[2].report_json)
            evidence_keys = {x.get("metric") for x in prior_report.get("supporting_evidence", [])}
            verified_again = bool(evidence_keys) and all(normalized.get(k) is not None for k in evidence_keys)
            if latest.status == "inconclusive" and not verified_again:
                previous_fault = prior_fault[2].suspected_root_cause
                label = "PREVIOUS FAULT · NOT VERIFIED CLEARED"
                detail = ("The latest snapshot lacks measurements required to verify recovery "
                          f"from the earlier {previous_fault.replace('_', ' ')} fault.")
            elif latest.status != "diagnosed" and verified_again:
                detail += " Earlier fault indicators are available in the latest snapshot; review their values and trend."
        output.append({
            "device_id": device_id, "timestamp": measured.isoformat() if measured else None,
            "site": normalized.get("site"), "parent_id": normalized.get("parent_id"),
            "status": latest.status, "root_cause": latest.suspected_root_cause,
            "evidence_support": latest.confidence, "incident_id": latest.incident_id,
            "record_id": latest.id, "has_timestamp": measured is not None,
            "display_status": label, "status_detail": detail,
            "previous_fault": previous_fault,
            "observation_count": len(observations),
        })
    return sorted(output, key=lambda item: item["device_id"])
