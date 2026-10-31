"""CLI: diagnose synthetic scenarios or a JSON file."""
import argparse,json
from pathlib import Path
from src.graph.workflow import diagnose
from src.utils.synthetic_data import scenarios
def main():
 p=argparse.ArgumentParser(description="NetCoop AI network incident diagnosis")
 p.add_argument("--scenario",choices=list(scenarios()),default="link_congestion")
 p.add_argument("--file",type=Path)
 p.add_argument("--incident-id",default="INC-DEMO")
 p.add_argument("--output",type=Path)
 args=p.parse_args()
 raw=json.loads(args.file.read_text(encoding="utf-8")) if args.file else scenarios()[args.scenario]
 state=diagnose(raw,args.incident_id)
 result=json.dumps(state["final_report"],indent=2)
 if args.output: args.output.write_text(result+"\n",encoding="utf-8")
 print(result)
 print("\n--- AGENT MESSAGE LOG ---")
 print(json.dumps(state["messages"],indent=2))
if __name__=="__main__": main()
