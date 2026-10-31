import pytest
from pydantic import ValidationError
from src.graph.workflow import diagnose
from src.protocol.models import EvidenceItem
from src.protocol.normalizer import normalize
from src.utils.synthetic_data import scenarios
@pytest.mark.parametrize("scenario,cause",[("link_congestion","link_congestion"),("weak_wifi_signal","weak_wifi_signal"),("interface_fault","physical_interface_fault"),("dhcp_dns_failure","dhcp_failure")])
def test_faults(scenario,cause):
 state=diagnose(scenarios()[scenario],scenario);r=state["final_report"]
 assert r["status"]=="diagnosed"
 assert r["suspected_root_cause"]==cause
 assert r["confidence"]>0
 assert len(state["messages"])>=5
 assert r["evidence_sources"]
def test_normal_no_false_alarm():
 r=diagnose(scenarios()["normal_operation"])["final_report"]
 assert r["status"]=="healthy" and r["confidence"]==0
def test_malformed_handled():
 s=diagnose(scenarios()["malformed_and_missing_data"])
 assert s["normalized_telemetry"]["latency_ms"]==240
 assert s["normalized_telemetry"]["link_utilization_pct"]==94
 assert s["warnings"]
 assert s["final_report"]["status"] in ("diagnosed","inconclusive")
def test_insufficient_evidence():
 r=diagnose({"latency":"290ms"})["final_report"]
 assert r["status"]=="inconclusive" and r["confidence"]==0
def test_units():
 n,w=normalize({"throughput":"1.2 Gbps","ping_ms":"0.28s","util":"94%","broken":"hello"})
 assert n["throughput_mbps"]==1200 and n["latency_ms"]==280 and n["link_utilization_pct"]==94
 assert w
def test_immutable():
 item=EvidenceItem(metric="latency_ms",observed_value=290,unit="ms",severity="HIGH",interpretation="slow")
 with pytest.raises(ValidationError):item.metric="changed"
def test_invalid_data():
 s=diagnose({"util":"NaN","cpu":True,"latency":"banana","device":None})
 assert s["final_report"]["status"]=="inconclusive"
 assert len(s["warnings"])>=3
def test_arbitration():
 raw=scenarios()["link_congestion"]|{"crc_errors":15000,"link_utilization_pct":14}
 s=diagnose(raw)
 assert s["final_report"]["suspected_root_cause"]=="physical_interface_fault"
