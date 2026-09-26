import {useEffect,useState} from 'react'
import {MapContainer,TileLayer,useMapEvents,Marker} from 'react-leaflet'
import L from 'leaflet'
import './styles.css'

type Pixel={lat:number;lng:number}
const API=(import.meta.env.VITE_API_URL||'http://localhost:8000/api').replace(/\/$/,'')
const icon=new L.Icon({iconUrl:'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',iconRetinaUrl:'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',shadowUrl:'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',iconSize:[25,41],iconAnchor:[12,41]})

function Picker({setPixel}:{setPixel:(p:Pixel)=>void}){useMapEvents({click:e=>setPixel(e.latlng)});return null}

export default function App(){
 const [projectId,setProjectId]=useState('')
 const [mode,setMode]=useState<'cold'|'hot'>('cold')
 const [cold,setCold]=useState<Pixel|null>(null),[hot,setHot]=useState<Pixel|null>(null)
 const [files,setFiles]=useState<FileList|null>(null)
 const [ws,setWs]=useState(''),[etoi,setEtoi]=useState(''),[eto,setEto]=useState('')
 const [status,setStatus]=useState('Creating project…'),[error,setError]=useState(''),[results,setResults]=useState<string[]>([])
 const select=(p:Pixel)=>mode==='cold'?setCold(p):setHot(p)

 useEffect(()=>{fetch(API+'/projects',{method:'POST'}).then(r=>r.json()).then(x=>{setProjectId(x.project_id);setStatus('Ready')}).catch(()=>setError('Backend is not reachable. Set VITE_API_URL to your deployed API.'))},[])

 async function upload(){
  try{
   if(!projectId||!files?.length)return
   setError('');setStatus('Uploading…')
   const fd=new FormData();Array.from(files).forEach(f=>fd.append('files',f))
   const r=await fetch(API+`/projects/${projectId}/upload`,{method:'POST',body:fd})
   const x=await r.json();if(!r.ok)throw new Error(x.detail||'Upload failed')
   setStatus('Input data uploaded')
  }catch(e){setError(e instanceof Error?e.message:'Upload failed');setStatus('Ready')}
 }
 async function run(){
  try{
   if(!projectId||!files?.length||!cold||!hot)throw new Error('Upload data and select both cold and hot pixels.')
   if(!ws||!etoi||!eto)throw new Error('Enter all three weather parameters.')
   setError('');setStatus('Saving configuration…')
   const fd=new FormData()
   ;[['wind_speed_2m',ws],['eto_instantaneous',etoi],['eto_daily',eto],['cold_lat',String(cold.lat)],['cold_lng',String(cold.lng)],['hot_lat',String(hot.lat)],['hot_lng',String(hot.lng)]].forEach(([k,v])=>fd.append(k,v))
   let r=await fetch(API+`/projects/${projectId}/configuration`,{method:'POST',body:fd})
   let x=await r.json();if(!r.ok)throw new Error(x.detail||'Configuration failed')
   setStatus('Starting SEBAL…')
   r=await fetch(API+`/projects/${projectId}/run`,{method:'POST'});x=await r.json();if(!r.ok)throw new Error(x.detail||'Run failed')
   const timer=window.setInterval(async()=>{const s=await fetch(API+`/projects/${projectId}/status`).then(q=>q.json());setStatus(s.status==='completed'?'Completed':s.status==='failed'?'Failed':'Processing…');if(s.status==='completed'||s.status==='failed'){window.clearInterval(timer);const rr=await fetch(API+`/projects/${projectId}/results`).then(q=>q.json());setResults(rr.results||[])}},3000)
  }catch(e){setError(e instanceof Error?e.message:'Something went wrong');setStatus('Ready')}
 }
 return <main>
  <header><div><span className="eyebrow">SEBAL • WEB ANALYSIS</span><h1>Surface Energy Balance & Evapotranspiration</h1><p>Run the original Python/GRASS SEBAL workflow through a browser interface.</p></div><span className="badge">{status}</span></header>
  {error&&<div className="error">{error}</div>}
  <section className="grid">
   <div className="card"><h2>1. Input data</h2><p>Upload Landsat GeoTIFF bands, the matching MTL.txt file, and MDT_Sebal.tif.</p><input type="file" multiple onChange={e=>setFiles(e.target.files)}/>{files&&<><small>{files.length} file(s) selected</small><button onClick={upload}>Upload to project</button></>}</div>
   <div className="card"><h2>2. Weather parameters</h2><label>Wind speed at 2 m (m/s)<input type="number" step="any" value={ws} onChange={e=>setWs(e.target.value)}/></label><label>Instantaneous reference ET (mm)<input type="number" step="any" value={etoi} onChange={e=>setEtoi(e.target.value)}/></label><label>Daily reference ET (mm)<input type="number" step="any" value={eto} onChange={e=>setEto(e.target.value)}/></label></div>
  </section>
  <section className="card"><div className="row"><div><h2>3. Select pixels</h2><p>Choose Cold or Hot Pixel, then click the map. Coordinates are converted to the uploaded raster CRS by the backend.</p></div><div className="buttons"><button className={mode==='cold'?'active':''} onClick={()=>setMode('cold')}>Cold Pixel</button><button className={mode==='hot'?'active':''} onClick={()=>setMode('hot')}>Hot Pixel</button></div></div>
   <MapContainer center={[24.86,67.01]} zoom={5} className="map"><TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"/><Picker setPixel={select}/>{cold&&<Marker position={cold} icon={icon}/>} {hot&&<Marker position={hot} icon={icon}/>}</MapContainer>
   <div className="coords"><span>Cold: {cold?cold.lat.toFixed(6)+', '+cold.lng.toFixed(6):'not selected'}</span><span>Hot: {hot?hot.lat.toFixed(6)+', '+hot.lng.toFixed(6):'not selected'}</span></div>
  </section>
  <section className="card"><h2>4. Run SEBAL</h2><button className="primary" onClick={run} disabled={!projectId}>Start SEBAL Analysis</button><p className="muted">The backend creates a GRASS project from the uploaded raster CRS, converts the selected pixels to East/North, runs SEBAL, and exports GeoTIFF results.</p></section>
  <section className="card"><h2>5. Results</h2>{results.length?<div className="outputs">{results.filter(x=>x.endsWith('.tif')).map(x=><a key={x} href={API+`/projects/${projectId}/download/${encodeURIComponent(x)}`} target="_blank" rel="noreferrer">{x}</a>)}</div>:<p className="muted">Results will appear here after processing.</p>}</section>
 </main>
}
