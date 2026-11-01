from src.protocol.models import FinalDiagnosticReport, ReportEvidence

RUNBOOKS = {
    "link_congestion": [
        "Inspect upstream and egress utilization",
        "Review queue configuration and traffic distribution",
        "Plan a capacity upgrade if saturation persists",
    ],
    "physical_interface_fault": [
        "Validate interface/CRC counter definitions and counter deltas",
        "Inspect cable, transceiver, duplex settings, and interface health",
        "Retest under controlled traffic before replacing hardware",
    ],
    "weak_wifi_signal": [
        "Survey RF interference and client location",
        "Adjust channel or transmit power under change control",
        "Inspect client RSSI, SNR, and retry trends",
    ],
    "dhcp_failure": [
        "Check DHCP and relay reachability",
        "Inspect pool exhaustion and logs",
        "Validate discovery and lease exchange",
    ],
    "dns_failure": [
        "Test configured resolvers",
        "Inspect DNS forwarding and firewall rules",
        "Validate resolver availability",
    ],
    "device_overload": [
        "Inspect CPU and forwarding queues",
        "Rebalance traffic load",
        "Review platform capacity",
    ],
    "packet_loss": [
        "Check packet-loss trends across the affected path",
        "Compare interface counters and upstream/downstream loss",
        "Inspect link quality and routing before changing configuration",
    ],
    "latency_spike": [
        "Compare latency and jitter across the path",
        "Check congestion, queueing, and upstream latency",
        "Capture repeat measurements to determine whether the spike persists",
    ],
}


def report(incident_id, t, findings, decision) -> FinalDiagnosticReport:
    cause = decision["cause"]
    devices = sorted({d for f in findings for d in f.affected_components})
    limitations = list(dict.fromkeys([*decision["resolution_notes"], *decision["warnings"]]))
    if not cause and not decision.get("healthy"):
        limitations.insert(0, "Available evidence cannot establish a reliable root cause")
    sources = list(dict.fromkeys(
        f.agent_id for f in findings if f.supporting_evidence or decision.get("healthy")
    ))
    return FinalDiagnosticReport(
        incident_id=incident_id,
        status="diagnosed" if cause else ("healthy" if decision.get("healthy") else "inconclusive"),
        suspected_root_cause=cause or (
            "No network fault detected" if decision.get("healthy")
            else "Insufficient evidence to determine root cause"
        ),
        confidence=decision["confidence"] if cause else 0.0,
        affected_devices=devices,
        supporting_evidence=[
            ReportEvidence(metric=x.metric, value=x.observed_value, interpretation=x.interpretation)
            for x in decision["evidence"]
        ],
        alternative_causes=decision["alternatives"],
        recommended_actions=RUNBOOKS.get(
            cause,
            ["Continue routine network monitoring"] if decision.get("healthy")
            else ["Collect additional telemetry and confirm topology",
                  "Inspect the affected device or link before changes"],
        ),
        evidence_sources=sources,
        limitations=limitations,
    )


def markdown_report(r: FinalDiagnosticReport) -> str:
    lines = [
        f"# Network Incident {r.incident_id}",
        f"**Status:** {r.status}",
        f"**Suspected root cause:** {r.suspected_root_cause}",
        f"**Diagnostic support score:** {r.confidence:.2f} (heuristic)",
        f'**Affected devices:** {", ".join(r.affected_devices) or "Unknown"}',
        "## Supporting evidence",
    ]
    lines += [
        f"- {x.metric}: {x.value} — {x.interpretation}" for x in r.supporting_evidence
    ] or ["- No sufficient evidence"]
    lines += ["## Alternative explanations"] + [f"- {x}" for x in r.alternative_causes]
    lines += ["## Corrective actions"] + [
        f"{i}. {x}" for i, x in enumerate(r.recommended_actions, 1)
    ]
    lines += ["## Limitations"] + [f"- {x}" for x in r.limitations]
    return "\n".join(lines)
