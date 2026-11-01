"""Evidence-based cross-agent arbitration for heterogeneous telemetry."""
from src.utils.confidence import score

CAUSE_METRICS = {
    "link_congestion": {"link_utilization_pct", "queue_drops", "latency_ms", "packet_loss_pct"},
    "physical_interface_fault": {"crc_errors", "interface_errors", "latency_ms", "packet_loss_pct"},
    "weak_wifi_signal": {"rssi_dbm", "snr_db", "retransmissions_pct"},
    "dhcp_failure": {"dhcp_timeout_pct", "gateway_ping_ms"},
    "dns_failure": {"dns_latency_ms", "gateway_ping_ms"},
    "device_overload": {"cpu_pct", "memory_pct", "latency_ms"},
    "packet_loss": {"packet_loss_pct", "interface_errors", "latency_ms"},
    "latency_spike": {"latency_ms", "jitter_ms", "packet_loss_pct"},
}
PRIORITY = [
    "physical_interface_fault", "weak_wifi_signal", "dhcp_failure", "dns_failure",
    "link_congestion", "packet_loss", "latency_spike", "device_overload",
]


def correlate(t, findings, warnings, arbitration=False):
    """Choose a supported fault, or report healthy only with adequate device-relevant data."""
    conflicts = []
    notes = []
    hypotheses = [
        f.primary_hypothesis for f in findings
        if f.primary_hypothesis in CAUSE_METRICS
    ]
    if "link_congestion" in hypotheses and "physical_interface_fault" in hypotheses:
        conflicts.append("Congestion and physical/interface-fault hypotheses disagree")
    elif len(set(hypotheses)) > 1:
        conflicts.append("Specialist agents propose competing causes")
    if arbitration and conflicts:
        notes.append("Arbitration compared metric-specific evidence, not agent votes")

    candidate = None
    loss = t.get("packet_loss_pct")
    latency = t.get("latency_ms")
    util = t.get("link_utilization_pct")
    drops = t.get("queue_drops")
    interface_errors = t.get("interface_errors")
    crc_errors = t.get("crc_errors")
    rssi, snr = t.get("rssi_dbm"), t.get("snr_db")
    retries = t.get("retransmissions_pct")
    cpu, memory = t.get("cpu_pct"), t.get("memory_pct")

    # Strong combined evidence suggests a physical/interface problem, but does not prove it.
    if ((interface_errors is not None and interface_errors >= 100 and
         loss is not None and loss >= 10) or
        (crc_errors is not None and crc_errors >= 100 and
         (util is None or util < 85)):
        candidate = "physical_interface_fault"
        notes.append("Possible physical/interface fault; verify counters and inspect hardware before concluding.")
    elif rssi is not None and snr is not None and rssi < -75 and snr < 15:
        candidate = "weak_wifi_signal"
    elif t.get("dhcp_timeout_pct") is not None and t["dhcp_timeout_pct"] >= 50 and t.get("gateway_ping_ms") is not None and t["gateway_ping_ms"] < 20:
        candidate = "dhcp_failure"
    elif t.get("dns_latency_ms") is not None and t["dns_latency_ms"] > 500 and t.get("gateway_ping_ms") is not None and t["gateway_ping_ms"] < 20:
        candidate = "dns_failure"
    elif util is not None and util >= 85 and (
        (latency is not None and latency >= 100) or (drops is not None and drops >= 100)
    ):
        candidate = "link_congestion"
    elif loss is not None and loss >= 5:
        candidate = "packet_loss"
    elif latency is not None and latency >= 150:
        candidate = "latency_spike"
    elif cpu is not None and cpu >= 90 or memory is not None and memory >= 90:
        candidate = "device_overload"

    # Keep specialist evidence for the selected cause, supplemented by direct telemetry evidence.
    evidence = [e for f in findings for e in f.supporting_evidence]
    selected_metrics = CAUSE_METRICS.get(candidate, set())
    diagnostic = [e for e in evidence if e.metric in selected_metrics]
    if candidate:
        # Directly create evidence for metrics that the specialist agents did not expose.
        from src.agents.base import e as evidence_item
        direct = {
            "link_congestion": [
                ("link_utilization_pct", "HIGH", "High link utilization supports congestion", "%"),
                ("latency_ms", "HIGH", "Elevated latency supports congestion", "ms"),
                ("queue_drops", "HIGH", "Elevated queue drops support congestion", "count"),
            ],
            "physical_interface_fault": [
                ("interface_errors", "CRITICAL", "High interface error count; validate device counters", "count"),
                ("crc_errors", "CRITICAL", "High CRC error count; validate device counters", "count"),
                ("packet_loss_pct", "CRITICAL", "Severe packet loss accompanies interface errors", "%"),
            ],
            "packet_loss": [("packet_loss_pct", "HIGH", "Packet loss exceeds 5%", "%")],
            "latency_spike": [("latency_ms", "HIGH", "Latency is at least 150 ms", "ms")],
            "weak_wifi_signal": [
                ("rssi_dbm", "HIGH", "Weak received signal", "dBm"),
                ("snr_db", "HIGH", "Low signal-to-noise ratio", "dB"),
                ("retransmissions_pct", "HIGH", "High wireless retransmissions", "%"),
            ],
            "device_overload": [
                ("cpu_pct", "HIGH", "High CPU utilization", "%"),
                ("memory_pct", "HIGH", "High memory utilization", "%"),
            ],
        }.get(candidate, [])
        existing = {item.metric for item in diagnostic}
        for key, severity, interpretation, unit in direct:
            value = t.get(key)
            if value is not None and key not in existing:
                diagnostic.append(evidence_item(key, value, severity, interpretation, unit))
                existing.add(key)

    if candidate and not diagnostic:
        notes.append("Fault threshold matched, but no supporting evidence was available.")
        candidate = None

    confidence = score(diagnostic, 0.25 if conflicts and not arbitration else 0, 0, not bool(candidate))
    if candidate and confidence < 0.2:
        notes.append("Insufficient convergent support")
        candidate, confidence = None, 0.0

    # Healthy is device-aware: do not require Wi-Fi/DHCP/DNS metrics from a switch,
    # or switch CPU/queue metrics from an access point. Unknown required values stay inconclusive.
    device_id = str(t.get("device_id", "")).upper()
    is_wireless = "AP_" in device_id or any(t.get(k) is not None for k in ("rssi_dbm", "snr_db", "retransmissions_pct"))
    if is_wireless:
        required = ("rssi_dbm", "snr_db", "retransmissions_pct")
        complete = all(t.get(k) is not None for k in required)
        healthy_thresholds = (
            complete and t["rssi_dbm"] >= -75 and t["snr_db"] >= 15
            and t["retransmissions_pct"] <= 20
        )
    else:
        required = ("link_utilization_pct", "latency_ms", "packet_loss_pct", "queue_drops")
        complete = all(t.get(k) is not None for k in required)
        healthy_thresholds = (
            complete and t["link_utilization_pct"] < 85 and t["latency_ms"] < 150
            and t["packet_loss_pct"] < 3 and t["queue_drops"] <= 20
            and (cpu is None or cpu < 90) and (memory is None or memory < 90)
            and (interface_errors is None or interface_errors < 100)
            and (crc_errors is None or crc_errors < 100)
        )

    ignored_metadata = {
        "Missing site", "Missing parent_id", "Missing timestamp; temporal correlation limited",
        "Input status is an external label, not diagnostic evidence",
    }
    blocking_warnings = [
        w for w in warnings
        if w not in ignored_metadata
        and not str(w).startswith("Unrecognized telemetry key: interface_errors")
    ]
    healthy = bool(not candidate and healthy_thresholds and not blocking_warnings)
    if healthy:
        notes.append("No anomaly detected across the available device-appropriate telemetry.")
    elif not candidate:
        notes.append("Available telemetry does not support a confident root cause or a complete healthy assessment.")

    alternatives = [x for x in PRIORITY if x != candidate and x in hypotheses]
    if candidate == "link_congestion":
        alternatives.extend(x for x in ("packet_loss", "latency_spike") if x not in alternatives)
    if candidate == "physical_interface_fault":
        alternatives.extend(x for x in ("packet_loss", "link_congestion") if x not in alternatives)

    return {
        "healthy": healthy,
        "cause": candidate,
        "confidence": confidence if candidate else 0.0,
        "evidence": diagnostic if candidate else evidence,
        "alternatives": list(dict.fromkeys(alternatives)),
        "conflicts": conflicts,
        "resolution_notes": notes,
        "inconclusive": not bool(candidate) and not healthy,
        "warnings": warnings,
    }
