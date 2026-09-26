import os
import subprocess
from pathlib import Path

import rasterio


def run_sebal(project_dir: Path, config: dict) -> int:
    input_dir = project_dir / "input"
    output_dir = project_dir / "results"
    output_dir.mkdir(parents=True, exist_ok=True)

    tif_files = sorted(
        p for p in input_dir.iterdir()
        if p.suffix.lower() == ".tif" and p.name.lower() != "mdt_sebal.tif"
    )
    dem = input_dir / "MDT_Sebal.tif"
    mtl_files = list(input_dir.glob("*MTL.txt"))

    if not tif_files:
        (output_dir / "error.txt").write_text("No Landsat GeoTIFF files were uploaded.")
        return 2
    if not dem.exists():
        (output_dir / "error.txt").write_text("MDT_Sebal.tif was not uploaded.")
        return 2
    if not mtl_files:
        (output_dir / "error.txt").write_text("No Landsat MTL.txt metadata file was uploaded.")
        return 2

    location_name = "sebal_" + project_dir.name.replace("-", "")[:20]
    gisdb = Path("/grassdata")
    location_path = gisdb / location_name
    gisdb.mkdir(parents=True, exist_ok=True)

    log = output_dir / "sebal.log"

    env = os.environ.copy()
    env.update({
        "SEBAL_INPUT_DIR": str(input_dir),
        "SEBAL_OUTPUT_DIR": str(output_dir),
        "WS_2M": str(config["wind_speed_2m"]),
        "ETO_INSTANT": str(config["eto_instantaneous"]),
        "ETO_DAILY": str(config["eto_daily"]),
        "COLDPIX_XY": config["cold_xy"],
        "HOTPIX_XY": config["hot_xy"],
        "GISDB": str(gisdb),
        "GRASS_LOCATION": location_name,
        "GRASS_MAPSET": "PERMANENT",
    })

    with log.open("w") as fh:
        if not location_path.exists():
            create = subprocess.run(
                ["grass", "-c", str(tif_files[0]), str(location_path), "-e"],
                stdout=fh, stderr=subprocess.STDOUT, env=env, text=True,
            )
            if create.returncode != 0:
                return create.returncode

        import_dem = subprocess.run(
            [
                "grass", str(location_path / "PERMANENT"), "--exec",
                "r.in.gdal", "input=" + str(dem),
                "output=MDT_Sebal", "--overwrite",
            ],
            stdout=fh, stderr=subprocess.STDOUT, env=env, text=True,
        )
        if import_dem.returncode != 0:
            return import_dem.returncode

        env["GRASS_OVERWRITE"] = "1"
        process = subprocess.run(
            ["python3", "/sebal_engine/sebal_v10.py"],
            env=env, cwd=str(output_dir),
            stdout=fh, stderr=subprocess.STDOUT, text=True,
        )
        return process.returncode
