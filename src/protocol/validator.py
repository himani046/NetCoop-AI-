"""ACP boundary checks: schema, routing, replay prevention, and provenance."""
from pydantic import ValidationError
from src.protocol.models import AgentEnvelope

SPECIALISTS = {"performance_agent", "infrastructure_agent", "connectivity_agent"}

def validate_messages(messages, incident_id):
    accepted, warnings = [], []
    ids, senders = set(), set()
    for index, raw in enumerate(messages):
        try:
            msg = AgentEnvelope.model_validate(raw)
            if msg.correlation_id != incident_id:
                raise ValueError("Correlation ID mismatch")
            if msg.recipient != "correlation_agent":
                raise ValueError("Unexpected recipient")
            if msg.sender not in SPECIALISTS:
                raise ValueError("Unknown specialist sender")
            if msg.payload.agent_id != msg.sender:
                raise ValueError("Payload sender mismatch")
            if msg.message_id in ids or msg.sender in senders:
                raise ValueError("Duplicate or replayed finding")
            ids.add(msg.message_id)
            senders.add(msg.sender)
            accepted.append(msg)
        except (ValidationError, ValueError, TypeError) as exc:
            warnings.append(f"Rejected ACP message {index}: {exc}")
    for sender in sorted(SPECIALISTS - senders):
        warnings.append(f"Missing ACP finding: {sender}")
    return accepted, warnings
