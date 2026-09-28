FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends tesseract-ocr && rm -rf /var/lib/apt/lists/*
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY frontend ./frontend
COPY data ./data
COPY outputs ./outputs
ENV VEIL_SEMANTIC_PROVIDER=heuristic VEIL_OCR_PROVIDER=tesseract VEIL_HOST=0.0.0.0 VEIL_PORT=8080
EXPOSE 8080
CMD ["python","-m","uvicorn","veil.main:app","--app-dir","backend","--host","0.0.0.0","--port","8080"]
