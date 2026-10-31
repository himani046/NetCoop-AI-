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


def latest_device_records(session) -> list[dict]:
    """Latest measured state per device; never use ingestion time as event time."""
    rows = session.scalars(select(Incident).order_by(Incident.id.desc())).all()
    latest = {}
    for row in rows:
        raw = json.loads(row.normalized_telemetry_json)
        timestamp = raw.get("timestamp")
        measured = observation_time(timestamp)
        key = row.device_id
        candidate = {
            "device_id": key,
            "timestamp": measured.isoformat() if measured else None,
            "site": raw.get("site"),
            "parent_id": raw.get("parent_id"),
            "status": row.status,
            "root_cause": row.suspected_root_cause,
            "evidence_support": row.confidence,
            "incident_id": row.incident_id,
            "record_id": row.id,
            "has_timestamp": measured is not None,
        }
        current = latest.get(key)
        if current is None:
            latest[key] = candidate
        elif measured and (not current["has_timestamp"] or measured.isoformat() > current["timestamp"]):
            latest[key] = candidate
        elif measured and current["timestamp"] == measured.isoformat() and row.id > current["record_id"]:
            latest[key] = candidate
        # An untimestamped/older reading never overwrites a dated newer one.
    return sorted(latest.values(), key=lambda item: item["device_id"])
