"use client";
import {useState} from "react";
import {postJSON,pretty} from "../../lib/api";
type Row={index:number;device_id:string;record_id?:number;report?:{status:string;suspected_root_cause:string};error?:string}
export default function ImportTelemetry(){
 const [text,setText]=useState("");
 const [rows,setRows]=useState<Row[]>([]);
 const [error,setError]=useState("");
 const [busy,setBusy]=useState(false);
 async function run(){
  setError("");setBusy(true);
  try{
   const payload=JSON.parse(text);
   const records=Array.isArray(payload)?payload:Array.isArray(payload.records)?payload.records:[payload];
   const result=await postJSON<{results:Row[]}>("/api/telemetry/import",{records});
   setRows(result.results);
  }catch(e){setError(String(e))}finally{setBusy(false)}
 }
 async function fromFile(file?:File){if(file)setText(await file.text())}
 return <><div className="eyebrow">DATA / INGESTION</div><h1 className="heading">Import telemetry.</h1>
 <p className="sub">Upload or paste a JSON object, JSON array, or an object with a records array. Every observation is retained by device ID and timestamp.</p>
 <section className="panel"><h2>Telemetry input</h2>
 <input type="file" accept=".json,application/json" onChange={e=>fromFile(e.target.files?.[0])}/>
 <p><textarea aria-label="Telemetry JSON" placeholder='[{"device_id":"SW-01","timestamp":"2026-10-31T10:00:00Z","latency_ms":20}]' value={text} onChange={e=>setText(e.target.value)}/></p>
 <button onClick={run} disabled={busy||!text.trim()}>{busy?"Diagnosing…":"Import and diagnose →"}</button>
 {error&&<p className="error">{error}</p>}
 </section>
 {rows.length>0&&<section className="panel table-wrap"><h2>Import results</h2><table><thead><tr><th>Record</th><th>Device</th><th>Status</th><th>Diagnosis</th></tr></thead><tbody>{rows.map(r=><tr key={r.index}><td>{r.record_id??r.index}</td><td>{r.device_id}</td><td>{r.report?.status??"FAILED"}</td><td>{r.error??pretty(r.report?.suspected_root_cause??"")}</td></tr>)}</tbody></table></section>}
 <p className="sub">Import defaults to the server's configured diagnostic mode. On a free public deployment, disable Gemini in the backend until authentication and quota limits are implemented.</p>
 </>;
}
