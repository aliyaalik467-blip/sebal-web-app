from fastapi import APIRouter,UploadFile,File,Form,HTTPException,BackgroundTasks
from pathlib import Path
import uuid,json
from .runner import run_sebal

router=APIRouter()
ROOT=Path("/data/projects"); ROOT.mkdir(parents=True,exist_ok=True)
def project(pid): return ROOT/pid

@router.post("/projects")
def create_project():
    pid=str(uuid.uuid4()); (project(pid)/"input").mkdir(parents=True); (project(pid)/"results").mkdir()
    (project(pid)/"status.json").write_text(json.dumps({"status":"created"}))
    return {"project_id":pid,"status":"created"}

@router.post("/projects/{project_id}/upload")
async def upload(project_id:str,files:list[UploadFile]=File(...)):
    base=project(project_id)/"input"
    if not base.exists(): raise HTTPException(404,"Project not found")
    saved=[]
    for f in files:
        name=Path(f.filename or "upload.bin").name
        (base/name).write_bytes(await f.read()); saved.append(name)
    return {"project_id":project_id,"files":saved}

@router.post("/projects/{project_id}/configuration")
def configuration(project_id:str,wind_speed_2m:float=Form(...),eto_instantaneous:float=Form(...),eto_daily:float=Form(...),cold_lat:float=Form(...),cold_lng:float=Form(...),hot_lat:float=Form(...),hot_lng:float=Form(...)):
    p=project(project_id)
    if not p.exists(): raise HTTPException(404,"Project not found")
    cfg={"wind_speed_2m":wind_speed_2m,"eto_instantaneous":eto_instantaneous,"eto_daily":eto_daily,"cold":{"lat":cold_lat,"lng":cold_lng},"hot":{"lat":hot_lat,"lng":hot_lng}}
    (p/"configuration.json").write_text(json.dumps(cfg,indent=2))
    return {"project_id":project_id,"configuration":cfg}

def worker(pid,cfg):
    p=project(pid); (p/"status.json").write_text(json.dumps({"status":"running"}))
    code=run_sebal(p,cfg)
    (p/"status.json").write_text(json.dumps({"status":"completed" if code==0 else "failed","exit_code":code}))

@router.post("/projects/{project_id}/run")
def run(project_id:str,background_tasks:BackgroundTasks):
    p=project(project_id)
    if not p.exists(): raise HTTPException(404,"Project not found")
    cfg=json.loads((p/"configuration.json").read_text())
    background_tasks.add_task(worker,project_id,cfg)
    return {"project_id":project_id,"status":"queued"}

@router.get("/projects/{project_id}/status")
def status(project_id:str):
    p=project(project_id)
    if not p.exists(): raise HTTPException(404,"Project not found")
    return json.loads((p/"status.json").read_text()) if (p/"status.json").exists() else {"status":"created"}

@router.get("/projects/{project_id}/results")
def results(project_id:str):
    p=project(project_id)
    if not p.exists(): raise HTTPException(404,"Project not found")
    return {"project_id":project_id,"results":[x.name for x in (p/"results").iterdir() if x.is_file()]}
