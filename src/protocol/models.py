"""ACP v1.2.0 immutable validated agent messages."""
from datetime import datetime,timezone
from typing import Any,Literal
from uuid import UUID,uuid4
from pydantic import BaseModel,Field,ConfigDict,field_validator
class ImmutableModel(BaseModel):
 model_config=ConfigDict(frozen=True,extra="forbid")
class EvidenceItem(ImmutableModel):
 metric:str
 observed_value:Any
 baseline:Any|None=None
 unit:str
 severity:Literal["INFO","LOW","MEDIUM","HIGH","CRITICAL"]
 interpretation:str
class AgentFinding(ImmutableModel):
 agent_id:str
 status:Literal["HEALTHY","DEGRADED","ANOMALY_DETECTED","INSUFFICIENT_DATA"]
 primary_hypothesis:str|None=None
 supporting_evidence:list[EvidenceItem]=Field(default_factory=list)
 affected_components:list[str]=Field(default_factory=list)
 confidence_contribution:float=Field(ge=0,le=1)
 limitations:list[str]=Field(default_factory=list)
class AgentEnvelope(ImmutableModel):
 message_id:UUID=Field(default_factory=uuid4)
 correlation_id:str
 timestamp:datetime=Field(default_factory=lambda:datetime.now(timezone.utc))
 sender:str
 recipient:str
 schema_version:Literal["1.2.0"]="1.2.0"
 payload:AgentFinding
 @field_validator("message_id")
 @classmethod
 def require_uuid4(cls,value):
  if value.version!=4:raise ValueError("message_id must be UUID4")
  return value
 @field_validator("timestamp")
 @classmethod
 def utc_only(cls,value):
  if value.tzinfo is None or value.utcoffset()!=timezone.utc.utcoffset(value):raise ValueError("timestamp must be UTC")
  return value
class ReportEvidence(ImmutableModel):
 metric:str
 value:Any
 interpretation:str
class FinalDiagnosticReport(ImmutableModel):
 incident_id:str
 status:Literal["diagnosed","inconclusive"]
 suspected_root_cause:str
 confidence:float=Field(ge=0,le=1)
 affected_devices:list[str]
 supporting_evidence:list[ReportEvidence]
 alternative_causes:list[str]
 recommended_actions:list[str]
 evidence_sources:list[str]
 limitations:list[str]
