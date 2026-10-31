from abc import ABC,abstractmethod
from typing import Any
from src.protocol.models import AgentFinding,EvidenceItem
class BaseAgent(ABC):
 agent_id:str
 @abstractmethod
 def analyze(self,telemetry:dict[str,Any])->AgentFinding:
  raise NotImplementedError("Concrete agents must implement analyze")
 def finding(self,telemetry,hypothesis,evidence,required,limitations=None):
  missing=[key for key in required if telemetry.get(key) is None]
  status="INSUFFICIENT_DATA" if not evidence and len(missing)==len(required) else "ANOMALY_DETECTED" if evidence else "HEALTHY"
  return AgentFinding(agent_id=self.agent_id,status=status,primary_hypothesis=hypothesis if evidence else None,supporting_evidence=evidence,affected_components=[] if telemetry.get("device_id")=="UNKNOWN" else [telemetry["device_id"]],confidence_contribution=min(.95,.25+.15*len(evidence)) if evidence else 0.,limitations=(limitations or [])+[f"Missing {k}" for k in missing])
def e(metric,value,severity,interpretation,unit="",baseline=None):
 return EvidenceItem(metric=metric,observed_value=value,baseline=baseline,unit=unit,severity=severity,interpretation=interpretation)
