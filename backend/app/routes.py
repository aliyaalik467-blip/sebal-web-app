from pathlib import Path
import io
import json
import os
import uuid
import zipfile
import xml.etree.ElementTree as ET

import ee
import rasterio
import shapefile
from google.oauth2 import service_account
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Body
from fastapi.responses import FileResponse
from pyproj import CRS, Transformer
from rasterio.warp import transform
from shapely.geometry import shape, mapping, Polygon
from shapely.ops import transform as shapely_transform, unary_union

from .runner import run_sebal

router = APIRouter()
ROOT = Path("/data/projects")
ROOT.mkdir(parents=True, exist_ok=True)


def project(pid: str) -> Path:
    return ROOT / pid


def initialize_earth_engine():
    project_id = os.environ["GOOGLE_EE_PROJECT_ID"]
    client_email = os.environ["GOOGLE_EE_CLIENT_EMAIL"]
    private_key = os.environ["GOOGLE_EE_PRIVATE_KEY"].replace("\\n", "\n")
    info = {
        "type": "service_account",
        "project_id": project_id,
        "private_key": private_key,
        "client_email": client_email,
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    credentials = service_account.Credentials.from_service_account_info(
        info,
        scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    ee.Initialize(credentials=credentials, project=project_id)


def save_aoi(pid: str, geometry, source: str):
    geometry = geometry.buffer(0)
    if geometry.is_empty or not geometry.is_valid:
        raise HTTPException(400, "AOI geometry is invalid or empty.")
    if geometry.geom_type not in ("Polygon", "MultiPolygon"):
        raise HTTPException(400, "AOI must be a Polygon or MultiPolygon.")
    geojson = {"type": "Feature", "properties": {"source": source}, "geometry": mapping(geometry)}
    (project(pid) / "aoi.geojson").write_text(json.dumps(geojson, indent=2))
    return geojson


def parse_kml(data: bytes):
    root = ET.fromstring(data)
    polygons = []
    for elem in root.iter():
        if elem.tag.split("}")[-1] != "coordinates":
            continue
        coords = []
        for token in (elem.text or "").replace("\n", " ").split():
            parts = token.split(",")
            if len(parts) >= 2:
                coords.append((float(parts[0]), float(parts[1])))
        if len(coords) >= 4:
            try:
                poly = Polygon(coords)
                if not poly.is_empty:
                    polygons.append(poly)
            except ValueError:
                continue
    if not polygons:
        raise HTTPException(400, "No polygon geometry was found in the KML file.")
    return unary_union(polygons)


def parse_shapefile_zip(data: bytes):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        names = [Path(n).name for n in z.namelist() if not n.endswith("/")]
        lower = {n.lower() for n in names}
        required = {".shp", ".shx", ".dbf", ".prj"}
        if not all(any(n.endswith(ext) for n in lower) for ext in required):
            raise HTTPException(400, "Shapefile ZIP must contain .shp, .shx, .dbf and .prj files.")
        shp = next(n for n in names if n.lower().endswith(".shp"))
        shx = next(n for n in names if n.lower().endswith(".shx"))
        dbf = next(n for n in names if n.lower().endswith(".dbf"))
        prj = next(n for n in names if n.lower().endswith(".prj"))
        reader = shapefile.Reader(
            shp=io.BytesIO(z.read(shp)),
            shx=io.BytesIO(z.read(shx)),
            dbf=io.BytesIO(z.read(dbf)),
        )
        geometries = [shape(s.__geo_interface__) for s in reader.shapes() if not shape(s.__geo_interface__).is_empty]
        if not geometries:
            raise HTTPException(400, "The Shapefile contains no geometry.")
        geom = unary_union(geometries)
        if geom.geom_type not in ("Polygon", "MultiPolygon"):
            raise HTTPException(400, "AOI Shapefile must contain polygon geometry.")
        source_crs = CRS.from_wkt(z.read(prj).decode("utf-8", errors="replace"))
        if source_crs.to_epsg() != 4326:
            transformer = Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)
            geom = shapely_transform(transformer.transform, geom)
        return geom


@router.post("/projects")
def create_project():
    pid = str(uuid.uuid4())
    (project(pid) / "input").mkdir(parents=True)
    (project(pid) / "results").mkdir(parents=True)
    (project(pid) / "status.json").write_text(json.dumps({"status": "created"}))
    return {"project_id": pid, "status": "created"}


@router.post("/projects/{project_id}/aoi")
async def upload_aoi(project_id: str, file: UploadFile = File(...)):
    p = project(project_id)
    if not p.exists():
        raise HTTPException(404, "Project not found.")
    name = Path(file.filename or "").name
    data = await file.read()
    if name.lower().endswith(".kml"):
        geometry = parse_kml(data)
        source = "KML"
    elif name.lower().endswith(".zip"):
        geometry = parse_shapefile_zip(data)
        source = "Shapefile ZIP"
    else:
        raise HTTPException(400, "AOI must be a .kml file or a ZIP containing .shp, .shx, .dbf and .prj.")
    return {"project_id": project_id, "aoi": save_aoi(project_id, geometry, source)}


@router.post("/projects/{project_id}/aoi/geojson")
def save_drawn_aoi(project_id: str, feature: dict = Body(...)):
    p = project(project_id)
    if not p.exists():
        raise HTTPException(404, "Project not found.")
    if feature.get("type") == "Feature":
        geometry_data = feature.get("geometry")
    elif feature.get("type") in ("Polygon", "MultiPolygon"):
        geometry_data = feature
    else:
        raise HTTPException(400, "AOI must be a GeoJSON Polygon or MultiPolygon.")
    try:
        geometry = shape(geometry_data)
    except Exception as exc:
        raise HTTPException(400, f"Invalid GeoJSON AOI: {exc}")
    return {"project_id": project_id, "aoi": save_aoi(project_id, geometry, "Drawn on map")}


@router.get("/projects/{project_id}/aoi")
def get_aoi(project_id: str):
    p = project(project_id)
    if not p.exists():
        raise HTTPException(404, "Project not found.")
    aoi = p / "aoi.geojson"
    if not aoi.exists():
        raise HTTPException(404, "AOI has not been selected.")
    return json.loads(aoi.read_text())


@router.post("/projects/{project_id}/earth-engine/landsat")
def find_landsat(
    project_id: str,
    start_date: str = Form(...),
    end_date: str = Form(...),
    max_cloud: float = Form(30),
):
    p = project(project_id)
    if not p.exists():
        raise HTTPException(404, "Project not found.")
    aoi_file = p / "aoi.geojson"
    if not aoi_file.exists():
        raise HTTPException(400, "Select or upload an AOI first.")
    if start_date >= end_date:
        raise HTTPException(400, "End date must be after start date.")

    try:
        aoi_data = json.loads(aoi_file.read_text())
        initialize_earth_engine()
        geometry = ee.Geometry(aoi_data["geometry"])

        collection = (
            ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
            .filterBounds(geometry)
            .filterDate(start_date, end_date)
            .filter(ee.Filter.lte("CLOUD_COVER", max_cloud))
            .sort("CLOUD_COVER")
        )
        count = collection.size().getInfo()
        images = collection.limit(10).getInfo()["features"]

        candidates = []
        for item in images:
            props = item.get("properties", {})
            candidates.append({
                "id": item.get("id"),
                "date": props.get("DATE_ACQUIRED"),
                "cloud_cover": props.get("CLOUD_COVER"),
                "scene": props.get("LANDSAT_PRODUCT_ID") or item.get("id"),
            })

        return {
            "status": "ok",
            "project_id": project_id,
            "collection": "LANDSAT/LC08/C02/T1_L2",
            "count": count,
            "candidates": candidates,
        }
    except Exception as exc:
        return {
            "status": "error",
            "earth_engine": "connected_but_query_failed",
            "error": str(exc),
        }


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
