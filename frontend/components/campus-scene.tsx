"use client";
import {Canvas,ThreeEvent} from "@react-three/fiber";
import {OrbitControls,Html,Environment,ContactShadows,Float} from "@react-three/drei";
import {useMemo,useState} from "react";
export type Region={id:string;name:string;latitude:number;longitude:number;status:"fault"|"limited"|"healthy"|"unmonitored";devices:{device_id:string;status:string;root_cause:string}[]};
const statusColors={fault:"#d6452f",limited:"#d79a34",healthy:"#467b5c",unmonitored:"#b9ab92"};
function Structure({region,index,onSelect,active}:{region:Region;index:number;onSelect:(id:string)=>void;active:boolean}){
 const coords=useMemo(()=>{
 const x=(region.longitude-85.6735)*950;
 const z=-(region.latitude-20.1472)*1050;
 return [x,z] as const;
 },[region.latitude,region.longitude]);
 const height=[2.2,1.6,2.6,1.85,1.3][index%5];
 const color=statusColors[region.status];
 return <group position={[coords[0],0,coords[1]]}>
   <mesh onClick={()=>onSelect(region.id)} onPointerOver={e=>{e.stopPropagation();document.body.style.cursor="pointer"}} onPointerOut={()=>document.body.style.cursor="auto"}>
     <boxGeometry args={[1.8,height,1.5]}/><meshStandardMaterial color={active?"#f1c084":"#d6cab5"} roughness={0.84}/>
   </mesh>
   <mesh position={[0,height/2+.09,0]} onClick={()=>onSelect(region.id)}>
     <boxGeometry args={[2,.18,1.7]}/><meshStandardMaterial color="#6b6154" roughness={0.8}/>
   </mesh>
   <mesh position={[0,.08,0]}>
     <cylinderGeometry args={[1.4,1.4,.08,24]}/><meshStandardMaterial color={color} emissive={color} emissiveIntensity={region.status==="fault"?.4:.1}/>
   </mesh>
   {region.status==="fault"&&<Float speed={2.7} floatIntensity={.22}>
     <mesh position={[0,height+.65,0]}>
       <octahedronGeometry args={[.31]}/><meshStandardMaterial color="#cc3c2b" emissive="#b52e20" emissiveIntensity={.8}/>
     </mesh>
   </Float>}
   <Html center position={[0,height+1.15,0]} distanceFactor={11} style={{pointerEvents:"none"}}>
     <div className={"scene-label "+region.status}><span className="pin-dot"/>{region.name}<small>{region.devices.length} assigned</small></div>
   </Html>
 </group>
}
export function CampusScene({regions,selected,onSelect}:{regions:Region[];selected:string|null;onSelect:(id:string)=>void}){
 return <div className="campus-canvas"><Canvas camera={{position:[11,14,18],fov:42}} shadows dpr={[1,1.75]}>
  <color attach="background" args={["#e5dfd1"]}/><ambientLight intensity={2}/><directionalLight position={[7,12,5]} intensity={2.7} castShadow/>
  <mesh rotation={[-Math.PI/2,0,0]} position={[0,-.12,0]} receiveShadow><planeGeometry args={[200,200]}/><meshStandardMaterial color="#dad5c5"/></mesh>
  <gridHelper args={[35,35,"#b8af9f","#c9c0ae"]} position={[0,-.10,0]}/>
  {regions.map((r,i)=><Structure key={r.id} region={r} index={i} onSelect={onSelect} active={r.id===selected}/>)}
  <ContactShadows opacity={.17} scale={38} blur={2.8} far={10} position={[0,-.07,0]}/>
  <OrbitControls makeDefault minDistance={7} maxDistance={35} maxPolarAngle={Math.PI/2.3} enablePan enableZoom/>
 </Canvas><div className="map-stamp">ILLUSTRATIVE 3D MASSING / NOT A SURVEYED BUILDING MODEL</div></div>
}
