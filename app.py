"""NetCoop AI operator console. Campus geography is reference-only, not live monitoring."""
import json
import uuid
from datetime import datetime, timezone

import pandas as pd
import pydeck as pdk
import streamlit as st

from src.graph.workflow import diagnose
from src.utils.synthetic_data import scenarios
from src.database.session import session_factory
from src.database.repository import save_incident, list_incidents, get_incident

st.set_page_config(page_title="NetCoop | Network operations", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');
:root{--ink:#102337;--sub:#617184;--cyan:#007d87;--border:#e3e8ef}
html,body,[class*="css"],[data-testid="stApp"]{font-family:'DM Sans',sans-serif}
[data-testid="stApp"]{background:#f5f7f9;color:#102337}
[data-testid="stSidebar"]{background:#10283c}
[data-testid="stSidebar"] *{color:#f2f7f8!important}
[data-testid="stSidebar"] [role="radiogroup"] label{padding:10px 12px;border-radius:8px}
.block-container{padding-top:1.8rem;max-width:1450px;padding-bottom:4rem}
h1,h2,h3{letter-spacing:-.035em}
h1{font-weight:750!important;font-size:2rem!important}
h2{font-weight:700!important;font-size:1.33rem!important}
[data-testid="stMetric"]{background:#fff;border:1px solid #e1e8ee;border-radius:12px;padding:14px 17px;box-shadow:0 3px 14px rgba(14,30,44,.025)}
[data-testid="stMetricValue"]{font-weight:700}
div.stButton>button[kind="primary"]{background:#007e86;border:0;border-radius:9px}
div.stButton>button{border-radius:9px}
.nc-eyebrow{font:600 11px 'IBM Plex Mono',monospace;letter-spacing:.13em;color:#007e86;text-transform:uppercase;margin-bottom:.4rem}
.nc-panel{background:#fff;border:1px solid #e1e8ee;border-radius:12px;padding:20px;margin:8px 0 16px}
.nc-sub{color:#627487;font-size:.90rem}
.nc-kicker{font:600 12px 'IBM Plex Mono',monospace;color:#66788b;text-transform:uppercase;letter-spacing:.06em}
.nc-status{display:inline-block;padding:5px 10px;border-radius:7px;font:600 11px 'IBM Plex Mono',monospace}
.nc-diagnosed{color:#a83c2f;background:#fbe8e4}
.nc-healthy{color:#126b4e;background:#dff4ea}
.nc-inconclusive{color:#9a6717;background:#fff0cf}
.nc-mono{font-family:'IBM Plex Mono',monospace;font-size:13px}
[data-testid="stAlert"]{border-radius:10px}
hr{border-color:#e2e8ee}
</style>
""", unsafe_allow_html=True)

SCENARIOS = scenarios()
SCENARIO_LABELS = {
    "normal_operation": "Normal operation",
    "link_congestion": "Link congestion",
    "weak_wifi_signal": "Weak Wi-Fi signal",
    "interface_fault": "Physical interface fault",
    "dhcp_dns_failure": "DHCP / DNS service failure",
    "malformed_and_missing_data": "Incomplete telemetry",
}
CAUSE_LABELS = {
    "link_congestion": "Link congestion",
    "physical_interface_fault": "Physical interface fault",
    "weak_wifi_signal": "Weak Wi-Fi signal",
    "dhcp_failure": "DHCP service failure",
    "dns_failure": "DNS service failure",
    "device_overload": "Device overload",
}
METRIC_LABELS = {
    "link_utilization_pct": ("Link utilization", "%"),
    "latency_ms": ("Network latency", "ms"),
    "packet_loss_pct": ("Packet loss", "%"),
    "queue_drops": ("Queue drops", ""),
    "crc_errors": ("CRC errors", ""),
    "rssi_dbm": ("Wi-Fi signal (RSSI)", "dBm"),
    "snr_db": ("Signal-to-noise ratio", "dB"),
    "retransmissions_pct": ("Wi-Fi retries", "%"),
    "dhcp_timeout_pct": ("DHCP timeout rate", "%"),
    "dns_latency_ms": ("DNS latency", "ms"),
    "cpu_pct": ("CPU utilization", "%"),
    "memory_pct": ("Memory utilization", "%"),
}
AGENT_LABELS = {
    "performance_agent": "Performance",
    "infrastructure_agent": "Infrastructure",
    "connectivity_agent": "Connectivity",
    "correlation_agent": "Correlation",
    "reporting_agent": "Reporting",
}
# Grounded OpenStreetMap campus places, reference markers only, no device associations.
CAMPUS_PLACES = [
    {"name": "IIT Bhubaneswar campus", "lat": 20.14797, "lon": 85.67007},
    {"name": "Main Building", "lat": 20.14827, "lon": 85.67108},
    {"name": "Lalitgiri Lecture Hall", "lat": 20.14684, "lon": 85.67411},
    {"name": "Pushpagiri Lecture Hall", "lat": 20.14640, "lon": 85.67558},
    {"name": "Lab Complex", "lat": 20.14819, "lon": 85.67761},
    {"name": "IIT SHSSM", "lat": 20.14591, "lon": 85.67773},
]
PLACE_SOURCES = "https://www.openstreetmap.org/#map=16/20.14797/85.67007"


def heading(eyebrow, title, sub=None):
    st.markdown(f'<div class="nc-eyebrow">{eyebrow}</div>', unsafe_allow_html=True)
    st.title(title)
    if sub:
        st.caption(sub)


def status_html(status):
    safe = status if status in ("healthy", "diagnosed", "inconclusive") else "inconclusive"
    return f'<span class="nc-status nc-{safe}">{safe.upper()}</span>'


def nice_cause(cause):
    return CAUSE_LABELS.get(cause, (cause or "Insufficient evidence").replace("_", " ").title())


def report_brief(report):
    st.markdown(status_html(report["status"]), unsafe_allow_html=True)
    st.markdown("### " + nice_cause(report["suspected_root_cause"]))
    st.caption(" · ".join(report.get("affected_devices", [])) or "Affected device not specified")
    if report["status"] == "healthy":
        st.success("No anomaly detected in the evaluated telemetry snapshot.")
    elif report["status"] == "inconclusive":
        st.warning("Evidence is insufficient for a reliable diagnosis.")
    else:
        st.error("Fault detected in simulated network telemetry. Operator review recommended.")


def report_detail(report):
    report_brief(report)
    st.divider()
    a,b,c = st.columns(3)
    a.metric("Fault evidence support", f'{report["confidence"]:.1%}')
    b.metric("Affected devices", len(report.get("affected_devices", [])))
    c.metric("Evidence measurements", len(report.get("supporting_evidence", [])))
    st.caption("Evidence support is a heuristic fault score, not a calibrated probability. For healthy cases, 0% means no fault evidence.")
    l,r = st.columns([1.3,1], gap="large")
    with l:
        st.subheader("Evidence")
        ev = report.get("supporting_evidence", [])
        if ev:
            for e in ev:
                label,unit = METRIC_LABELS.get(e["metric"], (e["metric"].replace("_"," ").title(),""))
                st.markdown(f'<div class="nc-panel"><div class="nc-kicker">{label}</div><b>{e["value"]} {unit}</b><div class="nc-sub">{e["interpretation"]}</div></div>', unsafe_allow_html=True)
        else:
            st.info("No fault-triggering measurements in this report.")
    with r:
        st.subheader("Operator actions")
        for i,action in enumerate(report.get("recommended_actions", []), 1):
            st.markdown(f"**{i:02}.** {action}")
        st.subheader("Limits & uncertainty")
        for item in report.get("limitations", []):
            st.caption("• " + item)
        if report.get("alternative_causes"):
            st.subheader("Alternative explanations")
            for item in report["alternative_causes"]:
                st.write("• " + nice_cause(item))


def agent_activity(state):
    st.subheader("Agent collaboration")
    st.caption("Three specialists investigate in parallel, then Correlation resolves evidence and Reporting prepares the operator decision.")
    findings = [(key,name) for key,name in [
        ("tpa_finding","Performance"),("iha_finding","Infrastructure"),("cta_finding","Connectivity")
    ]]
    cols = st.columns(3)
    for col,(key,name) in zip(cols,findings):
        f = state.get(key) or {}
        with col:
            st.markdown(f'<div class="nc-panel"><div class="nc-kicker">{name} agent</div><b>{str(f.get("status","—")).replace("_"," ").title()}</b><div class="nc-sub">{nice_cause(f.get("primary_hypothesis")) if f.get("primary_hypothesis") else "No domain-specific fault hypothesis"}</div></div>',unsafe_allow_html=True)
    st.markdown("**↓ Evidence correlated → Final operator report**")
    reviews = {x["agent_id"]:x for x in state.get("gemini_agent_reviews",[])}
    rows=[]
    for fkey,name in findings:
        f=state.get(fkey) or {}
        aid=f.get("agent_id")
        rv=reviews.get(aid,{})
        rows.append({"Agent":name,"Finding":str(f.get("status","unknown")).replace("_"," ").title(),
                     "Hypothesis":nice_cause(f["primary_hypothesis"]) if f.get("primary_hypothesis") else "None",
                     "Gemini review":"Completed" if rv.get("review") else ("Disabled / unavailable" if rv else "Not requested")})
    rows += [
        {"Agent":"Correlation","Finding":nice_cause(state.get("decision",{}).get("cause")) if state.get("decision",{}).get("cause") else "No fault selected","Hypothesis":"Evidence arbitration","Gemini review":"Completed" if state.get("decision",{}).get("ai_review") else "Unavailable / disabled"},
        {"Agent":"Reporting","Finding":state["final_report"]["status"].title(),"Hypothesis":"Operator summary","Gemini review":"Completed" if state.get("gemini_report_review") else "Unavailable / disabled"},
    ]
    st.dataframe(rows,use_container_width=True,hide_index=True)
    if state.get("decision",{}).get("conflicts"):
        st.warning("Competing findings: "+", ".join(state["decision"]["conflicts"]))


def latest_report_from_history(history):
    if history:
        with session_factory(st.session_state["db_path"])() as session:
            found = get_incident(session,int(history[0]["id"]))
        return found["report"] if found else None
    return None


with st.sidebar:
    st.markdown("## ◈ NETCOOP")
    st.caption("NETWORK OPERATIONS / IITBBS")
    page = st.radio("WORKSPACE", ["Overview","Run diagnosis","Campus map","Technical records"],label_visibility="collapsed")
    st.divider()
    st.caption("DATA SOURCE")
    st.markdown("**Synthetic / test telemetry**")
    st.caption("No production campus network access")
    st.divider()
    st.caption("ACP 1.2.0 · LANGGRAPH · GEMINI")
    st.session_state["db_path"] = st.text_input("SQLite database", st.session_state.get("db_path","data/netcoop.db"))

db_path=st.session_state["db_path"]
history=[]
history_error=None
try:
    with session_factory(db_path)() as session:
        history=list_incidents(session,100)
except Exception as exc:
    history_error=f"{type(exc).__name__}: {exc}"

state=st.session_state.get("diagnostic_state")
report=state["final_report"] if state else latest_report_from_history(history)

if page=="Overview":
    heading("OPERATIONS / OVERVIEW","Campus network diagnostics",
            "A concise view of the latest evaluated incident. All results are based on supplied test data.")
    if history_error:
        st.warning("Incident history unavailable: "+history_error)
    m1,m2,m3,m4=st.columns(4)
    m1.metric("Saved diagnostic runs",len(history))
    m2.metric("Latest status",report["status"].upper() if report else "NO RUN")
    m3.metric("Fault support",f'{report["confidence"]:.1%}' if report else "—")
    m4.metric("Active live monitors","0")
    st.caption("Live monitoring is not connected. Saved results are historical synthetic diagnostic runs.")
    if report:
        st.subheader("Latest diagnosis")
        report_detail(report)
    else:
        st.info("No diagnosis yet. Use Run diagnosis to evaluate a sample or supply telemetry.")
    if history:
        st.subheader("Recent incidents")
        st.dataframe(history[:8],use_container_width=True,hide_index=True)
    st.button("Run a new diagnosis →",on_click=lambda:st.session_state.update({"open_diagnose":True}))
    if st.session_state.pop("open_diagnose",False):
        st.info("Select 'Run diagnosis' in the left navigation.")

elif page=="Run diagnosis":
    heading("WORKSPACE / DIAGNOSIS","Run a network diagnosis",
            "Select a reproducible test case, or paste telemetry. The evidence-first agents always run even when Gemini is unavailable.")
    left,right=st.columns([1,1.15],gap="large")
    with left:
        scenario=st.selectbox("Test scenario",list(SCENARIOS),format_func=lambda k:SCENARIO_LABELS.get(k,k))
        raw=st.text_area("Telemetry input (JSON)",value=json.dumps(SCENARIOS[scenario],indent=2),height=300,key="payload_"+scenario)
        save=st.checkbox("Save incident to SQLite",value=True)
        if st.button("Run five-agent diagnosis",type="primary",use_container_width=True):
            try:
                payload=json.loads(raw)
                if not isinstance(payload,dict):
                    st.error("Telemetry must be a JSON object.")
                else:
                    with st.spinner("Analyzing telemetry · coordinating agents"):
                        result=diagnose(payload,incident_id="INC-"+uuid.uuid4().hex[:8].upper())
                    st.session_state["diagnostic_state"]=result
                    if save:
                        try:
                            with session_factory(db_path)() as session:
                                save_incident(session,payload,result)
                        except Exception as exc:
                            st.warning(f"Diagnosis succeeded; persistence failed ({type(exc).__name__}).")
                    st.rerun()
            except (ValueError,TypeError) as exc:
                st.error(f"Invalid telemetry input: {exc}")
            except Exception as exc:
                st.error(f"Diagnosis failed: {type(exc).__name__}: {exc}")
    with right:
        if state:
            st.markdown('<div class="nc-eyebrow">LATEST ANALYSIS</div>',unsafe_allow_html=True)
            report_brief(state["final_report"])
            st.metric("Fault evidence support",f'{state["final_report"]["confidence"]:.1%}')
            st.caption("Heuristic fault-evidence score · not calibrated correctness probability")
            for a in state["final_report"].get("recommended_actions",[]):
                st.markdown("✓ "+a)
            if state.get("warnings"):
                st.warning("Input quality: "+"; ".join(state["warnings"]))
        else:
            st.markdown('<div class="nc-panel"><div class="nc-kicker">Ready to analyze</div><h3>Five specialized roles. One evidence-backed decision.</h3><p class="nc-sub">Performance · Infrastructure · Connectivity → Correlation → Reporting</p></div>',unsafe_allow_html=True)
    if state:
        st.divider()
        report_detail(state["final_report"])
        agent_activity(state)
        if state.get("gemini_report_review"):
            with st.expander("Operator explanation from Gemini"):
                rv=state["gemini_report_review"]
                st.write(rv.get("operator_summary",""))
                st.write(rv.get("explanation_of_actions",""))
                for c in rv.get("caveats",[]):st.caption("• "+c)
        st.download_button("Download diagnostic report",json.dumps(state["final_report"],indent=2),
                           file_name="netcoop-incident.json",mime="application/json")

elif page=="Campus map":
    heading("CAMPUS / GEOGRAPHY","IIT Bhubaneswar campus map",
            "OpenStreetMap basemap · Argul permanent campus · Verified points of interest")
    st.info("Reference geography only — this app has no live campus telemetry feed or verified device-to-building mapping. A red incident marker is shown only for a device with a supplied, validated location.")
    # Explicit mapping, rather than inferring physical position from device names.
    # An operator may explicitly assign a test device to a known POI for demonstration.
    mapping = st.session_state.setdefault("demo_device_locations", {})
    if report and report.get("affected_devices"):
        with st.expander("Assign a test device to a campus location (demo only)"):
            incident_device = st.selectbox("Device", report["affected_devices"], key="map_device")
            selected_place = st.selectbox("Campus place", ["Not mapped"]+[p["name"] for p in CAMPUS_PLACES], key="map_place")
            if st.button("Apply demo location"):
                if selected_place=="Not mapped":
                    mapping.pop(incident_device,None)
                else:
                    mapping[incident_device]=selected_place
                st.rerun()
            st.caption("This is a manual demonstration assignment, not a discovered network link or verified installed-device position.")
    places=[{**p,"color":[0,126,134,200],"radius":65,"state":"Reference location"} for p in CAMPUS_PLACES]
    affected = report.get("affected_devices",[]) if report else []
    matched = [d for d in affected if mapping.get(d) in {p["name"] for p in places}]
    if matched and report["status"]=="diagnosed":
        for place in places:
            devices=[d for d in matched if mapping[d]==place["name"]]
            if devices:
                place["color"]=[211,48,53,230]
                place["radius"]=110
                place["state"]="⚠ SIMULATED FAULT · "+", ".join(devices)
    elif matched and report["status"]=="healthy":
        for place in places:
            if any(mapping[d]==place["name"] for d in matched):
                place["color"]=[15,139,99,220]
                place["state"]="Healthy in latest simulated test"
    alert_places = [{**p, "alert_symbol":"⚠"} for p in places if p["state"].startswith("⚠")]
    st.pydeck_chart(pdk.Deck(
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        initial_view_state=pdk.ViewState(latitude=20.1472,longitude=85.6735,zoom=15.25,pitch=0),
        layers=[
            pdk.Layer("ScatterplotLayer",data=places,get_position="[lon, lat]",
                      get_fill_color="color",get_radius="radius",pickable=True,radius_min_pixels=7),
            pdk.Layer("TextLayer",data=alert_places,get_position="[lon, lat]",get_text="alert_symbol",
                      get_size=19,get_color=[255,255,255],get_pixel_offset=[0,0],
                      get_text_anchor="'middle'",pickable=False),
            pdk.Layer("TextLayer",data=places,get_position="[lon, lat]",get_text="name",
                      get_size=13,get_color=[14,45,61],get_pixel_offset=[0,16],
                      get_text_anchor="'middle'",get_alignment_baseline="'top'",pickable=True),
        ],
        tooltip={"text":"{name} · {state}"}
    ),use_container_width=True)
    st.caption("Map and named places: © OpenStreetMap contributors. Marker positions are reference POIs, not network equipment coordinates.")
    st.link_button("Open full campus map",PLACE_SOURCES)
    st.subheader("Incident location & connectivity")
    if report:
        if report["status"]=="diagnosed":
            if matched:
                st.error("⚠ Simulated fault markers shown in red at manually assigned demonstration locations.")
            else:
                st.error(f"⚠ Simulated fault detected at {', '.join(report['affected_devices'])}. Physical campus position is not registered; no red pin is placed arbitrarily.")
        elif report["status"]=="healthy":
            st.success("The latest evaluated telemetry snapshot reported no detected fault. Other campus locations have not been tested.")
        else:
            st.warning("Latest evidence insufficient to determine network health.")
        st.markdown("**Devices from latest diagnosis**")
        for device in report["affected_devices"]:
            st.markdown(f"• `{device}` — location not geocoded; **{report['status']}** in latest test")
    st.caption("Campus buildings do not imply verified network links. Register surveyed coordinates and authorized live telemetry to enable accurate location-level alerts.")

elif page=="Technical records":
    heading("ENGINEERING / AUDIT","Technical records",
            "Structured JSON, ACP envelopes, normalized telemetry, validation warnings and saved reports.")
    if history_error:st.warning("Database history unavailable: "+history_error)
    if state:
        st.subheader("Current diagnostic run")
        options=["Final report","Normalized telemetry","Agent messages","Correlation & arbitration","Gemini reviews"]
        selected=st.selectbox("Inspect record",options)
        doc={
            "Final report":state["final_report"],
            "Normalized telemetry":state.get("normalized_telemetry",{}),
            "Agent messages":state.get("messages",[]),
            "Correlation & arbitration":state.get("decision",{}),
            "Gemini reviews":{"specialists":state.get("gemini_agent_reviews",[]),
                              "reporting":state.get("gemini_report_review")},
        }[selected]
        st.json(doc)
        st.download_button("Download JSON",json.dumps(doc,indent=2,default=str),
                           file_name="netcoop-technical.json",mime="application/json")
    if history:
        st.subheader("Stored incident history")
        st.dataframe(history,use_container_width=True,hide_index=True)
        pk=st.selectbox("Inspect saved incident",[x["id"] for x in history],
                        format_func=lambda v:f"Incident record #{v}")
        with session_factory(db_path)() as session:
            stored=get_incident(session,int(pk))
        if stored:
            tab1,tab2=st.tabs(["Diagnostic report JSON","ACP message log"])
            with tab1:st.json(stored["report"])
            with tab2:st.json(stored["messages"])
    if not state and not history:
        st.info("No technical records yet. Run a diagnosis first.")
