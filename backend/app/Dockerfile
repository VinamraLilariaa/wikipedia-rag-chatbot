# ---------- Build React ----------
FROM node:20 AS frontend

WORKDIR /app/frontend

COPY frontend/package*.json ./

RUN npm install

COPY frontend .

RUN npm run build

# ---------- Python ----------
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY backend backend
COPY chroma_db chroma_db

COPY --from=frontend /app/frontend/dist backend/static

EXPOSE 7860

CMD ["python", "-m", "uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "7860"]