import pytest
from pydantic import ValidationError
from src.graph.workflow import diagnose
from src.protocol.models import EvidenceItem
from src.protocol.normalizer import normalize
from src.utils.synthetic_data import scenarios


@pytest.mark.parametrize("scenario,cause", [
    ("link_congestion", "link_congestion"),
    ("weak_wifi_signal", "weak_wifi_signal"),
    ("interface_fault", "physical_interface_fault"),
    ("dhcp_dns_failure", "dhcp_failure"),
])
def test_faults(scenario, cause):
    state = diagnose(scenarios()[scenario], scenario)
    report = state["final_report"]
    assert report["status"] == "diagnosed"
    assert report["suspected_root_cause"] == cause
    assert report["confidence"] > 0
    assert len(state["messages"]) >= 5
    assert report["evidence_sources"]


def test_normal_no_false_alarm():
    report = diagnose(scenarios()["normal_operation"])["final_report"]
    assert report["status"] == "healthy" and report["confidence"] == 0


def test_user_generator_six_scenarios():
    samples = [
        {
            "device_id": "SW_CAMPUS_4",
            "metrics": {"cpu_utilization_pct": 19.15, "link_utilization_pct": 23.07,
                        "packet_loss_pct": 0.0, "latency_ms": 10.05, "jitter_ms": 2.0, "queue_drops": 0},
        },
        {
            "device_id": "SW_CAMPUS_7",
            "metrics": {"cpu_utilization_pct": 47.07, "link_utilization_pct": 62.32,
                        "packet_loss_pct": 1.07, "latency_ms": 367.66, "jitter_ms": 40.21, "queue_drops": 47},
        },
        {
            "device_id": "SW_CAMPUS_5",
            "metrics": {"cpu_utilization_pct": 99.9, "link_utilization_pct": 100.0,
                        "packet_loss_pct": 25.92, "latency_ms": 764.66, "queue_drops": 12219,
                        "interface_errors": 409},
        },
        {
            "device_id": "SW_CAMPUS_3",
            "metrics": {"cpu_utilization_pct": 57.46, "link_utilization_pct": 40.89,
                        "packet_loss_pct": 12.39, "latency_ms": 237.87, "jitter_ms": 46.84,
                        "interface_errors": 55},
        },
        {
            "device_id": "SW_CAMPUS_7",
            "metrics": {"cpu_utilization_pct": 78.98, "link_utilization_pct": 94.51,
                        "packet_loss_pct": 2.95, "latency_ms": 230.89, "jitter_ms": 30.17,
                        "queue_drops": 322},
        },
        {
            "device_id": "HOSTEL_AP_3",
            "metrics": {"rssi_dbm": -78, "snr_db": 12, "retransmissions_pct": 53,
                        "channel_utilization_pct": 90},
        },
    ]
    expected = [
        ("healthy", "No network fault detected"),
        ("diagnosed", "latency_spike"),
        ("diagnosed", "physical_interface_fault"),
        ("diagnosed", "packet_loss"),
        ("diagnosed", "link_congestion"),
        ("diagnosed", "weak_wifi_signal"),
    ]
    for record, (expected_status, expected_cause) in zip(samples, expected):
        report = diagnose(record)["final_report"]
        assert report["status"] == expected_status, (record["device_id"], report)
        assert report["suspected_root_cause"] == expected_cause, report


def test_malformed_handled():
    state = diagnose(scenarios()["malformed_and_missing_data"])
    assert state["normalized_telemetry"]["latency_ms"] == 240
    assert state["normalized_telemetry"]["link_utilization_pct"] == 94
    assert state["warnings"]
    assert state["final_report"]["status"] in ("diagnosed", "inconclusive")


def test_insufficient_evidence():
    report = diagnose({"latency": "290ms"})["final_report"]
    assert report["status"] == "inconclusive" and report["confidence"] == 0


def test_units():
    normalized, warnings = normalize({
        "throughput": "1.2 Gbps", "ping_ms": "0.28s", "util": "94%", "broken": "hello"
    })
    assert normalized["throughput_mbps"] == 1200
    assert normalized["latency_ms"] == 280
    assert normalized["link_utilization_pct"] == 94
    assert warnings


def test_immutable():
    item = EvidenceItem(metric="latency_ms", observed_value=290, unit="ms",
                        severity="HIGH", interpretation="slow")
    with pytest.raises(ValidationError):
        item.metric = "changed"


def test_invalid_data():
    state = diagnose({"util": "NaN", "cpu": True, "latency": "banana", "device": None})
    assert state["final_report"]["status"] == "inconclusive"
    assert len(state["warnings"]) >= 3


def test_arbitration():
    raw = scenarios()["link_congestion"] | {"crc_errors": 15000, "link_utilization_pct": 14}
    state = diagnose(raw)
    assert state["final_report"]["suspected_root_cause"] == "physical_interface_fault"
