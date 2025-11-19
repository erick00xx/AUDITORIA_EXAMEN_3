# # backend/Dockerfile (Versión con Ingesta Integrada)

# FROM python:3.12-slim

# WORKDIR /app

# # Copiamos primero el archivo de requisitos para la caché
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copiamos TODO el resto del proyecto, incluyendo la carpeta 'knowledge_base'
# COPY . .

# # --- NUEVO PASO ---
# # Ejecutamos el script de ingesta para crear la 'vector_store' DENTRO de la imagen
# RUN python ingest.py

# RUN python database_setup.py

# # El comando para iniciar la API (esto no cambia)
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]



# backend/Dockerfile (CORREGIDO)

FROM python:3.12-slim

WORKDIR /app

# Copiamos requisitos e instalamos
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiamos el código
COPY . .

# --- CORRECCIÓN DE LA TRAMPA ---
# Eliminamos los RUN de ingest y database aquí.
# Si los dejamos, el volumen del docker-compose los ocultará al arrancar.

# Modificamos el comando de inicio para:
# 1. Crear la DB
# 2. Hacer la ingesta de documentos (Vector Store)
# 3. Iniciar el servidor
CMD ["/bin/sh", "-c", "python database_setup.py && python ingest.py && uvicorn main:app --host 0.0.0.0 --port 8000"]