# Reuse API - Backend FastAPI

Backend completo para la sistema de intercambio sostenible **Reuse** de la PUCE (Pontificia Universidad Católica del Ecuador).

## 📋 Descripción

Reuse es una sistema que permite a estudiantes intercambiar libros, materiales académicos, ropa universitaria y accesorios electrónicos, promoviendo la economía circular dentro del campus.

## ✨ Características

- 🔐 **Autenticación JWT** con access y refresh tokens
- 📦 **CRUD de Ofertas** - Publicar y gestionar objetos
- 💬 **Sistema de Chat** - Mensajería entre usuarios
- 🔄 **Sistema de Intercambios** - Trueques con confirmación dual
- 🏆 **Gamificación** - Puntos, niveles, insignias y retos
- 📊 **Rankings** - Por facultad y general
- 🔔 **Notificaciones** - Sistema de notificaciones en tiempo real
- ⚙️ **Preferencias** - Configuración personalizable por usuario

## 🏗️ Arquitectura

El proyecto sigue **Clean Architecture** con las siguientes capas:

```
app/
├── core/          # Lógica core (seguridad, dependencias, excepciones)
├── db/            # Configuración de base de datos
├── models/        # Modelos ORM (SQLAlchemy)
├── schemas/       # Schemas Pydantic (validación)
├── crud/          # Operaciones CRUD
├── services/      # Lógica de negocio
├── api/v1/        # Endpoints REST
└── utils/         # Utilidades
```

## 🛠️ Stack Tecnológico

- **FastAPI** 0.109.0 - Framework web moderno y rápido
- **SQLAlchemy** 2.0.25 - ORM para PostgreSQL
- **Pydantic** v2 - Validación de datos
- **PostgreSQL** 14+ - Base de datos
- **JWT** - Autenticación basada en tokens
- **Uvicorn** - Servidor ASGI

### 🎯 Patrones de Diseño Implementados

- **Singleton Pattern** - Conexión única a base de datos
  - Una sola instancia de `DatabaseConnection`
  - Pool de conexiones reutilizable
  - Configuración centralizada

- **Repository Pattern** - CRUDs separados de la lógica de negocio

- **Dependency Injection** - Dependencias de FastAPI para modularidad

## 📦 Instalación

### 1. Requisitos Previos

- Python 3.10+
- PostgreSQL 14+
- pip o poetry

### 2. Clonar Repositorio

```bash
git clone https://github.com/osrkzc04/reuse-api
cd reuse-api
```

### 3. Crear Entorno Virtual

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 4. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 5. Configurar Variables de Entorno

Copiar `.env.example` a `.env`:

```bash
cp .env.example .env
```

**⚠️ IMPORTANTE: Configurar variables REQUERIDAS**

El archivo `.env` debe contener obligatoriamente:

```env
# REQUERIDO: URL de conexión a PostgreSQL
DATABASE_URL=postgresql://postgres:tu_password@localhost:5432/reuse_db

# REQUERIDO: Clave secreta para JWT (genera una nueva)
SECRET_KEY=tu-clave-secreta-generada-con-openssl-rand-hex-32
```

**Generar SECRET_KEY segura:**

```bash
# Linux/Mac
openssl rand -hex 32

# Windows PowerShell
-join ((48..57) + (97..102) | Get-Random -Count 32 | % {[char]$_})

# Python
python -c "import secrets; print(secrets.token_hex(32))"
```

Variables opcionales (tienen valores por defecto):
- `DEBUG` - Modo debug (default: False)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Expiración de tokens (default: 30)
- `ALLOWED_ORIGINS` - URLs permitidas para CORS

### 6. Inicializar Base de Datos

El script ejecuta automáticamente `scripts/init_db.sql`:

```bash
python scripts/create_db.py
```

Esto creará:
- ✅ 28 tablas con soft delete
- ✅ Índices optimizados
- ✅ Triggers automáticos de auditoría
- ✅ Vistas SQL para reportes
- ✅ Datos iniciales (facultades, categorías, ubicaciones, badges, retos)

### 7. Ejecutar Servidor

```bash
uvicorn app.main:app --reload
```

El servidor estará disponible en: **http://localhost:5002**

## 📚 Documentación API

Una vez el servidor esté corriendo:

- **Swagger UI (Interactiva)**: http://localhost:5002/docs
- **ReDoc**: http://localhost:5002/redoc
- **OpenAPI JSON**: http://localhost:5002/openapi.json

## 🔑 Endpoints Principales

### Autenticación

```
POST   /api/v1/auth/register      - Registrar nuevo usuario
POST   /api/v1/auth/login         - Iniciar sesión
POST   /api/v1/auth/refresh       - Renovar access token
POST   /api/v1/auth/logout        - Cerrar sesión
```

### Usuarios

```
GET    /api/v1/users/me           - Obtener usuario actual
PUT    /api/v1/users/me           - Actualizar perfil
GET    /api/v1/users/{id}         - Ver perfil público
GET    /api/v1/users/me/stats     - Estadísticas del usuario
```

### Ofertas

```
GET    /api/v1/offers             - Listar ofertas (feed)
GET    /api/v1/offers/{id}        - Detalle de oferta
POST   /api/v1/offers             - Crear oferta
PUT    /api/v1/offers/{id}        - Actualizar oferta
DELETE /api/v1/offers/{id}        - Eliminar oferta
GET    /api/v1/my-offers          - Mis ofertas
```

### Notificaciones

```
GET    /api/v1/notifications             - Listar notificaciones
GET    /api/v1/notifications/unread-count - Contador no leídas
PATCH  /api/v1/notifications/{id}/read   - Marcar como leída
POST   /api/v1/notifications/mark-all-read - Marcar todas
```

### Catálogos

```
GET    /api/v1/faculties    - Listar facultades
GET    /api/v1/categories   - Listar categorías
GET    /api/v1/locations    - Listar ubicaciones
```

## 🗄️ Modelo de Datos

### Entidades Principales (28 tablas)

**Características de la BD:**
- Soft Delete en todas las tablas principales (campo `deleted_at`)
- Triggers de auditoría que registran cambios en `audit_history`
- Vistas SQL optimizadas para reportes administrativos

**Catálogos:**
- `faculties` - Facultades PUCE
- `categories` - Categorías de objetos
- `locations` - Ubicaciones del campus

**Usuarios:**
- `users` - Usuarios del sistema
- `refresh_tokens` - Tokens JWT
- `user_preferences` - Preferencias
- `user_reputation_metrics` - Métricas y reputación

**Ofertas:**
- `offers` - Objetos publicados
- `offer_photos` - Fotos de objetos
- `offer_interests` - Intereses ("Me interesa")

**Chat:**
- `conversations` - Conversaciones
- `messages` - Mensajes

**Intercambios:**
- `exchanges` - Intercambios/trueques
- `exchange_events` - Eventos (auditoría)
- `exchange_ratings` - Valoraciones

**Gamificación:**
- `challenges` - Retos
- `user_challenges` - Progreso de retos
- `badges_catalog` - Catálogo de insignias
- `user_badges` - Insignias obtenidas

**Otros:**
- `notifications` - Notificaciones
- `credits_ledger` - Libro mayor de créditos
- `content_flags` - Reportes
- `activity_log` - Log de actividad

Ver `scripts/init_db.sql` para el schema completo.

## 🔒 Autenticación

El sistema usa **JWT (JSON Web Tokens)** con dos tipos de tokens:

1. **Access Token**
   - Validez: 30 minutos
   - Usado en cada request
   - Header: `Authorization: Bearer {access_token}`

2. **Refresh Token**
   - Validez: 7 días
   - Usado para renovar access tokens
   - Almacenado en BD para revocación

### Flujo de Autenticación

```
1. POST /auth/register → Crear cuenta
2. POST /auth/login → Obtener tokens
3. Usar access_token en headers de requests
4. Cuando expire → POST /auth/refresh con refresh_token
5. POST /auth/logout → Revocar refresh_token
```

## 🎮 Gamificación

### Puntos de Sostenibilidad

Los usuarios ganan puntos por:
- Completar intercambios
- Completar retos
- Obtener valoraciones positivas

### Niveles

Nivel calculado automáticamente según fórmula:
```python
nivel = sqrt(puntos / 50) + 1
```

### Insignias

Desbloqueadas automáticamente al cumplir criterios:
- `first_exchange` - Primer intercambio
- `frequent_trader` - 10 intercambios
- `eco_warrior` - Completar todos los retos mensuales
- `book_master` - 15 libros intercambiados
- Y más...

### Retos

Tipos:
- **Weekly** - Semanales
- **Monthly** - Mensuales
- **Special** - Especiales/eventos
- **Permanent** - Permanentes

## 🔒 Stored Procedures

El sistema implementa procedimientos almacenados para operaciones críticas que garantizan atomicidad y validación de reglas de negocio:

### Operaciones Críticas

| Stored Procedure | Descripción | Garantías |
|------------------|-------------|-----------|
| `sp_complete_exchange` | Completar intercambio con confirmación dual | FOR UPDATE lock, validación de saldo, transferencia atómica |
| `sp_claim_reward` | Reclamar recompensa del catálogo | Previene overselling con lock de stock |
| `sp_create_exchange` | Crear intercambio y reservar oferta | Reserva atómica, previene doble reserva |
| `sp_cancel_exchange` | Cancelar intercambio y liberar oferta | Liberación atómica de oferta |
| `sp_complete_challenge` | Completar reto con recompensas | Otorga puntos, créditos y badges atómicamente |
| `sp_transfer_credits` | Transferir créditos entre usuarios | Validación de balance, registro de ambas transacciones |

### Tipos de Transacción

```sql
-- Tipos soportados en credits_ledger
'initial_grant'      -- Créditos iniciales
'exchange_payment'   -- Pago por intercambio (débito)
'exchange_received'  -- Recepción por intercambio (crédito)
'reward_claim'       -- Canje de recompensa
'challenge_reward'   -- Recompensa por completar reto
'transfer_out'       -- Transferencia saliente
'transfer_in'        -- Transferencia entrante
'admin_adjustment'   -- Ajuste administrativo
'refund'             -- Reembolso
```

### Ejecución

Los stored procedures están integrados en `scripts/init_db.sql` y se crean automáticamente al inicializar la base de datos:

```bash
psql -U postgres -d reuse_db -f scripts/init_db.sql
```

## 🐳 Docker

### Despliegue con Docker Compose

El proyecto incluye configuración completa para Docker:

```bash
# Construir y ejecutar todos los servicios
docker-compose up -d

# Ver logs
docker-compose logs -f

# Detener servicios
docker-compose down
```

### Servicios Incluidos

| Servicio | Puerto | Descripción |
|----------|--------|-------------|
| `db` | 5432 | PostgreSQL 15 Alpine |
| `api` | 5002 | FastAPI Backend |
| `backup` | - | Servicio de backup automático |

### Variables de Entorno Docker

Crear archivo `.env` con:

```env
# Base de datos
POSTGRES_DB=reuse_db
POSTGRES_USER=postgres
POSTGRES_PASSWORD=tu_password_seguro

# API
SECRET_KEY=tu-clave-secreta-generada
DEBUG=False
ALLOWED_ORIGINS=http://localhost:3000

# Backup
BACKUP_SCHEDULE=0 2 * * *
BACKUP_RETENTION_DAYS=7
```

## 💾 Sistema de Backup

### Arquitectura

```
┌─────────────┐         ┌─────────────┐
│   backup    │ pg_dump │     db      │
│  container  │────────▶│  container  │
└──────┬──────┘         └─────────────┘
       │
       ▼
┌─────────────────────┐
│  /backups/          │
│  ├── backup_1.sql.gz│
│  └── backup_2.sql.gz│
└─────────────────────┘
  (volumen persistente)
```

### Configuración

| Variable | Default | Descripción |
|----------|---------|-------------|
| `BACKUP_SCHEDULE` | `0 2 * * *` | Expresión cron (2:00 AM diario) |
| `BACKUP_RETENTION_DAYS` | `7` | Días a mantener backups |

### Comandos de Backup

```bash
# Ejecutar backup manual
docker exec reuse-backup /usr/local/bin/backup.sh

# Ver backups disponibles
docker exec reuse-backup ls -lh /backups/

# Ver logs de backup
docker exec reuse-backup cat /var/log/backup.log
```

### Restaurar Backup

```bash
# Listar backups disponibles
docker exec -it reuse-backup /usr/local/bin/restore.sh

# Restaurar un backup específico
docker exec -it reuse-backup /usr/local/bin/restore.sh reuse_backup_20260205_020000.sql.gz
```

**⚠️ ADVERTENCIA:** La restauración sobrescribe TODOS los datos actuales. Se requiere confirmación escribiendo "SI".

### Flujo del Backup

1. **Inicio del contenedor**: Ejecuta backup inicial
2. **Cron programado**: Ejecuta `backup.sh` según `BACKUP_SCHEDULE`
3. **pg_dump**: Exporta la base de datos comprimida (.sql.gz)
4. **Limpieza automática**: Elimina backups mayores a `BACKUP_RETENTION_DAYS`
5. **Volumen persistente**: Backups guardados en `reuse-backup-data`

### Copiar Backup a Host

```bash
# Copiar backup al directorio actual
docker cp reuse-backup:/backups/reuse_backup_YYYYMMDD_HHMMSS.sql.gz ./

# Copiar todos los backups
docker cp reuse-backup:/backups/ ./backups-local/
```

## 📝 Sistema de Auditoría (Activity Log)

El sistema registra automáticamente acciones importantes para auditoría:

### Servicio de Logging

```python
from app.services.activity_log_service import log_activity, ActionTypes, EntityTypes

log_activity(
    db=db,
    action_type=ActionTypes.LOGIN,
    user_id=user.id,
    entity_type=EntityTypes.USER,
    entity_id=user.id,
    extra_data={"email": user.email},
    ip_address=x_forwarded_for,
    user_agent=user_agent
)
```

### Tipos de Acciones Registradas

| Categoría | Acciones |
|-----------|----------|
| Auth | `LOGIN`, `LOGIN_FAILED`, `REGISTER` |
| Ofertas | `CREATE_OFFER`, `UPDATE_OFFER`, `DELETE_OFFER` |
| Intercambios | `CREATE_EXCHANGE`, `ACCEPT_EXCHANGE`, `CONFIRM_EXCHANGE`, `COMPLETE_EXCHANGE`, `CANCEL_EXCHANGE`, `RATE_EXCHANGE` |
| Admin | `ADMIN_UPDATE_USER_STATUS`, `ADMIN_UPDATE_USER_ROLE`, `ADMIN_UPDATE_OFFER_STATUS` |
| Retos | `JOIN_CHALLENGE` |

### Endpoints de Reportes

```
GET  /api/v1/reports/audit         - Listar registros de auditoría
GET  /api/v1/reports/audit/export  - Exportar a CSV
GET  /api/v1/reports/action-types  - Tipos de acciones disponibles
```

## 🔐 Control de Acceso por Roles

### Roles Disponibles

| Rol | Descripción |
|-----|-------------|
| `estudiante` | Usuario normal, puede crear ofertas e intercambiar |
| `moderador` | Puede gestionar usuarios y ofertas |
| `administrador` | Acceso completo, puede cambiar roles |

### Restricciones para Admin/Moderador

- ❌ No pueden crear ofertas
- ❌ No participan en rankings
- ❌ No pueden unirse a retos
- ✅ Pueden acceder al panel de administración

### Dependencies de Autorización

```python
from app.core.deps import (
    get_current_active_user,    # Usuario activo autenticado
    get_current_admin_user,     # Admin o moderador
    get_current_superadmin_user # Solo administrador
)
```

## 👥 Autores
- **Oscar Gualoto** – Desarrollador Backend
  🔗 GitHub: https://github.com/osrkzc04

---

**Hecho con ❤️ para la comunidad PUCE**
