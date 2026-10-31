"""Parallel specialist agents, fan-in barrier, bounded conflict arbitration."""
import os
from dotenv import load_dotenv
load_dotenv()
from langgraph.graph import StateGraph,START,END
from src.graph.state import DiagnosticState
from src.protocol.normalizer import normalize
from src.protocol.models import AgentEnvelope,AgentFinding
from src.protocol.validator import validate_messages
from src.agents.performance import PerformanceAgent
from src.agents.infrastructure import InfrastructureAgent
from src.agents.connectivity import ConnectivityAgent
from src.agents.correlation import correlate
from src.agents.reporting import report,markdown_report
from src.agents.llm_fallback import structured_second_opinion
from src.utils.calibration import calibrated_probability,load_calibration
def normalization_node(state:DiagnosticState)->dict:
 t,w=normalize(state.get("raw_telemetry",{}))
 return {"normalized_telemetry":t,"warnings":w,"retry_budget":state.get("retry_budget",1),"messages":[]}
def agent_node(agent,field):
 def run(state:DiagnosticState):
  f=agent.analyze(state["normalized_telemetry"])
  msg=AgentEnvelope(correlation_id=state["incident_id"],sender=agent.agent_id,recipient="correlation_agent",payload=f)
  return {field:f.model_dump(mode="json"),"messages":[msg.model_dump(mode="json")]}
 return run
def decision_node(state:DiagnosticState,arbitration:bool=False)->dict:
 raw_messages=[m for m in state.get("messages",[]) if isinstance(m,dict) and "payload" in m]
 accepted, protocol_warnings=validate_messages(raw_messages,state["incident_id"])
 fs=[m.payload for m in accepted]
 d=correlate(state["normalized_telemetry"],fs,[*state["warnings"],*protocol_warnings],arbitration=arbitration)
 if protocol_warnings:
  d["resolution_notes"].extend(protocol_warnings)
  d["cause"]=None
  d["confidence"]=0.0
  d["inconclusive"]=True
  d["resolution_notes"].append("ACP validation incomplete: diagnosis withheld pending all specialist findings")
 if (arbitration or not d["conflicts"]) and os.getenv("NETCOOP_LLM_MODEL"):
  opinion,warning=structured_second_opinion(state["normalized_telemetry"],[f.model_dump(mode="json") for f in fs],d["cause"])
  if opinion is not None:
   d["ai_review"] = opinion.model_dump(mode="json")
   d["resolution_notes"].append("Advisory LLM second opinion: "+opinion.explanation)
   d["alternatives"]=list(dict.fromkeys(d["alternatives"]+opinion.alternative_causes))
   if opinion.suggested_cause!=d["cause"]:d["resolution_notes"].append("LLM differs from deterministic evidence; no automatic override")
  elif warning:d["resolution_notes"].append(warning)
 message={"message_type":"arbitration" if arbitration else "correlation","sender":"correlation_agent","recipient":"reporting_agent","correlation_id":state["incident_id"],"decision":{"cause":d["cause"],"confidence":d["confidence"],"conflicts":d["conflicts"]}}
 return {"validated_messages":[m.model_dump(mode="json") for m in accepted],"decision":d,"conflicts_detected":bool(d["conflicts"]) and not arbitration,"resolution_notes":d["resolution_notes"],"retry_budget":max(0,state.get("retry_budget",0)-1) if arbitration else state.get("retry_budget",0),"messages":[message]}
def route(state:DiagnosticState)->str:
 return "arbitration" if state.get("conflicts_detected") and state.get("retry_budget",0)>0 else "reporting"
def reporting_node(state:DiagnosticState)->dict:
 fs=[AgentFinding.model_validate(state[k]) for k in ("tpa_finding","iha_finding","cta_finding")]
 r=report(state["incident_id"],state["normalized_telemetry"],fs,state["decision"])
 output=r.model_dump(mode="json")
 path=os.getenv("NETCOOP_CALIBRATION_FILE")
 if path and r.status=="diagnosed":
  try:
   model=load_calibration(path)
   p=calibrated_probability(r.confidence,model)
   output["calibrated_correctness_probability"]=p
   if p is None:output["limitations"].append("Insufficient independent calibration samples in score bin")
  except (ValueError,KeyError,OSError,TypeError) as exc:output["limitations"].append(f"Invalid calibration model: {exc}")
 return {"final_report":output,"markdown_report":markdown_report(r),"messages":[{"message_type":"final_report","sender":"reporting_agent","recipient":"operator","correlation_id":state["incident_id"],"status":r.status}]}
def build_graph():
 g=StateGraph(DiagnosticState)
 g.add_node("normalize",normalization_node)
 g.add_node("tpa",agent_node(PerformanceAgent(),"tpa_finding"))
 g.add_node("iha",agent_node(InfrastructureAgent(),"iha_finding"))
 g.add_node("cta",agent_node(ConnectivityAgent(),"cta_finding"))
 g.add_node("correlation",lambda s:decision_node(s,False))
 g.add_node("arbitration",lambda s:decision_node(s,True))
 g.add_node("reporting",reporting_node)
 g.add_edge(START,"normalize")
 for n in ("tpa","iha","cta"):g.add_edge("normalize",n)
 g.add_edge(["tpa","iha","cta"],"correlation")
 g.add_conditional_edges("correlation",route,{"arbitration":"arbitration","reporting":"reporting"})
 g.add_edge("arbitration","reporting")
 g.add_edge("reporting",END)
 return g.compile()
def diagnose(raw:dict,incident_id:str="INC-DEMO",retry_budget:int=1)->DiagnosticState:
 return build_graph().invoke({"incident_id":incident_id,"raw_telemetry":raw,"retry_budget":retry_budget})
