"use client";
import {useCallback,useEffect,useMemo,useState} from "react";
import dynamic from "next/dynamic";
import {Device,getJSON,postJSON,pretty} from "../lib/api";
import type {Region} from "./campus-scene";
import {RegionInspection} from "./region-inspection";
const Scene=dynamic(()=>import("./campus-geospatial").then(m=>m.CampusGeospatial),{ssr:false,loading:()=> <div className="campus-canvas loading-map">Preparing campus scene…</div>});
type Frame={observed_at:string;regions:Region[];device_count:number;mapped_device_count:number};
type History={frames:Frame[];excluded_undated:number;truncated_source:boolean;assignment_policy:string};
type Snapshot={live:boolean;mode:string;regions:Region[];device_assignments:{device_id:string;region_id:string}[]};
export function CampusExperience(){
 const [data,setData]=useState<Snapshot|null>(null),[devices,setDevices]=useState<Device[]>([]),[selected,setSelected]=useState<string|null>(null);
 const [building,setBuilding]=useState<{name:string;osmId:number}|null>(null);
 const [buildingNames,setBuildingNames]=useState<string[]>([]);
 const chooseBuilding=useCallback((name:string,osmId:number)=>{setBuilding({name,osmId})},[]);
 const [device,setDevice]=useState(""),[region,setRegion]=useState(""),[busy,setBusy]=useState(false),[error,setError]=useState("");
 const [history,setHistory]=useState<History|null>(null),[frameIndex,setFrameIndex]=useState(0),[historical,setHistorical]=useState(false),[playing,setPlaying]=useState(false);
 async function refresh(){const [a,b,h]=await Promise.all([getJSON<Snapshot>("/api/map/regions"),getJSON<Device[]>("/api/devices/latest"),getJSON<History>("/api/map/history")]);setData(a);setDevices(b);setHistory(h);setFrameIndex(Math.max(0,h.frames.length-1));setSelected(s=>s||a.regions[0]?.id||null)}
 useEffect(()=>{refresh().catch(e=>setError(String(e)))},[]);
 const visibleRegions=historical&&history?.frames.length?history.frames[frameIndex]?.regions:data?.regions;
 const active=useMemo(()=>visibleRegions?.find(r=>r.id===selected),[visibleRegions,selected]);
 useEffect(()=>{if(!playing||!historical||!history||history.frames.length<2)return;const timer=window.setInterval(()=>setFrameIndex(i=>(i+1)%history.frames.length),1400);return()=>window.clearInterval(timer)},[playing,historical,history]);
 async function assign(){if(!device){setError("Choose a device");return}setBusy(true);setError("");try{await postJSON("/api/map/assign",{device_id:device,region_id:region||null});await refresh()}catch(e){setError(String(e))}finally{setBusy(false)}}
 return <><header className="page-head"><div className="eyebrow">01 / CAMPUS OPERATIONS</div><h1 className="heading">A campus in context.</h1><p className="sub">An interactive 3D operations model with fault states inferred from the latest saved readings of manually assigned devices.</p></header>
 <div className="cartouche"><span>SIMULATED DATA</span><span>LOCATIONS ASSIGNED MANUALLY</span><span>NO LIVE CAMPUS MONITORING</span></div>
 <section className="spatial-playback"><div className="spatial-head"><span className="smallmono">SPATIAL PLAYBACK / RECORDED OBSERVATIONS</span><label><input type="checkbox" checked={historical} onChange={e=>{setHistorical(e.target.checked);setPlaying(false)}}/> Historical mode</label></div>{historical?<><div className="spatial-time">{history?.frames[frameIndex]?.observed_at?new Date(history.frames[frameIndex].observed_at).toLocaleString("en-GB",{timeZone:"UTC",dateStyle:"medium",timeStyle:"medium"}):"No timestamped readings"} <small>UTC</small></div><div className="spatial-controls"><button disabled={!history||history.frames.length<2} onClick={()=>setPlaying(v=>!v)}>{playing?"Pause":"Play timeline"}</button><input aria-label="Historical observation time" type="range" min={0} max={Math.max(0,(history?.frames.length||0)-1)} value={frameIndex} onChange={e=>{setPlaying(false);setFrameIndex(Number(e.target.value))}}/><span>{history?.frames.length?frameIndex+1:0} / {history?.frames.length||0}</span></div><p className="sub">The latest recorded status for each assigned device persists until its next saved observation. Unobserved devices are not assigned a health status.</p></>:<p className="sub">Current mode displays the latest saved observation per device. Enable historical mode to replay region conditions.</p>}</section>
 <div className="map-layout"><section className="map-frame">{data?<Scene regions={visibleRegions||[]} selected={selected} onSelect={setSelected} onBuilding={chooseBuilding} onCatalog={setBuildingNames} devices={devices} assignments={data.device_assignments}/>:<div className="loading-map">Loading campus reference…</div>}<div className="map-legend"><span><i className="legend-green"/>Normal</span><span><i className="legend-red"/>Fault</span><span><i className="legend-yellow"/>Unverified</span><span><i className="legend-gray"/>Unassigned</span></div></section>
 <aside className="map-inspector">{building&&<div className="osm-building-inspect"><span className="smallmono">MAPPED BUILDING · OSM #{building.osmId}</span><h3>{building.name}</h3><p className="sub">Building shape and name sourced from OpenStreetMap if mapped. No equipment is assigned to this building automatically; select a network region to inspect diagnosed devices.</p><button onClick={()=>setBuilding(null)}>Close building details</button></div>}<span className="smallmono">SELECTED NETWORK REGION</span><h2>{active?.name||"Choose a region"}</h2><p className="sub">Reference point of interest</p><div className={"region-condition "+(active?.status||"unmonitored")}>{active?.status==="fault"?"FAULT DETECTED":active?.status==="healthy"?"OBSERVED NORMAL":active?.status==="limited"?"REVIEW REQUIRED":"NO ASSIGNED DEVICES"}</div>
 <div className="inspector-count">{active?.devices.length||0}<span>assigned device(s)</span></div>
 {active?.devices.map(d=><div className="region-device" key={d.device_id}><b>{d.device_id}</b><small>{d.status==="diagnosed"?pretty(d.root_cause):d.status.toUpperCase()}</small><RegionInspection deviceId={d.device_id}/></div>)}
 <details className="campus-building-directory"><summary>Mapped campus building names ({buildingNames.length})</summary>{buildingNames.length?buildingNames.map(name=><div key={name} className="directory-name">{name}</div>):<p className="sub">No named footprints returned. Additional verified building names require OSM data.</p>}</details>
 <div className="assign-box"><div className="smallmono">DEMO DEVICE PLACEMENT</div><p className="sub">Assignment is not a claim of a real equipment installation.</p>
 <select aria-label="Device to assign" value={device} onChange={e=>setDevice(e.target.value)}><option value="">Select device</option>{devices.map(d=><option key={d.device_id} value={d.device_id}>{d.device_id}</option>)}</select>
 <select aria-label="Region to assign" value={region} onChange={e=>setRegion(e.target.value)}><option value="">Remove assignment</option>{data?.regions.map(r=><option value={r.id} key={r.id}>{r.name}</option>)}</select><button disabled={busy||!device} onClick={assign}>Apply assignment</button></div>
 </aside></div>
 {error&&<p className="error">{error}</p>}
 <div className="section-header"><h2>Region conditions</h2><span className="smallmono">{historical?"AT SELECTED OBSERVATION / UTC":"LATEST OBSERVATIONS / UTC"}</span></div>
 <div className="region-list">{visibleRegions?.map(r=><button className={"region-row "+r.status} key={r.id} onClick={()=>setSelected(r.id)}><span>{r.name}</span><span>{r.devices.length} DEVICES</span><strong>{r.status.toUpperCase()}</strong></button>)}</div>
 {historical&&<p className="map-disclaimer">Historical mapping uses the current manual demo assignments for every past timestamp; device location changes are not stored. {history?.excluded_undated||0} undated readings excluded. {history?.truncated_source?"Only the latest 5,000 stored incidents were scanned.":""}</p>}
 <p className="map-disclaimer">This scene uses OpenStreetMap mapped building footprint polygons if available, with estimated extrusion heights when height data is absent. Missing buildings or names cannot be inferred. Color reflects only manually associated devices and their latest saved synthetic diagnoses, never an assertion about live area-wide connectivity.</p>
 </>;
}
