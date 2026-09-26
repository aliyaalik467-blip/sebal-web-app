FROM osgeo/grass-gis:8.5.0-ubuntu
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /app/requirements.txt
COPY backend/app /app/app
COPY sebal_engine /sebal_engine
RUN mkdir -p /data/projects /grassdata
EXPOSE 8080
CMD ["sh","-c","python3 -m uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
