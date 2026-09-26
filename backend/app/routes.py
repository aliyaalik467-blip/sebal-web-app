from pathlib import Path
import json
import uuid

import rasterio
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse
from rasterio.warp import transform

from .runner import run_sebal

router = APIRouter()
ROOT = Path("/data/projects")
ROOT.mkdir(parents=True, exist_ok=True)


def project(pid: str) -> Path:
    return ROOT / pid


@router.post("/projects")
def create_project():
    pid = str(uuid.uuid4())
    (project(pid) / "input").mkdir(parents=True)
    (project(pid) / "results").mkdir(parents=True)
    (project(pid) / "status.json").write_text(json.dumps({"status": "created"}))
    return {"project_id": pid, "status": "created"}


@router.post("/projects/{project_id}/upload")
async def upload(project_id: str, files: list[UploadFile] = File(...)):
    base = project(project_id) / "input"
    if not base.exists():
        raise HTTPException(404, "Project not found")
    saved = []
    for f in files:
        name = Path(f.filename or "upload.bin").name
        if name.lower().endswith((".tif", ".tiff")) or name.endswith("MTL.txt"):
            (base / name).write_bytes(await f.read())
            saved.append(name)
    if not saved:
        raise HTTPException(400, "No supported Landsat/DEM files were uploaded.")

    rasters = sorted(
        p for p in base.iterdir()
        if p.suffix.lower() in (".tif", ".tiff") and p.name.lower() != "mdt_sebal.tif"
    )
    metadata = {}
    if rasters:
        with rasterio.open(rasters[0]) as src:
            metadata = {
                "crs": str(src.crs) if src.crs else None,
                "bounds": [src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top],
                "width": src.width,
                "height": src.height,
            }
    return {"project_id": project_id, "files": saved, "raster": metadata}


@router.post("/projects/{project_id}/configuration")
def configuration(
    project_id: str,
    wind_speed_2m: float = Form(...),
    eto_instantaneous: float = Form(...),
    eto_daily: float = Form(...),
    cold_lat: float = Form(...),
    cold_lng: float = Form(...),
    hot_lat: float = Form(...),
    hot_lng: float = Form(...),
):
    p = project(project_id)
    if not p.exists():
        raise HTTPException(404, "Project not found")

    rasters = sorted(
        q for q in (p / "input").iterdir()
        if q.suffix.lower() in (".tif", ".tiff") and q.name.lower() != "mdt_sebal.tif"
    )
    if not rasters:
        raise HTTPException(400, "Upload a Landsat GeoTIFF before configuring pixels.")

    with rasterio.open(rasters[0]) as src:
        if src.crs is None:
            raise HTTPException(400, "The Landsat raster has no CRS.")
        xs, ys = transform("EPSG:4326", src.crs, [cold_lng, hot_lng], [cold_lat, hot_lat])
        cold_x, cold_y = xs[0], ys[0]
        hot_x, hot_y = xs[1], ys[1]
        bounds = src.bounds
        for label, x, y in [("cold", cold_x, cold_y), ("hot", hot_x, hot_y)]:
            if not (bounds.left <= x <= bounds.right and bounds.bottom <= y <= bounds.top):
                raise HTTPException(400, f"{label.title()} pixel is outside the Landsat raster extent.")

    cfg = {
        "wind_speed_2m": wind_speed_2m,
        "eto_instantaneous": eto_instantaneous,
        "eto_daily": eto_daily,
        "cold": {"lat": cold_lat, "lng": cold_lng},
        "hot": {"lat": hot_lat, "lng": hot_lng},
        "cold_xy": f"{cold_x},{cold_y}",
        "hot_xy": f"{hot_x},{hot_y}",
        "raster_crs": str(src.crs),
    }
    (p / "configuration.json").write_text(json.dumps(cfg, indent=2))
    return {"project_id": project_id, "configuration": cfg}


def worker(pid: str, cfg: dict):
    p = project(pid)
    (p / "status.json").write_text(json.dumps({"status": "running"}))
    try:
        code = run_sebal(p, cfg)
        status = "completed" if code == 0 else "failed"
        (p / "status.json").write_text(json.dumps({"status": status, "exit_code": code}))
    except Exception as exc:
        (p / "results" / "error.txt").write_text(str(exc))
        (p / "status.json").write_text(json.dumps({"status": "failed", "error": str(exc)}))


@router.post("/projects/{project_id}/run")
def run(project_id: str, background_tasks: BackgroundTasks):
    p = project(project_id)
    if not p.exists():
        raise HTTPException(404, "Project not found")
    cfg_file = p / "configuration.json"
    if not cfg_file.exists():
        raise HTTPException(400, "Project configuration is missing.")
    background_tasks.add_task(worker, project_id, json.loads(cfg_file.read_text()))
    return {"project_id": project_id, "status": "queued"}


@router.get("/projects/{project_id}/status")
def status(project_id: str):
    p = project(project_id)
    if not p.exists():
        raise HTTPException(404, "Project not found")
    return json.loads((p / "status.json").read_text())


@router.get("/projects/{project_id}/results")
def results(project_id: str):
    p = project(project_id)
    if not p.exists():
        raise HTTPException(404, "Project not found")
    files = [x.name for x in (p / "results").iterdir() if x.is_file()]
    return {"project_id": project_id, "results": files}


@router.get("/projects/{project_id}/download/{filename}")
def download(project_id: str, filename: str):
    p = project(project_id)
    target = (p / "results" / Path(filename).name).resolve()
    results_dir = (p / "results").resolve()
    if not target.is_relative_to(results_dir) or not target.exists():
        raise HTTPException(404, "Result file not found.")
    return FileResponse(target)
