"""Streamlit dashboard for NetCoop AI diagnostics."""
import json,uuid
import streamlit as st
from src.graph.workflow import diagnose
from src.utils.synthetic_data import scenarios
st.set_page_config(page_title="NetCoop AI",page_icon="🌐",layout="wide")
st.title("🌐 NetCoop AI · Multi-Agent Network Diagnostics")
st.caption("Evidence-first campus diagnosis · LangGraph fan-out/fan-in · ACP 1.2.0")
fixtures=scenarios()
scenario=st.selectbox("Benchmark scenario",list(fixtures))
raw=st.text_area("Edit synthetic or Colab-generated JSON",value=json.dumps(fixtures[scenario],indent=2),height=310,key=scenario)
if st.button("Run five-agent diagnosis",type="primary"):
 try:
  payload=json.loads(raw)
  if not isinstance(payload,dict):st.error("Input must be a JSON object")
  else:
   with st.spinner("Running specialists and arbitration"):
    st.session_state["diagnostic_state"]=diagnose(payload,incident_id="INC-"+uuid.uuid4().hex[:8].upper())
 except (ValueError,TypeError) as exc:st.error(f"Invalid JSON payload: {exc}")
 except Exception as exc:st.error(f"Diagnosis failed safely: {type(exc).__name__}: {exc}")
if "diagnostic_state" in st.session_state:
 state=st.session_state["diagnostic_state"];r=state["final_report"]
 a,b,c=st.columns(3)
 a.metric("Status",r["status"].upper());b.metric("Evidence support",f'{r["confidence"]:.1%}');c.metric("Agent messages",len(state["messages"]))
 st.subheader("Suspected root cause");st.info(r["suspected_root_cause"])
 st.subheader("Normalized telemetry");st.json(state["normalized_telemetry"])
 if state["warnings"]:
  with st.expander(f'Validation warnings ({len(state["warnings"])})',expanded=True):
   for warning in state["warnings"]:st.warning(warning)
 st.subheader("Agent-to-agent messages")
 for i,msg in enumerate(state["messages"],1):
  with st.expander(f'{i}. {msg["sender"]} → {msg["recipient"]}'):st.json(msg)
 st.subheader("Evidence and arbitration")
 st.json({"conflicts":state["decision"]["conflicts"],"resolution_notes":state["resolution_notes"]})
 st.subheader("Final report");st.json(r)
 st.download_button("Download incident JSON",json.dumps(r,indent=2),"incident-report.json","application/json")
 st.download_button("Download post-mortem Markdown",state["markdown_report"],"incident-postmortem.md","text/markdown")
