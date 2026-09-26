import {useState} from 'react'
import {MapContainer,TileLayer,useMapEvents,Marker} from 'react-leaflet'
import L from 'leaflet'
import './styles.css'

type Pixel={lat:number;lng:number}
const icon=new L.Icon({iconUrl:'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',iconRetinaUrl:'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',shadowUrl:'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',iconSize:[25,41],iconAnchor:[12,41]})
function Picker({setPixel}:{setPixel:(p:Pixel)=>void}){useMapEvents({click:e=>setPixel(e.latlng)});return null}

export default function App(){
 const [mode,setMode]=useState<'cold'|'hot'>('cold')
 const [cold,setCold]=useState<Pixel|null>(null),[hot,setHot]=useState<Pixel|null>(null)
 const [files,setFiles]=useState<FileList|null>(null)
 const [ws,setWs]=useState(''),[etoi,setEtoi]=useState(''),[eto,setEto]=useState('')
 const [status,setStatus]=useState('Ready')
 const select=(p:Pixel)=>mode==='cold'?setCold(p):setHot(p)
 const run=()=>setStatus('Configuration captured — backend SEBAL runner will process this project.')
 return <main>
  <header><div><span className="eyebrow">SEBAL • WEB ANALYSIS</span><h1>Surface Energy Balance & Evapotranspiration</h1><p>Run the SEBAL workflow through a browser-based interface.</p></div><span className="badge">{status}</span></header>
  <section className="grid">
   <div className="card"><h2>1. Input data</h2><p>Upload Landsat GeoTIFF files, the MTL metadata file, and MDT_Sebal.tif.</p><input type="file" multiple onChange={e=>setFiles(e.target.files)}/>{files&&<small>{files.length} file(s) selected</small>}</div>
   <div className="card"><h2>2. Weather parameters</h2><label>Wind speed at 2 m (m/s)<input value={ws} onChange={e=>setWs(e.target.value)}/></label><label>Instantaneous reference ET (mm)<input value={etoi} onChange={e=>setEtoi(e.target.value)}/></label><label>Daily reference ET (mm)<input value={eto} onChange={e=>setEto(e.target.value)}/></label></div>
  </section>
  <section className="card"><div className="row"><div><h2>3. Select pixels</h2><p>Choose Cold or Hot Pixel, then click the map.</p></div><div className="buttons"><button className={mode==='cold'?'active':''} onClick={()=>setMode('cold')}>Cold Pixel</button><button className={mode==='hot'?'active':''} onClick={()=>setMode('hot')}>Hot Pixel</button></div></div>
   <MapContainer center={[24.86,67.01]} zoom={5} className="map"><TileLayer attribution="&copy; OpenStreetMap contributors" url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"/><Picker setPixel={select}/>{cold&&<Marker position={cold} icon={icon}/>} {hot&&<Marker position={hot} icon={icon}/>}</MapContainer>
   <div className="coords"><span>Cold: {cold?cold.lat.toFixed(6)+', '+cold.lng.toFixed(6):'not selected'}</span><span>Hot: {hot?hot.lat.toFixed(6)+', '+hot.lng.toFixed(6):'not selected'}</span></div>
  </section>
  <section className="card"><h2>4. Run SEBAL</h2><button className="primary" onClick={run}>Start SEBAL Analysis</button><p className="muted">Processing will run the original Python/GRASS GIS engine in an isolated backend environment.</p></section>
  <section className="card"><h2>5. Expected outputs</h2><div className="outputs">{['NDVI','SAVI','LAI','Surface Temperature','Albedo','Net Radiation','Soil Heat Flux','Sensible Heat Flux','Latent Heat Flux','Instantaneous ET','Reference ET Fraction','Daily ET'].map(x=><span key={x}>{x}</span>)}</div></section>
 </main>
}