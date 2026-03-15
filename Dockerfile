# Imagen base Alpine (más ligera: ~50MB vs ~150MB de slim)
FROM python:3.11-alpine

# Variables de entorno
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias de sistema necesarias para compilar algunos paquetes
RUN apk add --no-cache gcc musl-dev curl

# Copiar requirements primero (para aprovechar cache de Docker)
COPY requirements.txt .

# Instalar dependencias Python
RUN pip install --no-cache-dir -r requirements.txt && \
    apk del gcc musl-dev

# Copiar el resto de la aplicación
COPY . .

# Crear directorio de cache y usuario no-root para seguridad
RUN mkdir -p /app/cache && \
    adduser -D -u 1000 appuser && \
    chown -R appuser:appuser /app

USER appuser

# Exponer puerto
EXPOSE 5000

# Healthcheck usando curl (más ligero que python+requests)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/api/status || exit 1

# Comando de inicio con Gunicorn optimizado para NAS
# 1 worker con 4 threads: menos RAM (~50MB menos), suficiente para dashboard doméstico
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--worker-class", "gthread", "--timeout", "60", "--access-logfile", "-", "--error-logfile", "-", "app:app"]
