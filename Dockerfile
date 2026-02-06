# ==========================================
# STAGE 1: Builder
# ==========================================
FROM python:3.11-slim as builder

# Instalar dependencias del sistema necesarias para compilar
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Crear directorio de trabajo
WORKDIR /app

# Copiar archivos de dependencias
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==========================================
# STAGE 2: Runtime
# ==========================================
FROM python:3.11-slim

# Instalar solo las dependencias runtime necesarias
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpq5 \
    curl \
    dos2unix \
    && rm -rf /var/lib/apt/lists/*

# Crear usuario no-root para seguridad
RUN useradd -m -u 1000 appuser

# Crear directorio de trabajo
WORKDIR /app

# Copiar las dependencias instaladas desde builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copiar el código de la aplicación
COPY --chown=appuser:appuser . .

# Crear directorio para uploads
RUN mkdir -p /app/uploads && chown -R appuser:appuser /app/uploads

# Convertir terminaciones de linea CRLF a LF y dar permisos de ejecucion
RUN dos2unix /app/start.sh && chmod +x /app/start.sh

# Cambiar a usuario no-root
USER appuser

# Exponer el puerto 5002
EXPOSE 5002

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:5002/health || exit 1

# Comando de inicio
CMD ["/app/start.sh"]