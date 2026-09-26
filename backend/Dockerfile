FROM osgeo/grass:ubuntu-small-latest
WORKDIR /app
COPY requirements.txt .
RUN python3 -m pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY ../sebal_engine /sebal_engine
RUN mkdir -p /data/projects /grassdata
EXPOSE 8000
CMD ["python3","-m","uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
