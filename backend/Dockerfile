FROM osgeo/grass:ubuntu-small-latest
WORKDIR /app
COPY backend/requirements.txt /app/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /app/requirements.txt
COPY backend/app /app/app
COPY sebal_engine /sebal_engine
RUN mkdir -p /data/projects /grassdata
EXPOSE 8000
CMD ["python3","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
