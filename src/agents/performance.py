from src.agents.base import BaseAgent,e
class PerformanceAgent(BaseAgent):
 agent_id="performance_agent"
 def analyze(self,t):
  evidence=[];cause=None
  util=t.get("link_utilization_pct");latency=t.get("latency_ms");loss=t.get("packet_loss_pct");jitter=t.get("jitter_ms")
  if util is not None and util>85:evidence.append(e("link_utilization_pct",util,"CRITICAL" if util>95 else "HIGH","Uplink utilization exceeds 85%","%",85))
  if latency is not None and latency>150:evidence.append(e("latency_ms",latency,"HIGH","Round-trip time exceeds 150 ms","ms",150))
  if loss is not None and loss>3:evidence.append(e("packet_loss_pct",loss,"HIGH","Elevated packet loss","%",3))
  if jitter is not None and jitter>35:evidence.append(e("jitter_ms",jitter,"MEDIUM","Elevated latency variation","ms",35))
  if util is not None and latency is not None and util>85 and latency>150:cause="link_congestion"
  elif evidence:cause="performance_degradation"
  return self.finding(t,cause,evidence,("link_utilization_pct","latency_ms","packet_loss_pct"))
