"""Loss-aware heterogeneous telemetry normalizer with explicit missing values."""
import math,re
from datetime import datetime
from typing import Any
ALIASES={
"link_utilization_pct":["util","link_util","utilization_pct","bandwidth_usage","link_utilization","utilization"],
"queue_drops":["drops","egress_drops","queue_drop_count"],
"latency_ms":["rtt","ping_ms","latency","lat_val","response_time_ms"],
"jitter_ms":["jitter","jitter_val"],"packet_loss_pct":["packet_loss","loss","ping_loss","packet_loss_percent"],
"throughput_mbps":["throughput","bandwidth_mbps","transfer_rate"],"cpu_pct":["cpu","cpu_usage","cpu_utilization","cpu_utilization_pct"],
"memory_pct":["memory","mem_usage","memory_utilization"],"crc_errors":["crc","interface_crc","crc_error_count"],
"rssi_dbm":["rssi","signal_strength","wifi_rssi"],"snr_db":["snr","signal_to_noise"],
"retransmissions_pct":["retries","retry_rate","frame_retransmissions"],
"dns_latency_ms":["dns_rtt","dns_response_time"],"dhcp_timeout_pct":["dhcp_timeout","dhcp_fail_pct","dhcp_discovery_timeout"],
"gateway_ping_ms":["gateway_ping","gateway_rtt"],"device_id":["device","hostname","device_name"],
"timestamp":["time","observed_at","ts"],"parent_id":["uplink_to","parent","upstream_device"],
"site":["location","zone","building"]}
KEYS={alias:canonical for canonical,aliases in ALIASES.items() for alias in [canonical,*aliases]}
METRICS={key for key in ALIASES if key not in {"device_id","timestamp","parent_id","site"}}
UNITS={"ms","s","sec","seconds","%","percent","gbps","mbps","kbps","dbm","db","count"}
PATTERN=re.compile(r"^\s*([-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[-+]?\d+)?)\s*([a-zA-Z%]*)\s*$",re.I)
def normalize(raw:Any)->tuple[dict[str,Any],list[str]]:
 warnings=[]
 if not isinstance(raw,dict):
  return {k:None for k in METRICS}|{"device_id":"UNKNOWN","timestamp":None,"parent_id":"UNKNOWN","site":"UNKNOWN"},["Telemetry must be a JSON object"]
 out={}
 nested=raw.get("metrics",{})
 if nested is None:nested={}
 if not isinstance(nested,dict):
  warnings.append("metrics must be a JSON object; nested measurements ignored")
  nested={}
 merged={**nested,**{k:v for k,v in raw.items() if k!="metrics"}}
 if "status" in merged:
  warnings.append("Input status is an external label, not diagnostic evidence")
  merged.pop("status")
 for key in ("interface_errors",):
  if key in merged:
   warnings.append("interface_errors is not necessarily CRC errors; preserved as unclassified telemetry")
   out[key]=merged.pop(key)
 for key in ("topology","affected_device_ids"):
  if key in merged:out[key]=merged[key]
 for rawkey,value in merged.items():
  if rawkey in ("topology","affected_device_ids"):continue
  key=KEYS.get(str(rawkey).strip().lower())
  if not key:warnings.append(f"Unrecognized telemetry key: {rawkey}");continue
  if key in out:warnings.append(f"Duplicate alias for {key}; keeping first");continue
  if key not in METRICS:
   out[key]=str(value).strip() if value is not None and str(value).strip() else ("UNKNOWN" if key!="timestamp" else None)
   continue
  if value is None or value=="":
   out[key]=None;warnings.append(f"Missing value for {key}");continue
  if isinstance(value,bool):
   out[key]=None;warnings.append(f"Invalid boolean for {key}");continue
  match=PATTERN.fullmatch(str(value))
  if not match:
   out[key]=None;warnings.append(f"Invalid numeric measurement {key}: {value!r}");continue
  number=float(match.group(1));suffix=match.group(2).lower()
  if not math.isfinite(number) or suffix not in UNITS|{""}:
   out[key]=None;warnings.append(f"Nonfinite or unsupported unit for {key}");continue
  if suffix in ("s","sec","seconds"):
   if not key.endswith("_ms"):out[key]=None;warnings.append(f"Invalid time unit for {key}");continue
   number*=1000
  elif suffix in ("gbps","kbps","mbps"):
   if key!="throughput_mbps":out[key]=None;warnings.append(f"Unexpected throughput unit for {key}");continue
   number*=1000 if suffix=="gbps" else .001 if suffix=="kbps" else 1
  elif suffix in ("%","percent") and not key.endswith("_pct"):
   out[key]=None;warnings.append(f"Unexpected percent for {key}");continue
  elif suffix in ("db","dbm") and not key.endswith("_"+suffix):
   out[key]=None;warnings.append(f"Unexpected radio unit for {key}");continue
  if number<0 and key!="rssi_dbm":
   out[key]=None;warnings.append(f"Negative measurement for {key}");continue
  if key.endswith("_pct") and number>100:
   out[key]=None;warnings.append(f"Percentage outside range for {key}");continue
  out[key]=number
 for key in METRICS:out.setdefault(key,None)
 for key in ("device_id","site","parent_id"):
  out.setdefault(key,"UNKNOWN")
  if out[key]=="UNKNOWN":warnings.append(f"Missing {key}")
 out.setdefault("timestamp",None)
 if out["timestamp"] is None:warnings.append("Missing timestamp; temporal correlation limited")
 else:
  try:datetime.fromisoformat(out["timestamp"].replace("Z","+00:00"))
  except ValueError:out["timestamp"]=None;warnings.append("Invalid timestamp")
 return out,warnings
