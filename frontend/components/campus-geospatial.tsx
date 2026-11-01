"use client";
import {getCampusBasemap,campusBounds} from "../lib/campus-basemap";
import {useEffect,useRef,useState} from "react";
import maplibregl,{Map as GLMap,Marker} from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import type {Region} from "./campus-scene";
import type {Device} from "../lib/api";
type OSMWay={type:string;id:number;tags?:Record<string,string>;geometry?:{lat:number;lon:number}[]};
type OSMResult={elements?:OSMWay[]};
type Footprint={type:"Feature";id:string;properties:{name:string;height:number;estimated:number;osm_id:number};geometry:{type:"Polygon";coordinates:number[][][]}};
const palette={fault:"#d94b46",limited:"#d99a27",healthy:"#29835b",unmonitored:"#8b9795"};
const fallback={version:8 as const,sources:{osm:{type:"raster" as const,tiles:["https://tile.openstreetmap.org/{z}/{x}/{y}.png"],tileSize:256,attribution:"© OpenStreetMap contributors"}},layers:[{id:"osm",type:"raster" as const,source:"osm"}]};
const cacheKey="netcoop-osm-buildings-v2";
const CAMPUS_BOUNDS:[[number,number],[number,number]]=[[85.666,20.143],[85.683,20.153]];
function toGeoJSON(input:OSMResult){const features:Footprint[]=[];for(const e of input.elements||[]){if(e.type!=="way"||!e.tags?.building||!e.geometry||e.geometry.length<4)continue;
 const coordinates=e.geometry.map(p=>[p.lon,p.lat]);if(coordinates[0][0]!==coordinates[coordinates.length-1][0]||coordinates[0][1]!==coordinates[coordinates.length-1][1])continue;
 const taggedHeight=parseFloat(e.tags.height||"");const levels=Number(e.tags["building:levels"]||2);const height=Number.isFinite(taggedHeight)&&taggedHeight>0?Math.min(taggedHeight,120):Math.min(12,Math.max(1,Number.isFinite(levels)?levels:2))*3.2;features.push({type:"Feature",id:"way/"+e.id,properties:{name:e.tags.name||"Unnamed mapped building",height,estimated:Number(!(Number.isFinite(taggedHeight)&&taggedHeight>0)),osm_id:e.id},geometry:{type:"Polygon",coordinates:[coordinates]}})}
 return {type:"FeatureCollection" as const,features};}
const api="https://overpass.kumi.systems/api/interpreter";
export function CampusGeospatial({regions,selected,onSelect,onBuilding,onCatalog,devices=[],assignments=[]}:{regions:Region[];selected:string|null;onSelect:(id:string)=>void;onBuilding?:(name:string,osmId:number)=>void;onCatalog?:(names:string[])=>void;devices?:Device[];assignments?:{device_id:string;region_id:string}[]}){
 const holder=useRef<HTMLDivElement>(null),map=useRef<GLMap|null>(null),markers=useRef<Marker[]>([]),connectionLabels=useRef<Marker[]>([]),recent=useRef(regions);
 const [count,setCount]=useState<number|null>(null),[warning,setWarning]=useState(""),[loading,setLoading]=useState(true);
 const basemap=getCampusBasemap();
 const [ready,setReady]=useState(false);
 useEffect(()=>{recent.current=regions},[regions]);
 useEffect(()=>{if(!holder.current)return;const m=new maplibregl.Map({container:holder.current,style:basemap.style,center:[85.6735,20.1478],zoom:16,pitch:63,bearing:-27,antialias:true,maxPitch:75,maxBounds:campusBounds,minZoom:14.9});
 map.current=m;m.addControl(new maplibregl.NavigationControl({visualizePitch:true}),"top-right");m.on("load",()=>setReady(true));return()=>{markers.current.forEach(x=>x.remove());connectionLabels.current.forEach(x=>x.remove());markers.current=[];connectionLabels.current=[];m.remove();map.current=null}},[]);
 useEffect(()=>{if(!ready||!map.current)return;const m=map.current;let cancelled=false;
 async function load(){try{let raw:OSMResult|null=null;try{const stored=sessionStorage.getItem(cacheKey);if(stored)raw=JSON.parse(stored) as OSMResult}catch{}
 if(!raw){const q='[out:json][timeout:25];way["building"](20.143,85.666,20.153,85.683);out geom;';const response=await fetch(api+"?data="+encodeURIComponent(q),{signal:AbortSignal.timeout(29000)});if(!response.ok)throw Error("OSM footprints temporarily unavailable");raw=await response.json() as OSMResult;try{sessionStorage.setItem(cacheKey,JSON.stringify(raw))}catch{}}
 if(cancelled)return;const shapes=toGeoJSON(raw);setCount(shapes.features.length);onCatalog?.([...new Set(shapes.features.map(f=>f.properties.name).filter(n=>n!=="Unnamed mapped building"))].sort());
 if(!m.getSource("campus-buildings"))m.addSource("campus-buildings",{type:"geojson",data:shapes});
 if(!m.getLayer("campus-buildings-3d"))m.addLayer({id:"campus-buildings-3d",type:"fill-extrusion",source:"campus-buildings",paint:{"fill-extrusion-color":["case",["==",["get","estimated"],0],"#859c9a","#aab5af"],"fill-extrusion-height":["interpolate",["linear"],["zoom"],14.9,0,16,["get","height"]],"fill-extrusion-base":0,"fill-extrusion-opacity":0.81}});
 if(!m.getLayer("campus-building-outline"))m.addLayer({id:"campus-building-outline",type:"line",source:"campus-buildings",paint:{"line-color":"#61727c","line-width":0.8}});
 if(!m.getLayer("campus-building-names"))m.addLayer({id:"campus-building-names",type:"symbol",source:"campus-buildings",filter:["!=",["get","name"],"Unnamed mapped building"],layout:{"text-field":["get","name"],"text-size":11,"text-anchor":"center","text-max-width":11},paint:{"text-color":"#1d303a","text-halo-color":"#ffffff","text-halo-width":2}});
 const interact=(ev:maplibregl.MapMouseEvent&{features?:maplibregl.MapGeoJSONFeature[]})=>{const f=ev.features?.[0];if(f)onBuilding?.(String(f.properties?.name||"Unnamed mapped building"),Number(f.properties?.osm_id||0))};
 m.on("click","campus-buildings-3d",interact);m.on("mouseenter","campus-buildings-3d",()=>{m.getCanvas().style.cursor="pointer"});m.on("mouseleave","campus-buildings-3d",()=>{m.getCanvas().style.cursor=""});
 }catch(e){if(!cancelled)setWarning(String(e))}finally{if(!cancelled)setLoading(false)}}
 void load();return()=>{cancelled=true}},[ready,onBuilding]);
 useEffect(()=>{if(!ready||!map.current)return;const m=map.current;
 const byId=new Map(devices.map(d=>[d.device_id,d]));
 const regionId=new Map(assignments.map(a=>[a.device_id,a.region_id]));
 const locations=new Map(regions.map(r=>[r.id,r]));
 const failedIds=new Set(regions.flatMap(r=>r.devices.filter(d=>d.status==="diagnosed").map(d=>d.device_id)));
 const features=devices.flatMap(d=>{const parent=byId.get((d as Device&{parent_id?:string|null}).parent_id||"");
 if(!parent)return [];
 const from=locations.get(regionId.get(d.device_id)||"");const to=locations.get(regionId.get(parent.device_id)||"");
 if(!from||!to||from.id===to.id)return [];
 return [{type:"Feature" as const,properties:{label:parent.device_id+" → "+d.device_id,device:d.device_id,upstream:parent.device_id,alert:failedIds.has(d.device_id)||failedIds.has(parent.device_id)?1:0},geometry:{type:"LineString" as const,coordinates:[[to.longitude,to.latitude],[from.longitude,from.latitude]]}}]});
 connectionLabels.current.forEach(label=>label.remove());connectionLabels.current=[];
 for(const feature of features){const [a,b]=feature.geometry.coordinates;const el=document.createElement("span");el.className="geo-link-name"+(feature.properties.alert?" geo-link-alert":"");el.textContent=(feature.properties.alert?"⚠ ":"")+feature.properties.label;el.title="Logical parent relationship only — not a mapped physical cable";connectionLabels.current.push(new maplibregl.Marker({element:el,anchor:"center"}).setLngLat([(a[0]+b[0])/2,(a[1]+b[1])/2]).addTo(m))}
 const geojson={type:"FeatureCollection" as const,features};
 const src=m.getSource("logical-connections") as maplibregl.GeoJSONSource|undefined;
 if(src)src.setData(geojson);else{m.addSource("logical-connections",{type:"geojson",data:geojson});
 m.addLayer({id:"logical-connection-lines",type:"line",source:"logical-connections",paint:{"line-color":["case",["==",["get","alert"],1],"#d94b46","#315fc0"],"line-width":3,"line-dasharray":[2,1],"line-opacity":.9}});
}
 },[ready,devices,assignments,regions]);
 useEffect(()=>{if(!ready||!map.current)return;markers.current.forEach(x=>x.remove());markers.current=[];
 for(const r of regions){const el=document.createElement("button");el.type="button";el.className="geo-3d-marker "+r.status+(selected===r.id?" selected":"");el.style.setProperty("--status-color",palette[r.status]);el.setAttribute("aria-label",r.name+"; "+r.status+"; "+r.devices.length+" devices");el.innerHTML='<span class="geo-3d-halo"></span><span class="geo-3d-pin"></span>'+(r.status==="fault"?'<span class="geo-alert-glyph">!</span>':"");
 const label=document.createElement("span");label.textContent=r.name;label.className="geo-3d-name";el.appendChild(label);el.addEventListener("mouseenter",()=>onSelect(r.id));el.addEventListener("click",()=>onSelect(r.id));
 markers.current.push(new maplibregl.Marker({element:el,anchor:"center"}).setLngLat([r.longitude,r.latitude]).addTo(map.current))}
 },[ready,regions,selected,onSelect]);
 return <div className="campus-geospatial"><div ref={holder} className="campus-geospatial-canvas"/><div className="geo-3d-caption"><b>3D CAMPUS / IIT BHUBANESWAR</b><span>{basemap.source}</span><span>{loading?"Loading mapped building footprints…":count!==null?count+" OSM mapped building outlines":"Building footprints unavailable"}</span></div>{warning&&<div className="geo-3d-warning">OSM geometry unavailable; reference regions remain interactive. {warning}</div>}<div className="geo-3d-bottom">CAMPUS VIEWPORT RESTRICTED · RED LINKS = FAULT AT AN ENDPOINT · NOT PROOF OF DOWNSTREAM FAILURE · LOGICAL LINKS, NOT CABLE ROUTES · © OPENSTREETMAP</div></div>;
}
