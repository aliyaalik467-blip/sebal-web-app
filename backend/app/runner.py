import os,subprocess
from pathlib import Path

def run_sebal(project_dir: Path, config: dict):
    env=os.environ.copy()
    env.update({
        "SEBAL_INPUT_DIR": str(project_dir/"input"),
        "SEBAL_OUTPUT_DIR": str(project_dir/"results"),
        "WS_2M": str(config["wind_speed_2m"]),
        "ETO_INSTANT": str(config["eto_instantaneous"]),
        "ETO_DAILY": str(config["eto_daily"]),
        "COLDPIX_XY": f'{config["cold"]["lng"]},{config["cold"]["lat"]}',
        "HOTPIX_XY": f'{config["hot"]["lng"]},{config["hot"]["lat"]}',
        "GISDB": "/grassdata",
        "GRASS_LOCATION": "sebal",
        "GRASS_MAPSET": "PERMANENT",
    })
    log=project_dir/"results"/"sebal.log"
    with log.open("w") as fh:
        p=subprocess.run(["python3","/sebal_engine/sebal_v10.py"],env=env,cwd="/sebal_engine",stdout=fh,stderr=subprocess.STDOUT)
    return p.returncode
