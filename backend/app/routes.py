from fastapi import APIRouter,UploadFile,File,Form,HTTPException
from pathlib import Path
import uuid,json

router=APIRouter()
ROOT=Path("/data/projects")
ROOT.mkdir(parents=True,exist_ok=True)

@router.post("/projects")
def create_project():
    pid=str(uuid.uuid4())
    (ROOT/pid/"input").mkdir(parents=True)
    (ROOT/pid/"results").mkdir()
    return {"project_id":pid,"status":"created"}

@router.post("/projects/{project_id}/upload")
async def upload(project_id:str,files:list[UploadFile]=File(...)):
    base=ROOT/project_id/"input"
    if not base.exists():
        raise HTTPException(404,"Project not found")
    saved=[]
    for f in files:
        target=base/Path(f.filename or "upload.bin").name
        target.write_bytes(await f.read())
        saved.append(target.name)
    return {"project_id":project_id,"files":saved}

@router.post("/projects/{project_id}/configuration")
def configuration(project_id:str,wind_speed_2m:float=Form(...),eto_instantaneous:float=Form(...),eto_daily:float=Form(...),cold_lat:float=Form(...),cold_lng:float=Form(...),hot_lat:float=Form(...),hot_lng:float=Form(...)):
    if not (ROOT/project_id).exists():
        raise HTTPException(404,"Project not found")
    cfg={"wind_speed_2m":wind_speed_2m,"eto_instantaneous":eto_instantaneous,"eto_daily":eto_daily,"cold":{"lat":cold_lat,"lng":cold_lng},"hot":{"lat":hot_lat,"lng":hot_lng}}
    (ROOT/project_id/"configuration.json").write_text(json.dumps(cfg,indent=2))
    return {"project_id":project_id,"configuration":cfg}

@router.post("/projects/{project_id}/run")
def run(project_id:str):
    if not (ROOT/project_id).exists():
        raise HTTPException(404,"Project not found")
    return {"project_id":project_id,"status":"queued","message":"SEBAL processing integration is the next engine step"}

@router.get("/projects/{project_id}/status")
def status(project_id:str):
    return {"project_id":project_id,"status":"ready"}

@router.get("/projects/{project_id}/results")
def results(project_id:str):
    return {"project_id":project_id,"results":[]}
