# backend/Dockerfile (Versión con Ingesta Integrada)

FROM python:3.12-slim

WORKDIR /app

# Copiamos primero el archivo de requisitos para la caché
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos TODO el resto del proyecto, incluyendo la carpeta 'knowledge_base'
COPY . .

# --- NUEVO PASO ---
# Ejecutamos el script de ingesta para crear la 'vector_store' DENTRO de la imagen
RUN python ingest.py

RUN python database_setup.py

# El comando para iniciar la API (esto no cambia)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]