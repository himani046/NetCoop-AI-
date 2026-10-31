"use client";
import {useEffect,useMemo,useState} from "react";
import {getJSON,pretty} from "../lib/api";
type Point={record_id:number;observed_at:string;status:string;metrics:Record<string,number>};
type Trends={device_id:string;points:Point[];excluded_undated:number;source_limit_reached:boolean};
const suggested=["latency_ms","packet_loss_pct","link_utilization_pct","cpu_pct","rssi_dbm","snr_db","dns_latency_ms"];
export function MetricTrends({deviceId}:{deviceId:string}){
 const [data,setData]=useState<Trends|null>(null),[metric,setMetric]=useState("latency_ms"),[error,setError]=useState("");
 useEffect(()=>{setData(null);getJSON<Trends>("/api/devices/"+encodeURIComponent(deviceId)+"/trends").then(setData).catch(e=>setError(String(e)))},[deviceId]);
 const names=useMemo(()=>[...new Set(data?.points.flatMap(p=>Object.keys(p.metrics))||[])].sort((a,b)=>suggested.indexOf(a)-suggested.indexOf(b)),[data]);
 useEffect(()=>{if(names.length&&!names.includes(metric))setMetric(names[0])},[names,metric]);
 const points=(data?.points||[]).filter(p=>Number.isFinite(p.metrics[metric]));
 const min=Math.min(...points.map(p=>p.metrics[metric])),max=Math.max(...points.map(p=>p.metrics[metric]));
 const width=720,height=185,spread=max-min||1;
 const poly=points.map((p,i)=>`${34+(i/Math.max(points.length-1,1))*(width-65)},${height-25-((p.metrics[metric]-min)/spread)*(height-55)}`).join(" ");
 return <div className="panel trend-panel"><div className="section-header"><h2>Metric history</h2><span className="smallmono">OBSERVED VALUES / NO FORECAST</span></div>
 <label className="smallmono" htmlFor="trend-metric">SELECT METRIC</label><select id="trend-metric" value={metric} onChange={e=>setMetric(e.target.value)}>{names.map(n=><option key={n} value={n}>{pretty(n)}</option>)}</select>
 {error&&<p className="error">{error}</p>}
 {points.length?<><svg viewBox="0 0 720 185" className="trend-svg" role="img" aria-label={pretty(metric)+" trend across "+points.length+" observations"}><line x1="34" x2="685" y1="160" y2="160" stroke="#c7b8a4"/><line x1="34" x2="685" y1="30" y2="30" stroke="#ded2c2" strokeDasharray="5 7"/><polyline fill="none" stroke="#b65435" strokeWidth="3.5" strokeLinejoin="round" points={poly}/>{points.map((p,i)=><circle key={p.record_id} cx={34+(i/Math.max(points.length-1,1))*(width-65)} cy={height-25-((p.metrics[metric]-min)/spread)*(height-55)} r="5" fill={p.status==="diagnosed"?"#be4632":p.status==="healthy"?"#477a55":"#b58a38"} stroke="#f8f3e7" strokeWidth="2"><title>{p.observed_at}: {p.metrics[metric]}</title></circle>)}<text x="36" y="20" fontSize="12" fill="#756e5e">{max.toFixed(2)}</text><text x="36" y="180" fontSize="12" fill="#756e5e">{min.toFixed(2)}</text></svg><div className="trend-range"><span>{points[0].observed_at} UTC</span><span>{points[points.length-1].observed_at} UTC</span></div></>:<p className="sub">No dated numeric measurements available for this metric.</p>}
 <p className="map-disclaimer">{data?.excluded_undated||0} undated readings excluded. Dots represent stored samples; connecting lines do not imply continuous monitoring.</p></div>
}
