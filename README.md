# SEBAL Web App

A web application built around the public Rafael Tieppo SEBAL Python/GRASS GIS implementation.

## Goal
Upload Landsat inputs, enter SEBAL weather parameters, select hot/cold pixels, run the SEBAL processing engine, and inspect/download resulting raster products.

## Stack
- Frontend: React + Vite + TypeScript + Leaflet
- Backend: FastAPI
- Scientific processing: Python + GRASS GIS + original SEBAL engine
- Deployment: Docker-based processing/backend environment

## Status
Initial scaffold. The original SEBAL calculation is kept as the scientific source of truth and is being adapted from desktop hard-coded paths into a web-processing workflow.

The original repository is BSD 3-Clause licensed.
