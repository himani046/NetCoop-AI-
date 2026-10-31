from src.utils.topology import analyze_topology
from src.agents.base import BaseAgent,e
class ConnectivityAgent(BaseAgent):
 agent_id="connectivity_agent"
 def analyze(self,t):
  evidence=[];cause=None;notes=[]
  rssi=t.get("rssi_dbm");snr=t.get("snr_db");retries=t.get("retransmissions_pct");dhcp=t.get("dhcp_timeout_pct");dns=t.get("dns_latency_ms");gw=t.get("gateway_ping_ms")
  if rssi is not None and rssi<-75:evidence.append(e("rssi_dbm",rssi,"HIGH","Weak Wi-Fi signal","dBm",-75))
  if snr is not None and snr<15:evidence.append(e("snr_db",snr,"HIGH","Poor Wi-Fi signal-to-noise ratio","dB",15))
  if retries is not None and retries>20:evidence.append(e("retransmissions_pct",retries,"HIGH","Excessive Wi-Fi retries","%",20))
  if dhcp is not None and dhcp>=50:evidence.append(e("dhcp_timeout_pct",dhcp,"CRITICAL","DHCP discovery failures","%",0))
  if dns is not None and dns>500:evidence.append(e("dns_latency_ms",dns,"HIGH","DNS lookup is slow","ms",500))
  if rssi is not None and snr is not None and rssi<-75 and snr<15:cause="weak_wifi_signal"
  elif dhcp is not None and dhcp>=50 and gw is not None and gw<20:cause="dhcp_failure"
  elif dns is not None and dns>500 and gw is not None and gw<20:cause="dns_failure"
  elif evidence:cause="connectivity_anomaly"
  if t.get("parent_id")=="UNKNOWN":notes.append("No upstream topology link provided; blast radius cannot be confirmed")
  else:notes.append(f"Upstream: {t['parent_id']}; local site: {t.get('site','UNKNOWN')}")
  topo=analyze_topology(t)
  if topo["affected"]:notes.append(f"Topology blast radius: {topo['scope']}; common ancestor: {topo['common_ancestor']}")
  notes.extend(topo["warnings"])
  finding=self.finding(t,cause,evidence,("rssi_dbm","snr_db","dhcp_timeout_pct","dns_latency_ms"),notes)
  if topo["affected"]:return finding.model_copy(update={"affected_components":topo["affected"]})
  return finding
