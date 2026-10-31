"use client";
import {useEffect,useState} from "react";import Link from "next/link";import {getJSON,pretty} from "../lib/api";
type History={record_id:number;timestamp:string|null;status:string;root_cause:string;evidence_support:number};
type Detail={device:{device_id:string;parent_id?:string|null;site?:string|null;timestamp:string|null;previous_fault?:string|null};metrics:unknown[]};
export function RegionInspection({deviceId}:{deviceId:string}){
 const [history,setHistory]=useState<History[]>([]),[detail,setDetail]=useState<Detail|null>(null),[error,setError]=useState("");
 useEffect(()=>{setHistory([]);setDetail(null);setError("");Promise.all([getJSON<History[]>("/api/devices/"+encodeURIComponent(deviceId)+"/history?limit=5"),getJSON<Detail>("/api/devices/"+encodeURIComponent(deviceId))]).then(([h,d])=>{setHistory(h);setDetail(d)}).catch(e=>setError(String(e)))},[deviceId]);
 return <details className="region-history"><summary>History and upstream connection</summary>{error&&<p className="sub">History unavailable: {error}</p>}
 <p className="sub"><b>Upstream / parent:</b> {detail?.device.parent_id&&detail.device.parent_id!=="UNKNOWN"?detail.device.parent_id:"Not recorded"}<br/><b>Site:</b> {detail?.device.site||"Not supplied"}</p>
 {detail?.device.previous_fault&&<p className="sub">Previous unverified fault: {pretty(detail.device.previous_fault)}</p>}
 {history.map(r=><div key={r.record_id} className="region-history-item"><b>{r.timestamp||"Undated"}</b><span>{r.status==="diagnosed"?pretty(r.root_cause):r.status}</span><Link href={"/courtroom?record="+r.record_id}>Case ↗</Link></div>)}
 <p className="map-disclaimer">Upstream ID is a logical metadata field, not a surveyed cable route. Saved observations are not proof of connected-device impact.</p>
 </details>;
}
