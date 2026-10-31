"use client";
import {useEffect,useState} from "react";import Link from "next/link";import {getJSON,Device} from "../lib/api";
type NetworkDevice=Device & {parent_id?:string|null;site?:string|null};
export function TopologySchematic(){const [devices,setDevices]=useState<NetworkDevice[]>([]),[error,setError]=useState("");
useEffect(()=>{getJSON<NetworkDevice[]>("/api/devices/latest").then(setDevices).catch(e=>setError(String(e)))},[]);
const edges=devices.filter(d=>d.parent_id&&d.parent_id!=="UNKNOWN"&&d.parent_id!==d.device_id);
return <section className="panel"><div className="section-header"><h2>Logical upstream relationships</h2><span className="smallmono">SAVED TELEMETRY / NOT GEOGRAPHIC CABLE ROUTES</span></div>
<p className="sub">These relationships are shown only when the stored observation contains a parent device ID. Red status does not automatically prove an upstream outage or a downstream blast radius.</p>
{error&&<p className="error">{error}</p>}
{edges.length?<div className="topology-links">{edges.map(d=><div className="topology-edge" key={d.device_id}><span className="topology-node">{d.parent_id}</span><span className="topology-arrow" aria-label="logical parent relationship">→</span><Link href={"/devices?device="+encodeURIComponent(d.device_id)} className="topology-node">{d.device_id}</Link><span className={"status "+d.status}>{d.display_status}</span></div>)}</div>:<p className="sub">No explicit parent-device relationships in the latest saved observations. Physical connections cannot be inferred from device names.</p>}
</section>}
