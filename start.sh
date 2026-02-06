#!/bin/bash

# Script de inicio para contenedor Docker
# Ejecuta inicialización de BD y arranca el servidor

set -e

echo "========================================"
echo "🚀 Iniciando Reuse API"
echo "========================================"

# Función para esperar a que PostgreSQL esté listo
wait_for_postgres() {
    echo "⏳ Esperando a que PostgreSQL esté listo..."

    # Extraer información de la DATABASE_URL
    # Formato: postgresql://usuario:contraseña@host:puerto/database
    DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\).*/\1/p')
    DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')
    DB_USER=$(echo $DATABASE_URL | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
    DB_NAME=$(echo $DATABASE_URL | sed -n 's/.*\/\([^?]*\).*/\1/p')

    # Valores por defecto si no se pueden extraer
    DB_HOST=${DB_HOST:-db}
    DB_PORT=${DB_PORT:-5432}
    DB_USER=${DB_USER:-postgres}
    DB_NAME=${DB_NAME:-reuse_db}

    echo "   📍 Host: $DB_HOST:$DB_PORT"
    echo "   👤 Usuario: $DB_USER"
    echo "   🗃️  Database: $DB_NAME"

    # Esperar hasta 60 segundos
    RETRIES=30
    until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" > /dev/null 2>&1 || [ $RETRIES -eq 0 ]; do
        echo "   ⏳ Esperando PostgreSQL... ($RETRIES intentos restantes)"
        RETRIES=$((RETRIES-1))
        sleep 2
    done

    if [ $RETRIES -eq 0 ]; then
        echo "   ❌ Error: No se pudo conectar a PostgreSQL"
        exit 1
    fi

    echo "   ✅ PostgreSQL está listo!"
}

# Verificar que exista la variable DATABASE_URL
if [ -z "$DATABASE_URL" ]; then
    echo "❌ Error: DATABASE_URL no está configurada"
    exit 1
fi

if [ -z "$SECRET_KEY" ]; then
    echo "❌ Error: SECRET_KEY no está configurada"
    exit 1
fi

echo ""
echo "📋 Configuración:"
echo "   🔧 App Name: ${APP_NAME:-Reuse API}"
echo "   📦 Version: ${APP_VERSION:-1.0.0}"
echo "   🐛 Debug: ${DEBUG:-False}"
echo ""

# Esperar a PostgreSQL
wait_for_postgres

echo ""
echo "🗄️  Verificando base de datos..."

# Nota: El script init_db.sql se ejecuta automáticamente por PostgreSQL
# en el primer inicio si se monta en /docker-entrypoint-initdb.d/
# Si la DB ya existe, este script no se ejecutará nuevamente.

echo "   ✅ Base de datos lista"

echo ""
echo "========================================"
echo "🎯 Iniciando servidor Uvicorn"
echo "========================================"
echo "   🌐 Puerto: 5002"
echo "   🔄 Hot reload: ${DEBUG:-False}"
echo ""

# Iniciar el servidor uvicorn
# Usamos --host 0.0.0.0 para que sea accesible desde fuera del contenedor
# Usamos --port 5002 como especificado
if [ "$DEBUG" = "True" ] || [ "$DEBUG" = "true" ]; then
    echo "⚠️  Modo DEBUG activado - Hot reload habilitado"
    exec uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 5002 \
        --reload \
        --log-level debug
else
    echo "🚀 Modo PRODUCCIÓN - Optimizado"
    exec uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 5002 \
        --workers 4 \
        --log-level info
fi
