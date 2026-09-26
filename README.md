# SEBAL Web App

A browser interface around the public Rafael Tieppo SEBAL implementation using Python and GRASS GIS.

## What it does

1. Creates an analysis project.
2. Uploads Landsat GeoTIFF bands, the matching MTL metadata file, and `MDT_Sebal.tif`.
3. Collects wind speed, instantaneous reference ET, and daily reference ET.
4. Lets the user select cold and hot pixels on a Leaflet map.
5. Converts those browser WGS84 coordinates to the uploaded raster CRS/East-North coordinates required by the original SEBAL script.
6. Creates a GRASS project from the uploaded raster CRS.
7. Runs the original SEBAL calculation.
8. Exports the main SEBAL products as GeoTIFF files for download.

## Stack

- Frontend: React + Vite + TypeScript + Leaflet
- API: FastAPI
- Scientific engine: original `sebal_v10.py`
- GIS: GRASS GIS
- Raster processing: GDAL/rasterio/pyproj
- Local orchestration: Docker Compose

## Local development

### Frontend

From `frontend/`:

```bash
npm install
npm run dev
```

### Backend + GRASS

From the repository root:

```bash
docker compose up --build
```

API health check:

```
http://localhost:8000/health
```

Set the frontend environment variable when the API is not local:

```
VITE_API_URL=https://YOUR-BACKEND-URL/api
```

## Vercel deployment

The Vercel deployment should use **`frontend/` as the Vercel Root Directory**.

After the backend is deployed, add this Vercel environment variable:

```
VITE_API_URL=https://YOUR-BACKEND-URL/api
```

Vercel hosts the React UI. The GRASS/Python processing backend must run in a Docker-capable environment such as Google Cloud Run, a VM, or another container platform.

## Backend deployment

The backend image is built from the repository root using:

```bash
docker build -f backend/Dockerfile -t sebal-web-api .
```

The container accepts the platform `PORT` environment variable.

## Expected input

The current scientific engine follows the upstream workflow and expects:

- Landsat 8 GeoTIFF bands, including the bands needed by the original script
- the matching `MTL.txt`
- `MDT_Sebal.tif`
- wind speed at 2 m
- instantaneous reference ET
- daily reference ET
- a cold pixel in an irrigation/vegetated area
- a hot pixel in a suitable bare/dry area

## Main outputs

The API exports:

- NDVI
- SAVI
- LAI
- Surface Temperature
- Albedo
- Net Radiation
- Soil Heat Flux
- Sensible Heat Flux
- Latent Heat Flux
- Instantaneous ET
- Reference ET Fraction
- Daily ET

## Scientific source

The calculation logic is based on the public repository:

`https://github.com/rafatieppo/sebal`

The upstream project is licensed under the BSD 3-Clause License. The original author attribution and license are retained in this project.

## Important

A real Landsat/DEM sample should be used for the first end-to-end production test. The repository includes CI checks for frontend compilation, Python syntax, and Docker image construction, but this environment cannot execute the GRASS Docker image against a real satellite dataset.
