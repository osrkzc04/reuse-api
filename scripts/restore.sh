#!/bin/bash
# Script para restaurar backup de PostgreSQL
# Uso: ./restore.sh [archivo_backup.sql.gz]

set -e

BACKUP_DIR="/backups"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Verificar argumento
if [ -z "$1" ]; then
    echo "Uso: $0 <archivo_backup.sql.gz>"
    echo ""
    echo "Backups disponibles:"
    ls -lh "${BACKUP_DIR}"/reuse_backup_*.sql.gz 2>/dev/null || echo "No hay backups disponibles"
    exit 1
fi

BACKUP_FILE="$1"

# Si no es ruta absoluta, buscar en BACKUP_DIR
if [[ ! "$BACKUP_FILE" == /* ]]; then
    BACKUP_FILE="${BACKUP_DIR}/${BACKUP_FILE}"
fi

# Verificar que existe el archivo
if [ ! -f "${BACKUP_FILE}" ]; then
    log_error "Archivo no encontrado: ${BACKUP_FILE}"
    exit 1
fi

log_info "Restaurando desde: ${BACKUP_FILE}"
log_info "Base de datos: ${POSTGRES_DB}"

# Confirmar
echo -e "${YELLOW}ADVERTENCIA: Esto sobrescribirá TODOS los datos actuales.${NC}"
read -p "¿Estás seguro? (escribe 'SI' para confirmar): " confirm

if [ "$confirm" != "SI" ]; then
    log_info "Restauración cancelada"
    exit 0
fi

# Restaurar
log_info "Iniciando restauración..."

gunzip -c "${BACKUP_FILE}" | PGPASSWORD="${POSTGRES_PASSWORD}" psql \
    -h "${POSTGRES_HOST}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    --quiet

if [ $? -eq 0 ]; then
    log_info "Restauración completada exitosamente"
else
    log_error "Error durante la restauración"
    exit 1
fi
