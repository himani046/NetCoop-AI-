export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export interface Device {device_id:string;timestamp:string|null;status:string;display_status:string;status_detail:string;root_cause:string;evidence_support:number;record_id:number;observation_count:number;previous_fault:string|null}
export interface Summary {devices:number;healthy:number;faulty:number;unverified:number;saved_observations:number;live_monitoring:boolean}
export async function getJSON<T>(endpoint:string):Promise<T>{const r=await fetch(API+endpoint,{cache:"no-store"});if(!r.ok)throw new Error(`API ${r.status}: ${endpoint}`);return r.json()}
export async function postJSON<T>(endpoint:string,value:unknown):Promise<T>{const r=await fetch(API+endpoint,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(value)});if(!r.ok)throw new Error(await r.text());return r.json()}
export function pretty(v:string){return v.replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase())}
