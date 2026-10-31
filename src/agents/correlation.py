"""Cross-agent evidence arbitration with explicit sufficiency checks."""
from src.utils.confidence import score
CAUSE_METRICS={"link_congestion":{"link_utilization_pct","queue_drops","latency_ms","packet_loss_pct"},"physical_interface_fault":{"crc_errors","latency_ms","packet_loss_pct"},"weak_wifi_signal":{"rssi_dbm","snr_db","retransmissions_pct"},"dhcp_failure":{"dhcp_timeout_pct","gateway_ping_ms"},"dns_failure":{"dns_latency_ms","gateway_ping_ms"},"device_overload":{"cpu_pct","memory_pct","latency_ms"}}
PRIORITY=["physical_interface_fault","weak_wifi_signal","dhcp_failure","dns_failure","link_congestion","device_overload"]
def correlate(t,findings,warnings,arbitration=False):
 metrics={k:v for k,v in t.items() if isinstance(v,(int,float)) and not isinstance(v,bool)}
 hypotheses=[f.primary_hypothesis for f in findings if f.primary_hypothesis in CAUSE_METRICS]
 conflicts=[];notes=[]
 if "link_congestion" in hypotheses and "physical_interface_fault" in hypotheses:conflicts.append("Congestion and physical fault hypotheses disagree")
 if len(set(hypotheses))>1 and not conflicts:conflicts.append("Specialist agents propose competing causes")
 if arbitration and conflicts:notes.append("Arbitration compared metric-specific evidence, not agent votes")
 if len(metrics)<3:notes.append("Fewer than three valid numerical measurements")
 candidate=None
 if t.get("crc_errors") is not None and t["crc_errors"]>=100 and (t.get("link_utilization_pct") or 0)<50:candidate="physical_interface_fault"
 elif t.get("rssi_dbm") is not None and t.get("snr_db") is not None and t["rssi_dbm"]<-75 and t["snr_db"]<15:candidate="weak_wifi_signal"
 elif t.get("dhcp_timeout_pct") is not None and t["dhcp_timeout_pct"]>=50 and t.get("gateway_ping_ms") is not None and t["gateway_ping_ms"]<20:candidate="dhcp_failure"
 elif t.get("dns_latency_ms") is not None and t["dns_latency_ms"]>500 and t.get("gateway_ping_ms") is not None and t["gateway_ping_ms"]<20:candidate="dns_failure"
 elif t.get("link_utilization_pct") is not None and t.get("latency_ms") is not None and t["link_utilization_pct"]>85 and t["latency_ms"]>150:candidate="link_congestion"
 elif t.get("cpu_pct") is not None and t["cpu_pct"]>=90:candidate="device_overload"
 if len(metrics)<3:candidate=None
 if candidate:
  required={"physical_interface_fault":["crc_errors","link_utilization_pct"],"weak_wifi_signal":["rssi_dbm","snr_db"],"dhcp_failure":["dhcp_timeout_pct","gateway_ping_ms"],"dns_failure":["dns_latency_ms","gateway_ping_ms"],"link_congestion":["link_utilization_pct","latency_ms"],"device_overload":["cpu_pct"]}[candidate]
  missing=[k for k in required if t.get(k) is None]
  if missing:notes.append("Missing critical path data: "+", ".join(missing));candidate=None
 evidence=[e for f in findings for e in f.supporting_evidence]
 diagnostic=[e for e in evidence if candidate and e.metric in CAUSE_METRICS[candidate]]
 if t.get("queue_drops")==0 and t.get("link_utilization_pct") is not None and t["link_utilization_pct"]<20:notes.append("Zero queue drops and low utilization argue against congestion")
 unresolved=bool(conflicts) and not arbitration
 path=CAUSE_METRICS.get(candidate,set())
 present=sum(t.get(k) is not None for k in path)
 penalty=.2*(1-present/len(path)) if path else 0
 confidence=score(diagnostic,.35 if unresolved else 0,penalty,not bool(candidate))
 if candidate and confidence<.2:notes.append("Insufficient convergent support");candidate=None;confidence=0.
 alternatives=[x for x in PRIORITY if x!=candidate and x in hypotheses]
 if candidate=="link_congestion":alternatives.append("upstream_link_congestion")
 healthy_keys={"link_utilization_pct","latency_ms","packet_loss_pct","cpu_pct","memory_pct","crc_errors","rssi_dbm","snr_db","dhcp_timeout_pct","dns_latency_ms","gateway_ping_ms"}
 # Metadata warnings do not invalidate complete, normal numeric telemetry.
 # Numeric-quality, schema and ACP warnings still block a positive health claim.
 metadata_warnings = {"Missing site", "Missing parent_id", "Missing timestamp; temporal correlation limited",
                      "Input status is an external label, not diagnostic evidence"}
 blocking_warnings = [w for w in warnings if w not in metadata_warnings]
 complete=(all(t.get(k) is not None for k in healthy_keys)
           and all(f.status=="HEALTHY" for f in findings) and len(findings)==3
           and not blocking_warnings and not conflicts and not candidate)
 if complete:notes.append("No anomalies detected across complete required telemetry snapshot")
 return {"healthy":complete,"cause":candidate,"confidence":confidence,"evidence":diagnostic if candidate else evidence,"alternatives":list(dict.fromkeys(alternatives)),"conflicts":conflicts,"resolution_notes":notes,"inconclusive":not bool(candidate),"warnings":warnings}
