from src.protocol.models import AgentEnvelope

def check_message(raw):
    return AgentEnvelope.model_validate(raw)
