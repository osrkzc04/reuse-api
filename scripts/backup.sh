#!/bin/bash
# Script de backup para PostgreSQL
# Ejecutado por cron dentro del contenedor de backup

set -e

# Variables
BACKUP_DIR="/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/reuse_backup_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}

# Colores para logs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] INFO:${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARN:${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1"
}

# Crear directorio si no existe
mkdir -p "${BACKUP_DIR}"

log_info "Iniciando backup de la base de datos..."
log_info "Host: ${POSTGRES_HOST}, DB: ${POSTGRES_DB}"

# Realizar backup
PGPASSWORD="${POSTGRES_PASSWORD}" pg_dump \
    -h "${POSTGRES_HOST}" \
    -U "${POSTGRES_USER}" \
    -d "${POSTGRES_DB}" \
    --format=plain \
    --no-owner \
    --no-acl \
    | gzip > "${BACKUP_FILE}"

if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "${BACKUP_FILE}" | cut -f1)
    log_info "Backup completado exitosamente: ${BACKUP_FILE} (${BACKUP_SIZE})"
else
    log_error "Error al crear el backup"
    exit 1
fi

# Limpiar backups antiguos
log_info "Limpiando backups con más de ${RETENTION_DAYS} días..."
DELETED_COUNT=$(find "${BACKUP_DIR}" -name "reuse_backup_*.sql.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l)

if [ "${DELETED_COUNT}" -gt 0 ]; then
    log_info "Se eliminaron ${DELETED_COUNT} backups antiguos"
else
    log_info "No hay backups antiguos para eliminar"
fi

# Mostrar resumen de backups existentes
log_info "Backups actuales:"
ls -lh "${BACKUP_DIR}"/reuse_backup_*.sql.gz 2>/dev/null || log_warn "No hay backups disponibles"

# Calcular espacio total usado
TOTAL_SIZE=$(du -sh "${BACKUP_DIR}" | cut -f1)
log_info "Espacio total usado en backups: ${TOTAL_SIZE}"

log_info "Proceso de backup finalizado"
