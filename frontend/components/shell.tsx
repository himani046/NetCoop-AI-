"use client";
import Link from "next/link";
import {usePathname} from "next/navigation";
import {useEffect,useState} from "react";
import type {LucideIcon} from "lucide-react";
import {LayoutDashboard,Map,Box,Network,ClipboardList,History,Workflow,Scale,MessageSquare,ScanSearch,Upload,Settings2,FileJson,Search,Menu,X} from "lucide-react";
import {getJSON,Device} from "../lib/api";
type NavItem=[string,string,LucideIcon];
type NavGroup={title:string;links:NavItem[]};
const groups:NavGroup[]=[
{title:"OPERATIONS",links:[["/","Command center",LayoutDashboard],["/satellite","Satellite campus",Map],["/campus","3D campus",Box],["/devices","Device inventory",Network],["/incidents","Incident command",ClipboardList],["/events","Events & history",History]]},
{title:"INTELLIGENCE",links:[["/agents","Agent collaboration",Workflow],["/courtroom","Fault courtroom",Scale],["/experience","Network experience",MessageSquare],["/investigation","Adaptive investigation",ScanSearch]]},
{title:"SYSTEM",links:[["/import","Upload JSON",Upload],["/configure","Configure system",Settings2],["/technical","Technical records",FileJson]]}];
export function Shell({children}:{children:React.ReactNode}){
 const path=usePathname();const [open,setOpen]=useState(false);const [query,setQuery]=useState("");const [devices,setDevices]=useState<Device[]>([]);
 useEffect(()=>{getJSON<Device[]>("/api/devices/latest").then(setDevices).catch(()=>{})},[path]);
 const found=devices.filter(d=>d.device_id.toLowerCase().includes(query.toLowerCase())).slice(0,6);
 const last=devices.map(d=>d.timestamp).filter((x):x is string=>!!x).sort().at(-1);
 return <div className="shell app-shell">
 <aside className={"sidebar new-sidebar "+(open?"sidebar-open":"")}>
 <div className="brand-lockup"><span className="brand-symbol">◈</span><div><strong>NETCOOP</strong><small>CAMPUS NETWORK INTELLIGENCE</small></div><button className="mobile-close" aria-label="Close navigation" onClick={()=>setOpen(false)}><X size={18}/></button></div>
 <div className="sidebar-scroll">{groups.map(g=><div className="nav-group" key={g.title}><div className="nav-heading">{g.title}</div>{g.links.map(([href,label,Icon])=><Link onClick={()=>setOpen(false)} key={href} href={href} className={"nav "+(path===href?"active":"")}><Icon size={17}/><span>{label}</span></Link>)}</div>)}</div>
 <div className="source-note"><span className="source-led"/> SYNTHETIC / TEST TELEMETRY<small>Not connected to production infrastructure</small></div>
 </aside><div className="shell-main">
 <header className="topbar"><button className="mobile-menu" aria-label="Open navigation" onClick={()=>setOpen(true)}><Menu size={20}/></button><div className="topbar-name"><small>INSTITUTE OF TECHNOLOGY · BHUBANESWAR</small><b>Network operations command</b></div><div className="global-search"><Search size={16}/><input aria-label="Search device ID" value={query} placeholder="Find a device ID…" onChange={e=>setQuery(e.target.value)}/>{query&&<div className="search-results">{found.length?found.map(d=><Link key={d.device_id} onClick={()=>setQuery("")} href={"/devices?device="+encodeURIComponent(d.device_id)}>{d.device_id}<small>{d.display_status}</small></Link>):<span>No matching saved devices</span>}</div>}</div><div className="topbar-record"><span>LAST OBSERVATION</span><b>{last?last.replace("T"," ").slice(0,19)+" UTC":"No readings"}</b></div><Link className="topbar-cta" href="/import"><Upload size={15}/> Upload JSON</Link></header>
 <main className="content new-content">{children}</main></div></div>;
}
