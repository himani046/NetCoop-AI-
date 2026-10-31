"use client";
import {useEffect,useRef,useState} from "react";
import maplibregl,{Map as GLMap,Marker,Popup} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import Link from "next/link";
import {RegionInspection} from "./region-inspection";
import {getJSON,postJSON,Device,pretty} from "../lib/api";
export type Place={id:string;name:string;latitude:number;longitude:number;status:"fault"|"limited"|"healthy"|"unmonitored";devices:Device[]};
type Snapshot={regions:Place[];device_assignments:{device_id:string;region_id:string}[];mode:string};
const colors={fault:"#d94b46",limited:"#d99a27",healthy:"#29835b",unmonitored:"#8b9795"};
const raster={version:8 as const,sources:{basemap:{type:"raster" as const,tiles:["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],tileSize:256,attribution:"© OpenStreetMap contributors"}},layers:[{id:"basemap",type:"raster" as const,source:"basemap"}]};
export function SatelliteMap({compact=false}:{compact?:boolean}){
 const container=useRef<HTMLDivElement>(null),map=useRef<GLMap|null>(null),markers=useRef<Marker[]>([]);
 const [snapshot,setSnapshot]=useState<Snapshot|null>(null),[devices,setDevices]=useState<Device[]>([]),[selected,setSelected]=useState<Place|null>(null),[device,setDevice]=useState(""),[region,setRegion]=useState(""),[error,setError]=useState(""),[saving,setSaving]=useState(false);
 const satelliteStyle=process.env.NEXT_PUBLIC_SATELLITE_STYLE_URL;
 async function refresh(){const [a,b]=await Promise.all([getJSON<Snapshot>("/api/map/regions"),getJSON<Device[]>("/api/devices/latest")]);setSnapshot(a);setDevices(b)}
 useEffect(()=>{refresh().catch(e=>setError(String(e)))},[]);
 useEffect(()=>{if(!container.current||map.current)return;
  try{map.current=new maplibregl.Map({container:container.current,style:satelliteStyle||raster,center:[85.674,20.1476],zoom:15.2,attributionControl:true});
   map.current.addControl(new maplibregl.NavigationControl(),"top-right");
  }catch(e){setError("Map rendering unavailable: "+String(e))}
  return()=>{markers.current.forEach(m=>m.remove());markers.current=[];map.current?.remove();map.current=null};
 },[satelliteStyle]);
 useEffect(()=>{if(!map.current||!snapshot)return;markers.current.forEach(m=>m.remove());markers.current=[];
 for(const item of snapshot.regions){const root=document.createElement("button");root.type="button";root.className="site-marker "+item.status;root.style.setProperty("--marker",colors[item.status]);root.setAttribute("aria-label",item.name+": "+item.status);root.innerHTML='<span class="site-pulse"></span><span class="site-core"></span>';
  root.addEventListener("click",()=>setSelected(item));
  root.addEventListener("mouseenter",()=>{root.title=item.name+" — "+item.devices.length+" device(s) · "+item.status});
  const marker=new maplibregl.Marker({element:root}).setLngLat([item.longitude,item.latitude]).addTo(map.current!);markers.current.push(marker)}
 },[snapshot]);
 async function assign(){if(!device)return;setSaving(true);try{await postJSON("/api/map/assign",{device_id:device,region_id:region||null});await refresh();setSelected(null)}catch(e){setError(String(e))}finally{setSaving(false)}}
 return <div className={"geo-wrap "+(compact?"geo-compact":"")}><div className="geo-frame"><div className="geo-map" ref={container}/><div className="geo-status"><b>{satelliteStyle?"IMAGERY LAYER":"OPENSTREETMAP STREET BASEMAP"}</b><small>{satelliteStyle?"Externally configured style. Respect provider license and attribution.":"Satellite imagery requires a licensed provider style URL."}</small></div><div className="geo-legend">{Object.entries(colors).map(([label,color])=><span key={label}><i style={{background:color}}/>{label}</span>)}</div></div>
 {!compact&&<aside className="geo-side"><div className="eyebrow">REGION INSPECTOR</div><h2>{selected?.name||"Select a campus location"}</h2><p className="sub">Reference location · manual demo device placement</p>{selected?<><div className={"region-condition "+selected.status}>{selected.status.toUpperCase()} · {selected.devices.length} mapped devices</div>{selected.devices.length?selected.devices.map(d=><div className="location-device" key={d.device_id}><b>{d.device_id}</b><span>{d.status==="diagnosed"?pretty(d.root_cause):d.display_status}</span><small>{d.timestamp||"Undated"} · {d.status==="diagnosed"?(d.evidence_support*100).toFixed(1)+"% support":"fault evidence N/A"}</small><Link href={"/agents?record="+d.record_id}>Investigate ↗</Link><RegionInspection deviceId={d.device_id}/></div>):<p className="sub">No assigned devices or diagnoses for this location.</p>}</>:<p className="sub">Click a status marker to inspect saved diagnoses, timestamps, and any assigned devices.</p>}
 <div className="assign-box"><h3>Demo location assignment</h3><p className="sub">Changes are stored by the existing API. These are not verified physical device locations.</p><select aria-label="Device" value={device} onChange={e=>setDevice(e.target.value)}><option value="">Choose saved device</option>{devices.map(d=><option key={d.device_id}>{d.device_id}</option>)}</select><select aria-label="Region" value={region} onChange={e=>setRegion(e.target.value)}><option value="">Remove assignment</option>{snapshot?.regions.map(r=><option value={r.id} key={r.id}>{r.name}</option>)}</select><button disabled={saving||!device} onClick={assign}>{saving?"Saving…":"Save assignment"}</button></div></aside>}
 {error&&<p className="error">{error}</p>}
 {!compact&&<p className="map-disclaimer">Only current manually assigned devices affect marker colors. Region markers are point-based status indicators, not proof of a whole-building outage or a geographic blast radius. Physical topology paths cannot be drawn from device IDs alone. Map data © OpenStreetMap contributors.</p>}
 </div>;
}
