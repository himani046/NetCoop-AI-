from src.agents.base import BaseAgent,e
class InfrastructureAgent(BaseAgent):
 agent_id="infrastructure_agent"
 def analyze(self,t):
  evidence=[];cause=None
  cpu=t.get("cpu_pct");mem=t.get("memory_pct");crc=t.get("crc_errors");drops=t.get("queue_drops");util=t.get("link_utilization_pct")
  if crc is not None and crc>=100:evidence.append(e("crc_errors",crc,"CRITICAL" if crc>=1000 else "HIGH","Interface CRC errors indicate possible physical corruption","count",0))
  if drops is not None and drops>20:evidence.append(e("queue_drops",drops,"HIGH","Elevated egress queue drops","count",0))
  if cpu is not None and cpu>=90:evidence.append(e("cpu_pct",cpu,"HIGH","CPU pressure may affect forwarding","%",90))
  if mem is not None and mem>=90:evidence.append(e("memory_pct",mem,"HIGH","Memory pressure detected","%",90))
  if crc is not None and crc>=100 and util is not None and util<50:cause="physical_interface_fault"
  elif drops is not None and drops>20 and util is not None and util>85:cause="link_congestion"
  elif cpu is not None and cpu>=90:cause="device_overload"
  elif evidence:cause="infrastructure_anomaly"
  return self.finding(t,cause,evidence,("crc_errors","queue_drops","cpu_pct","memory_pct"))
