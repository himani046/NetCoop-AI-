"""CLI for individual and batch NetCoop AI incident diagnosis."""
import argparse
import csv
import json
import sys
from pathlib import Path
from src.graph.workflow import diagnose
from src.utils.synthetic_data import scenarios
from src.database.session import session_factory
from src.database.repository import save_incident, list_incidents, get_incident

def read_batch(path: Path) -> list:
    if path.suffix.lower() == ".csv":
        with path.open(encoding="utf-8-sig", newline="") as handle:
            records = list(csv.DictReader(handle))
    elif path.suffix.lower() in (".json", ".jsonl"):
        with path.open(encoding="utf-8") as handle:
            if path.suffix.lower() == ".jsonl":
                records = [json.loads(line) for line in handle if line.strip()]
            else:
                data = json.load(handle)
                records = data.get("records") if isinstance(data, dict) else data
    else:
        raise ValueError("Batch file must be CSV, JSON array or JSONL")
    if not isinstance(records, list):
        raise ValueError("Batch JSON must be an array or an object with a 'records' array")
    if not records:
        raise ValueError("Batch contains no telemetry records")
    return records

def run_batch(path: Path, db_path: Path | None = None) -> dict:
    records = read_batch(path)
    results = []
    factory = session_factory(db_path) if db_path else None
    for index, record in enumerate(records, start=1):
        incident_id = f"INC-BATCH-{index:05d}"
        if not isinstance(record, dict):
            results.append({"incident_id":incident_id,"status":"error",
                            "error":"Record must be a JSON object"})
            continue
        try:
            state = diagnose(record, incident_id)
            if factory:
                with factory() as session:
                    saved_pk = save_incident(session, record, state)
            else:
                saved_pk = None
            results.append({"incident_id":incident_id,
                            "database_id":saved_pk,
                            "device_id":state["normalized_telemetry"].get("device_id"),
                            "report":state["final_report"],
                            "warnings":state.get("warnings",[]),
                            "agent_messages":state.get("messages",[])})
        except Exception as exc:
            results.append({"incident_id":incident_id,"status":"error",
                            "error":f"{type(exc).__name__}: {exc}"})
    return {"total":len(records),
            "diagnosed":sum(r.get("report",{}).get("status")=="diagnosed" for r in results),
            "inconclusive":sum(r.get("report",{}).get("status")=="inconclusive" for r in results),
            "errors":sum(r.get("status")=="error" for r in results),
            "results":results}

def main() -> int:
    p=argparse.ArgumentParser(description="NetCoop AI network incident diagnosis")
    group=p.add_mutually_exclusive_group()
    group.add_argument("--scenario",choices=list(scenarios()))
    group.add_argument("--file",type=Path)
    group.add_argument("--batch",type=Path,help="CSV, JSON array or JSONL telemetry")
    p.add_argument("--incident-id",default="INC-DEMO")
    p.add_argument("--output",type=Path)
    p.add_argument("--db",type=Path,help="SQLite database path: enables persistence")
    p.add_argument("--history",action="store_true",help="List recent stored incidents")
    p.add_argument("--show-incident",type=int,help="Read a stored incident by database ID")
    args=p.parse_args()
    try:
        if args.history or args.show_incident is not None:
            factory=session_factory(args.db)
            with factory() as session:
                output=list_incidents(session) if args.history else get_incident(session,args.show_incident)
            if output is None:
                raise ValueError("Stored incident not found")
        elif args.batch:
            output=run_batch(args.batch,args.db)
        else:
            raw=json.loads(args.file.read_text(encoding="utf-8")) if args.file else scenarios()[args.scenario or "link_congestion"]
            if not isinstance(raw,dict):
                raise ValueError("Single-incident telemetry must be a JSON object")
            state=diagnose(raw,args.incident_id)
            pk=None
            if args.db:
                with session_factory(args.db)() as session:
                    pk=save_incident(session,raw,state)
            output={"database_id":pk,"report":state["final_report"],"messages":state["messages"]}
        result=json.dumps(output,indent=2,default=str)
        if args.output:
            args.output.parent.mkdir(parents=True,exist_ok=True)
            args.output.write_text(result+"\n",encoding="utf-8")
        print(result)
        return 0 if not isinstance(output,dict) or output.get("errors",0)==0 else 1
    except (OSError,ValueError,json.JSONDecodeError) as exc:
        print(f"Input error: {exc}",file=sys.stderr)
        return 2

if __name__=="__main__":
    sys.exit(main())
