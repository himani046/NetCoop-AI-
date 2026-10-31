"use client";
import {useEffect,useMemo,useState} from "react";
import Link from "next/link";
import {getJSON,pretty} from "../../lib/api";
type Event={record_id:number;device_id:string;observed_at:string;status:string;root_cause:string;evidence_support:number};
type Data={events:Event[];excluded_undated:number;truncated_source:boolean;source:string};
const stateName=(s:string)=>s==="diagnosed"?"Fault":s==="healthy"?"Healthy":"Review";
export default function Playback(){
 const [data,setData]=useState<Data|null>(null),[point,setPoint]=useState(0),[error,setError]=useState(""),[playing,setPlaying]=useState(false);
 useEffect(()=>{getJSON<Data>("/api/playback/events").then(d=>{setData(d);setPoint(Math.max(0,[...new Set(d.events.map(x=>x.observed_at))].length-1))}).catch(e=>setError(String(e)))},[]);
 const times=useMemo(()=>[...new Set((data?.events||[]).map(x=>x.observed_at))], [data]);
 useEffect(()=>{if(!playing)return;const timer=window.setInterval(()=>setPoint(x=>x+1>=times.length?0:x+1),1300);return()=>window.clearInterval(timer)},[playing,times.length]);
 const cutoff=times[point];
 const visible=useMemo(()=>{const records=new Map<string,Event>();for(const e of data?.events||[]){if(e.observed_at<=cutoff)records.set(e.device_id,e)}return [...records.values()].sort((a,b)=>a.device_id.localeCompare(b.device_id))},[data,cutoff]);
 const faults=visible.filter(x=>x.status==="diagnosed").length,healthy=visible.filter(x=>x.status==="healthy").length;
 return <><div className="eyebrow">02 / FORENSIC TIMELINE</div><h1 className="heading">The network, through time.</h1><p className="sub">Scrub through historical telemetry. At each observation time, view the last known assessment of every device.</p>
 {error&&<p className="error">{error}</p>}
 <div className="playback-stage"><div className="playback-top"><span className="smallmono">OBSERVATION PLAYBACK</span><span className="smallmono">{times.length} TIMEPOINTS</span></div>
 <div className="time-readout">{cutoff?new Date(cutoff).toLocaleString("en-GB",{timeZone:"UTC",dateStyle:"medium",timeStyle:"medium"}):"No timestamped observations"} <span>UTC</span></div>
 <div className="playback-controls"><button onClick={()=>setPlaying(!playing)} disabled={times.length<2}>{playing?"Pause":"Play sequence"}</button><input aria-label="Playback timestamp" type="range" min="0" max={Math.max(times.length-1,0)} value={Math.min(point,Math.max(times.length-1,0))} onChange={e=>{setPlaying(false);setPoint(Number(e.target.value))}}/><strong>{times.length?point+1:0} / {times.length}</strong></div>
 <div className="playback-metrics"><div><span>Tracked by this point</span><b>{visible.length}</b></div><div><span>Healthy</span><b className="green">{healthy}</b></div><div><span>Fault detected</span><b className="red">{faults}</b></div><div><span>Unverified</span><b className="yellow">{visible.length-healthy-faults}</b></div></div></div>
 <div className="section-header"><h2>Device snapshots</h2><span className="smallmono">LATEST KNOWN AS OF SELECTED TIME</span></div>
 <div className="device-grid">{visible.map(d=><Link href={"/agents?record="+d.record_id} className={"device-card "+(d.status==="healthy"?"healthy":d.status==="diagnosed"?"fault":"")} key={d.device_id}><div className="smallmono">DEVICE / {d.record_id}</div><h3 className="device-title">{d.device_id}</h3><span className={"status "+d.status}>{stateName(d.status)}</span><p className="device-cause">{d.status==="diagnosed"?pretty(d.root_cause):"No confirmed fault hypothesis"}</p><p className="device-time">OBSERVED {d.observed_at}</p><div className="smallmono">OPEN AGENT INVESTIGATION ↗</div></Link>)}</div>
 <p className="map-disclaimer">Playback reflects saved diagnoses, not live monitoring or continuous interpolation. Device states persist visually until their next stored observation. {data?.excluded_undated||0} undated records are excluded. {data?.truncated_source?"The source scan was capped at 5,000 recent records.":""}</p>
 </>;
}
