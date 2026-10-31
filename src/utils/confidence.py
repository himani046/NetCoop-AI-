"""Deterministic evidence support, not an empirical probability."""
from src.protocol.models import EvidenceItem
WEIGHTS={"crc_errors":1.0,"queue_drops":0.9,"link_utilization_pct":0.9,"dhcp_timeout_pct":1.0,"dns_latency_ms":0.8,"rssi_dbm":0.9,"snr_db":0.9,"retransmissions_pct":0.8,"latency_ms":0.6,"packet_loss_pct":0.6,"cpu_pct":0.8,"memory_pct":0.7,"gateway_ping_ms":0.5,"jitter_ms":0.5}
SEVERITY={"INFO":0.0,"LOW":0.25,"MEDIUM":0.55,"HIGH":0.85,"CRITICAL":1.0}
def score(evidence:list[EvidenceItem],conflict_penalty:float=0.,missing_penalty:float=0.,inconclusive:bool=False)->float:
 if inconclusive or not evidence:return 0.
 weights=[WEIGHTS.get(e.metric,.5) for e in evidence]
 raw=sum(w*SEVERITY[e.severity] for w,e in zip(weights,evidence))/sum(weights)
 return round(min(.95,raw*(1-max(0,min(1,conflict_penalty)))*(1-max(0,min(1,missing_penalty)))),4)
