import {useEffect,useState} from 'react'
import {MapContainer,TileLayer,useMapEvents,Marker,Polygon} from 'react-leaflet'
import L from 'leaflet'
import './styles.css'

type Pixel={lat:number;lng:number}
type LatLngPoint=[number,number]
type GeoJSONFeature={type:'Feature';properties:Record<string,unknown>;geometry:{type:'Polygon';coordinates:number[][][]}}

const API=(import.meta.env.VITE_API_URL||'http://localhost:8000/api').replace(/\/$/,'')
const icon=new L.Icon({iconUrl:'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',iconRetinaUrl:'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',shadowUrl:'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',iconSize:[25,41],iconAnchor:[12,41]})

function Picker({setPixel,drawMode,addPoint}:{setPixel:(p:Pixel)=>void;drawMode:boolean;addPoint:(p:LatLngPoint)=>void}){
 useMapEvents({click:e=>drawMode?addPoint([e.latlng.lat,e.latlng.lng]):setPixel(e.latlng)})
 return null
}

export default function App(){
 const [projectId,setProjectId]=useState('')
 const [mode,setMode]=useState<'cold'|'hot'>('cold')
 const [drawMode,setDrawMode]=useState(false)
 const [drawPoints,setDrawPoints]=useState<LatLngPoint[]>([])
 const [aoi,setAoi]=useState<LatLngPoint[]|null>(null)
 const [aoiSource,setAoiSource]=useState('')
 const [aoiFile,setAoiFile]=useState<File|null>(null)
 const [cold,setCold]=useState<Pixel|null>(null),[hot,setHot]=useState<Pixel|null>(null)
 const [files,setFiles]=useState<FileList|null>(null)
 const [ws,setWs]=useState(''),[etoi,setEtoi]=useState(''),[eto,setEto]=useState('')
 const [status,setStatus]=useState('Creating project…'),[error,setError]=useState(''),[results,setResults]=useState<string[]>([])
 const select=(p:Pixel)=>mode==='cold'?setCold(p):setHot(p)

 useEffect(()=>{fetch(API+'/projects',{method:'POST'}).then(r=>r.json()).then(x=>{setProjectId(x.project_id);setStatus('Ready')}).catch(()=>setError('Backend is not reachable. Set VITE_API_URL to your deployed API.'))},[])

 function startDrawing(){setDrawMode(true);setDrawPoints([]);setAoi(null);setAoiSource('')}
 function addDrawPoint(p:LatLngPoint){setDrawPoints(prev=>[...prev,p])}
 async function finishDrawing(){
  if(drawPoints.length<3){setError('AOI ke liye kam az kam 3 points select karein.');return}
  const ring=[...drawPoints,drawPoints[0]].map(([lat,lng])=>[lng,lat])
  const feature:GeoJSONFeature={type:'Feature',properties:{},geometry:{type:'Polygon',coordinates:[ring]}}
  try{
   setError('');setStatus('Validating AOI…')
   const r=await fetch(API+'/projects/'+projectId+'/aoi/geojson',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(feature)})
   const x=await r.json();if(!r.ok)throw new Error(x.detail||'AOI validation failed')
   setAoi(drawPoints);setAoiSource('Drawn on map');setDrawMode(false);setStatus('AOI ready')
  }catch(e){setError(e instanceof Error?e.message:'AOI validation failed');setStatus('Ready')}
 }
 async function uploadAoi(){
  if(!aoiFile||!projectId)return
  try{
   setError('');setStatus('Uploading AOI…')
   const fd=new FormData();fd.append('file',aoiFile)
   const r=await fetch(API+'/projects/'+projectId+'/aoi',{method:'POST',body:fd})
   const x=await r.json();if(!r.ok)throw new Error(x.detail||'AOI upload failed')
   const coords=x.aoi?.geometry?.coordinates
   const ring=coords?.[0]?.map((p:number[])=>[p[1],p[0]] as LatLngPoint)
   if(ring?.length){setAoi(ring);setAoiSource(x.aoi.properties?.source||'Uploaded AOI')}
   setStatus('AOI ready')
  }catch(e){setError(e instanceof Error?e.message:'AOI upload failed');setStatus('Ready')}
 }
 async function upload(){
  try{
   if(!projectId||!files?.length)return
   setError('');setStatus('Uploading…')
   const fd=new FormData();Array.from(files).forEach(f=>fd.append('files',f))
   const r=await fetch(API+'/projects/'+projectId+'/upload',{method:'POST',body:fd})
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
   let r=await fetch(API+'/projects/'+projectId+'/configuration',{method:'POST',body:fd})
   let x=await r.json();if(!r.ok)throw new Error(x.detail||'Configuration failed')
   setStatus('Starting SEBAL…')
   r=await fetch(API+'/projects/'+projectId+'/run',{method:'POST'});x=await r.json();if(!r.ok)throw new Error(x.detail||'Run failed')
   const timer=window.setInterval(async()=>{const s=await fetch(API+'/projects/'+projectId+'/status').then(q=>q.json());setStatus(s.status==='completed'?'Completed':s.status==='failed'?'Failed':'Processing…');if(s.status==='completed'||s.status==='failed'){window.clearInterval(timer);const rr=await fetch(API+'/projects/'+projectId+'/results').then(q=>q.json());setResults(rr.results||[])}},3000)
  }catch(e){setError(e instanceof Error?e.message:'Something went wrong');setStatus('Ready')}
 }
 return <main>
  <header><div><span className="eyebrow">SEBAL • WEB ANALYSIS</span><h1>Surface Energy Balance & Evapotranspiration</h1><p>Run the original Python/GRASS SEBAL workflow through a browser interface.</p></div><span className="badge">{status}</span></header>
  {error&&<div className="error">{error}</div>}
  <section className="grid">
   <div className="card"><h2>1. AOI Input</h2><p>Draw an area on the map, or upload a KML / Shapefile ZIP containing .shp, .shx, .dbf and .prj.</p><div className="buttons"><button className={drawMode?'active':''} onClick={startDrawing}>Draw AOI</button>{drawMode&&<button onClick={finishDrawing}>Finish AOI ({drawPoints.length} points)</button>}</div><input type="file" accept=".kml,.zip" onChange={e=>setAoiFile(e.target.files?.[0]||null)}/>{aoiFile&&<><small>{aoiFile.name}</small><button onClick={uploadAoi}>Upload AOI</button></>}{aoiSource&&<div className="success">AOI ready • {aoiSource}</div>}</div>
   <div className="card"><h2>2. Input data</h2><p>Upload Landsat GeoTIFF bands, the matching MTL.txt file, and MDT_Sebal.tif.</p><input type="file" multiple onChange={e=>setFiles(e.target.files)}/>{files&&<><small>{files.length} file(s) selected</small><button onClick={upload}>Upload to project</button></>}</div>
  </section>
  <section className="grid">
   <div className="card"><h2>3. Weather parameters</h2><label>Wind speed at 2 m (m/s)<input type="number" step="any" value={ws} onChange={e=>setWs(e.target.value)}/></label><label>Instantaneous reference ET (mm)<input type="number" step="any" value={etoi} onChange={e=>setEtoi(e.target.value)}/></label><label>Daily reference ET (mm)<input type="number" step="any" value={eto} onChange={e=>setEto(e.target.value)}/></label></div>
   <div className="card"><h2>4. Pixel selection</h2><p>When Draw AOI is off, click the map to select Cold or Hot Pixel.</p><div className="buttons"><button className={mode==='cold'?'active':''} onClick={()=>{setDrawMode(false);setMode('cold')}}>Cold Pixel</button><button className={mode==='hot'?'active':''} onClick={()=>{setDrawMode(false);setMode('hot')}}>Hot Pixel</button></div></div>
  </section>
  <section className="card"><div className="row"><div><h2>5. Map</h2><p>{drawMode?'Click 3 or more points to draw your AOI, then press Finish AOI.':'Select Cold/Hot Pixel by clicking the map.'}</p></div></div>
   <MapContainer center={[24.86,67.01]} zoom={5} className="map"><TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"/><Picker setPixel={select} drawMode={drawMode} addPoint={addDrawPoint}/>{aoi&&<Polygon positions={aoi}/>} {cold&&<Marker position={cold} icon={icon}/>} {hot&&<Marker position={hot} icon={icon}/>} {drawPoints.length>1&&<Polygon positions={drawPoints}/>}</MapContainer>
   <div className="coords"><span>AOI: {aoi?String(aoi.length-1)+' vertices':'not selected'}</span><span>Cold: {cold?cold.lat.toFixed(6)+', '+cold.lng.toFixed(6):'not selected'}</span><span>Hot: {hot?hot.lat.toFixed(6)+', '+hot.lng.toFixed(6):'not selected'}</span></div>
  </section>
  <section className="card"><h2>6. Run SEBAL</h2><button className="primary" onClick={run} disabled={!projectId}>Start SEBAL Analysis</button><p className="muted">The AOI is now stored and validated. Earth Engine integration will use this AOI in the next phase.</p></section>
  <section className="card"><h2>7. Results</h2>{results.length?<div className="outputs">{results.filter(x=>x.endsWith('.tif')).map(x=><a key={x} href={API+'/projects/'+projectId+'/download/'+encodeURIComponent(x)} target="_blank" rel="noreferrer">{x}</a>)}</div>:<p className="muted">Results will appear here after processing.</p>}</section>
 </main>
}
