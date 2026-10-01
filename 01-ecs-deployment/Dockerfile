FROM python:3.11-slim

# Evita que Python escriba archivos .pyc en disco y fuerza el envío directo de logs a la terminal
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Copiar e instalar dependencias limpiando la caché en la misma capa
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY . .

EXPOSE 8501

# Comando corregido (Streamlit no acepta espacios antes de las flags)
CMD ["streamlit", "run", "app.py", "--server.enableCORS=false", "--server.port=8501"]