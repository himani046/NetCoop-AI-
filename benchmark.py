"""Reproducible synthetic diagnostic benchmark (not real-world accuracy)."""
import argparse
import json
import random
import statistics
import time
from collections import Counter
from pathlib import Path

from src.graph.workflow import diagnose
from src.utils.synthetic_data import scenarios

LABELS = {
    "normal_operation": "normal",
    "link_congestion": "link_congestion",
    "weak_wifi_signal": "weak_wifi_signal",
    "interface_fault": "physical_interface_fault",
    "dhcp_dns_failure": "dhcp_failure",
}
PERTURBATIONS = {
    "link_utilization_pct": 3.0,
    "latency_ms": 12.0,
    "packet_loss_pct": 1.0,
    "queue_drops": 9.0,
    "crc_errors": 40.0,
    "rssi_dbm": 2.0,
    "snr_db": 2.0,
    "retransmissions_pct": 2.0,
    "dhcp_timeout_pct": 3.0,
    "gateway_ping_ms": 0.2,
    "cpu_pct": 3.0,
    "dns_latency_ms": 5.0,
}
NONNEGATIVE = set(PERTURBATIONS) - {"rssi_dbm"}

def make_dataset(per_class=20, seed=42):
    """Create labeled samples from existing fixtures with small seeded noise."""
    if per_class < 1:
        raise ValueError("per_class must be positive")
    rng = random.Random(seed)
    fixtures = scenarios()
    records = []
    for name, label in LABELS.items():
        for index in range(per_class):
            sample = dict(fixtures[name])
            for metric, amount in PERTURBATIONS.items():
                if metric in sample:
                    new = sample[metric] + rng.uniform(-amount, amount)
                    sample[metric] = round(max(0, new) if metric in NONNEGATIVE else new, 3)
            sample["device_id"] = f"BENCH_{name.upper()}_{index:04d}"
            records.append({"id": f"{name}-{index:04d}", "expected": label, "telemetry": sample})
    # Explicit abstention cases measure safe refusal to guess.
    for index in range(per_class):
        records.append({"id": f"insufficient-{index:04d}", "expected": "inconclusive",
                        "telemetry": {"device_id": f"BENCH_UNKNOWN_{index:04d}",
                                      "latency_ms": rng.uniform(10, 300)}})
    rng.shuffle(records)
    return records

def classification_metrics(rows):
    labels = sorted({x["expected"] for x in rows} | {x["predicted"] for x in rows})
    metrics = {}
    for label in labels:
        tp = sum(x["expected"] == label and x["predicted"] == label for x in rows)
        fp = sum(x["expected"] != label and x["predicted"] == label for x in rows)
        fn = sum(x["expected"] == label and x["predicted"] != label for x in rows)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        metrics[label] = {"support": sum(x["expected"] == label for x in rows),
                          "precision": round(precision, 4), "recall": round(recall, 4),
                          "f1": round(f1, 4)}
    return {
        "total": len(rows),
        "accuracy": round(sum(x["expected"] == x["predicted"] for x in rows) / len(rows), 4),
        "macro_f1": round(statistics.mean(x["f1"] for x in metrics.values()), 4),
        "abstention_rate": round(sum(x["predicted"] == "inconclusive" for x in rows) / len(rows), 4),
        "per_class": metrics,
        "confusion": {label: dict(Counter(x["predicted"] for x in rows if x["expected"] == label)) for label in labels},
    }

def evaluate(records):
    if not records:
        raise ValueError("Cannot evaluate an empty benchmark")
    rows = []
    for sample in records:
        start = time.perf_counter()
        try:
            state = diagnose(sample["telemetry"], sample["id"])
            report = state["final_report"]
            predicted = report["suspected_root_cause"] if report["status"] == "diagnosed" else "inconclusive"
            # Normal operation is a valid no-fault outcome, rather than an incorrect abstention.
            if predicted == "inconclusive" and not any(
                finding.get("primary_hypothesis") for finding in
                (state["tpa_finding"], state["iha_finding"], state["cta_finding"])
            ):
                predicted = "normal"
            error = None
        except Exception as exc:
            predicted = "error"
            error = type(exc).__name__
        rows.append({"id": sample["id"], "expected": sample["expected"],
                     "predicted": predicted, "latency_ms": round((time.perf_counter()-start)*1000,2),
                     "error": error})
    summary = classification_metrics(rows)
    durations = [x["latency_ms"] for x in rows]
    summary.update({"mean_latency_ms": round(statistics.mean(durations),2),
                    "p95_latency_ms": round(sorted(durations)[min(len(durations)-1,int(0.95*len(durations)))],2),
                    "misclassified": [x for x in rows if x["expected"] != x["predicted"]],
                    "rows": rows,
                    "methodology": "Seeded perturbations of existing synthetic fixtures, with known generator labels; not independent or real-world validation.",
                    "ai_used": False})
    return summary

def main():
    parser = argparse.ArgumentParser(description="Offline synthetic NetCoop benchmark")
    parser.add_argument("--per-class", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("reports/benchmark.json"))
    args = parser.parse_args()
    import os
    os.environ.pop("NETCOOP_LLM_MODEL", None)
    report = evaluate(make_dataset(args.per_class, args.seed))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in ("rows","misclassified")},indent=2))
    print(f"Saved full benchmark to {args.output}")

if __name__ == "__main__":
    main()
