#!/bin/bash
# Entrypoint para el contenedor de backup
# Configura cron basado en variables de entorno

set -e

# Valores por defecto
BACKUP_SCHEDULE="${BACKUP_SCHEDULE:-0 2 * * *}"  # Por defecto: 2:00 AM diario

echo "==================================="
echo "Reuse Database Backup Service"
echo "==================================="
echo "Schedule: ${BACKUP_SCHEDULE}"
echo "Retention: ${BACKUP_RETENTION_DAYS:-7} días"
echo "Database: ${POSTGRES_DB}@${POSTGRES_HOST}"
echo "==================================="

# Crear archivo de entorno para cron
printenv | grep -E '^(POSTGRES_|BACKUP_)' > /etc/environment

# Configurar crontab
echo "${BACKUP_SCHEDULE} /usr/local/bin/backup.sh >> /var/log/backup.log 2>&1" > /etc/crontabs/root

# Crear archivo de log
touch /var/log/backup.log

echo "Cron configurado. Ejecutando backup inicial..."

# Ejecutar un backup inicial
/usr/local/bin/backup.sh

echo "Iniciando cron daemon..."

# Ejecutar cron en primer plano y tail del log
crond -f -l 2 &
tail -f /var/log/backup.log
