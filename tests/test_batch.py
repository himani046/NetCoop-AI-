import json
from pathlib import Path
from main import read_batch, run_batch

def test_batch_sample():
    path = Path(__file__).resolve().parents[1] / "data" / "colab_batch.json"
    result = run_batch(path)
    assert result["total"] == 3
    assert result["errors"] == 0
    assert result["diagnosed"] == 3
    assert len(result["results"][0]["agent_messages"]) >= 5
    assert result["results"][0]["report"]["suspected_root_cause"] == "link_congestion"

def test_batch_malformed_record(tmp_path):
    path = tmp_path / "batch.json"
    path.write_text(json.dumps([{"latency_ms": 200}, 42]))
    result = run_batch(path)
    assert result["total"] == 2
    assert result["inconclusive"] == 1
    assert result["errors"] == 1

def test_batch_csv(tmp_path):
    path = tmp_path / "telemetry.csv"
    path.write_text("device_id,link_utilization_pct,latency_ms,queue_drops\nSW1,94,280,160\n")
    result=run_batch(path)
    assert result["total"]==1 and result["diagnosed"]==1
