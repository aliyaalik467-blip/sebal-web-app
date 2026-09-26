import os

import ee
from google.oauth2 import service_account
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import router

app=FastAPI(title="SEBAL Web API",version="0.1.0")
app.add_middleware(CORSMiddleware,allow_origins=["*"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(router,prefix="/api")


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


@app.get("/")
def root():
    return {"status":"ok","service":"sebal-web-api"}


@app.get("/health")
def health():
    return {"status":"ok","service":"sebal-web-api"}


@app.get("/api/earth-engine/test")
def earth_engine_test():
    try:
        initialize_earth_engine()
        count = (
            ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
            .limit(1)
            .size()
            .getInfo()
        )
        return {
            "status": "ok",
            "earth_engine": "connected",
            "landsat_collection_access": True,
            "sample_count": count,
        }
    except Exception as exc:
        return {
            "status": "error",
            "earth_engine": "not_connected",
            "error": str(exc),
        }
