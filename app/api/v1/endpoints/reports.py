"""
Endpoints de reportes para el panel de administracion.
Solo lectura (GET).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import datetime
import io
import csv

from app.core.deps import get_db, get_current_admin_user
from app.models.user import User
from app.schemas.reports import (
    TransactionReportItem,
    TransactionReportResponse,
    AuditReportItem,
    AuditReportResponse,
    TriggerReportItem,
    TriggerReportResponse,
)

router = APIRouter()


# ================================================================
# REPORTE DE TRANSACCIONES (Ofertas)
# ================================================================

@router.get("/transactions", response_model=TransactionReportResponse)
async def get_transactions_report(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    category_id: Optional[int] = Query(None, description="Filtrar por categoria"),
    faculty_id: Optional[int] = Query(None, description="Filtrar por facultad del propietario"),
    date_from: Optional[datetime] = Query(None, description="Fecha desde"),
    date_to: Optional[datetime] = Query(None, description="Fecha hasta"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtener reporte de transacciones (ofertas).
    Requiere rol de administrador o moderador.
    """
    offset = (page - 1) * per_page

    # Intentar usar la vista, si no existe usar query directo
    try:
        base_query = "SELECT * FROM v_transactions_report"
    except Exception:
        base_query = """
            SELECT
                o.id, o.title, o.description, o.status, o.condition, o.credits_value,
                o.views_count, o.interests_count, o.is_featured, o.created_at, o.updated_at,
                u.id as owner_id, u.full_name as owner_name, u.email as owner_email,
                c.id as category_id, c.name as category_name,
                l.id as location_id, l.name as location_name,
                f.id as faculty_id, f.name as faculty_name,
                COALESCE((SELECT COUNT(*) FROM exchanges e WHERE e.offer_id = o.id), 0) as total_exchanges,
                COALESCE((SELECT COUNT(*) FROM exchanges e WHERE e.offer_id = o.id AND e.status = 'completed'), 0) as completed_exchanges,
                COALESCE((SELECT COUNT(*) FROM offer_photos op WHERE op.offer_id = o.id AND op.deleted_at IS NULL), 0) as photos_count,
                (SELECT photo_url FROM offer_photos op WHERE op.offer_id = o.id AND op.is_primary = TRUE AND op.deleted_at IS NULL LIMIT 1) as primary_photo_url
            FROM offers o
            JOIN users u ON o.user_id = u.id
            LEFT JOIN categories c ON o.category_id = c.id
            LEFT JOIN locations l ON o.location_id = l.id
            LEFT JOIN faculties f ON u.faculty_id = f.id
        """

    where_clauses = []
    params = {"limit": per_page, "offset": offset}

    if status:
        where_clauses.append("status = :status")
        params["status"] = status

    if category_id:
        where_clauses.append("category_id = :category_id")
        params["category_id"] = category_id

    if faculty_id:
        where_clauses.append("faculty_id = :faculty_id")
        params["faculty_id"] = faculty_id

    if date_from:
        where_clauses.append("created_at >= :date_from")
        params["date_from"] = date_from

    if date_to:
        where_clauses.append("created_at <= :date_to")
        params["date_to"] = date_to

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    query = f"{base_query} {where_sql} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    count_query = f"SELECT COUNT(*) FROM ({base_query} {where_sql}) as subq"

    results = db.execute(text(query), params).fetchall()
    total = db.execute(text(count_query), {k: v for k, v in params.items() if k not in ["limit", "offset"]}).scalar()

    # Obtener estadisticas resumidas
    summary_query = f"""
        SELECT
            COUNT(*) as total_offers,
            COUNT(*) FILTER (WHERE status = 'active') as active_offers,
            COUNT(*) FILTER (WHERE status = 'completed') as completed_offers,
            COUNT(*) FILTER (WHERE status = 'cancelled') as cancelled_offers,
            COUNT(*) FILTER (WHERE status = 'flagged') as flagged_offers,
            AVG(credits_value)::INTEGER as avg_credits_value,
            SUM(views_count) as total_views,
            SUM(interests_count) as total_interests
        FROM ({base_query} {where_sql}) as subq
    """
    summary_result = db.execute(text(summary_query), {k: v for k, v in params.items() if k not in ["limit", "offset"]}).fetchone()

    items = [
        TransactionReportItem(
            id=row.id,
            title=row.title,
            description=row.description,
            status=row.status,
            condition=row.condition,
            credits_value=row.credits_value,
            views_count=row.views_count,
            interests_count=row.interests_count,
            is_featured=row.is_featured,
            created_at=row.created_at,
            updated_at=row.updated_at,
            owner_id=row.owner_id,
            owner_name=row.owner_name,
            owner_email=row.owner_email,
            category_id=row.category_id,
            category_name=row.category_name,
            location_id=row.location_id,
            location_name=row.location_name,
            faculty_id=row.faculty_id,
            faculty_name=row.faculty_name,
            total_exchanges=row.total_exchanges,
            completed_exchanges=row.completed_exchanges,
            photos_count=row.photos_count,
            primary_photo_url=row.primary_photo_url
        )
        for row in results
    ]

    return TransactionReportResponse(
        data=items,
        total=total or 0,
        page=page,
        per_page=per_page,
        summary={
            "total_offers": summary_result.total_offers or 0,
            "active_offers": summary_result.active_offers or 0,
            "completed_offers": summary_result.completed_offers or 0,
            "cancelled_offers": summary_result.cancelled_offers or 0,
            "flagged_offers": summary_result.flagged_offers or 0,
            "avg_credits_value": summary_result.avg_credits_value or 0,
            "total_views": summary_result.total_views or 0,
            "total_interests": summary_result.total_interests or 0
        } if summary_result else None
    )


@router.get("/transactions/export")
async def export_transactions_report(
    status: Optional[str] = Query(None),
    category_id: Optional[int] = Query(None),
    faculty_id: Optional[int] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Exportar reporte de transacciones a CSV.
    Requiere rol de administrador o moderador.
    """
    # Obtener datos sin paginacion
    base_query = """
        SELECT
            o.id, o.title, o.status, o.condition, o.credits_value,
            o.views_count, o.interests_count, o.created_at,
            u.full_name as owner_name, u.email as owner_email,
            c.name as category_name, l.name as location_name, f.name as faculty_name
        FROM offers o
        JOIN users u ON o.user_id = u.id
        LEFT JOIN categories c ON o.category_id = c.id
        LEFT JOIN locations l ON o.location_id = l.id
        LEFT JOIN faculties f ON u.faculty_id = f.id
    """

    where_clauses = []
    params = {}

    if status:
        where_clauses.append("o.status = :status")
        params["status"] = status

    if category_id:
        where_clauses.append("o.category_id = :category_id")
        params["category_id"] = category_id

    if faculty_id:
        where_clauses.append("u.faculty_id = :faculty_id")
        params["faculty_id"] = faculty_id

    if date_from:
        where_clauses.append("o.created_at >= :date_from")
        params["date_from"] = date_from

    if date_to:
        where_clauses.append("o.created_at <= :date_to")
        params["date_to"] = date_to

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    query = f"{base_query} {where_sql} ORDER BY o.created_at DESC"

    results = db.execute(text(query), params).fetchall()

    # Generar CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Titulo", "Estado", "Condicion", "Creditos",
        "Vistas", "Intereses", "Fecha Creacion",
        "Propietario", "Email", "Categoria", "Ubicacion", "Facultad"
    ])

    for row in results:
        writer.writerow([
            str(row.id), row.title, row.status, row.condition, row.credits_value,
            row.views_count, row.interests_count, row.created_at.isoformat() if row.created_at else "",
            row.owner_name, row.owner_email, row.category_name or "", row.location_name or "", row.faculty_name or ""
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=reporte_transacciones_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )


# ================================================================
# REPORTE DE AUDITORIA (Activity Log)
# ================================================================

@router.get("/audit", response_model=AuditReportResponse)
async def get_audit_report(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    action_type: Optional[str] = Query(None, description="Filtrar por tipo de accion"),
    entity_type: Optional[str] = Query(None, description="Filtrar por tipo de entidad"),
    user_id: Optional[str] = Query(None, description="Filtrar por usuario"),
    date_from: Optional[datetime] = Query(None, description="Fecha desde"),
    date_to: Optional[datetime] = Query(None, description="Fecha hasta"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtener reporte de auditoria (activity_log).
    Requiere rol de administrador o moderador.
    """
    offset = (page - 1) * per_page

    base_query = """
        SELECT
            al.id, al.action_type, al.entity_type, al.entity_id,
            al.extra_data, al.ip_address, al.user_agent, al.created_at,
            u.id as user_id, u.full_name as user_name, u.email as user_email,
            u.role as user_role, f.name as user_faculty
        FROM activity_log al
        LEFT JOIN users u ON al.user_id = u.id
        LEFT JOIN faculties f ON u.faculty_id = f.id
    """

    where_clauses = []
    params = {"limit": per_page, "offset": offset}

    if action_type:
        where_clauses.append("al.action_type = :action_type")
        params["action_type"] = action_type

    if entity_type:
        where_clauses.append("al.entity_type = :entity_type")
        params["entity_type"] = entity_type

    if user_id:
        where_clauses.append("al.user_id = :user_id")
        params["user_id"] = user_id

    if date_from:
        where_clauses.append("al.created_at >= :date_from")
        params["date_from"] = date_from

    if date_to:
        where_clauses.append("al.created_at <= :date_to")
        params["date_to"] = date_to

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    query = f"{base_query} {where_sql} ORDER BY al.created_at DESC LIMIT :limit OFFSET :offset"
    count_query = f"SELECT COUNT(*) FROM activity_log al {where_sql}"

    results = db.execute(text(query), params).fetchall()
    total = db.execute(text(count_query), {k: v for k, v in params.items() if k not in ["limit", "offset"]}).scalar()

    items = [
        AuditReportItem(
            id=row.id,
            action_type=row.action_type,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            extra_data=row.extra_data,
            ip_address=row.ip_address,
            user_agent=row.user_agent,
            created_at=row.created_at,
            user_id=row.user_id,
            user_name=row.user_name,
            user_email=row.user_email,
            user_role=row.user_role,
            user_faculty=row.user_faculty
        )
        for row in results
    ]

    return AuditReportResponse(
        data=items,
        total=total or 0,
        page=page,
        per_page=per_page
    )


@router.get("/audit/export")
async def export_audit_report(
    action_type: Optional[str] = Query(None),
    entity_type: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Exportar reporte de auditoria a CSV.
    Requiere rol de administrador o moderador.
    """
    base_query = """
        SELECT
            al.id, al.action_type, al.entity_type, al.entity_id,
            al.ip_address, al.created_at,
            u.full_name as user_name, u.email as user_email
        FROM activity_log al
        LEFT JOIN users u ON al.user_id = u.id
    """

    where_clauses = []
    params = {}

    if action_type:
        where_clauses.append("al.action_type = :action_type")
        params["action_type"] = action_type

    if entity_type:
        where_clauses.append("al.entity_type = :entity_type")
        params["entity_type"] = entity_type

    if user_id:
        where_clauses.append("al.user_id = :user_id")
        params["user_id"] = user_id

    if date_from:
        where_clauses.append("al.created_at >= :date_from")
        params["date_from"] = date_from

    if date_to:
        where_clauses.append("al.created_at <= :date_to")
        params["date_to"] = date_to

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    query = f"{base_query} {where_sql} ORDER BY al.created_at DESC"

    results = db.execute(text(query), params).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Tipo Accion", "Tipo Entidad", "ID Entidad",
        "IP", "Fecha", "Usuario", "Email"
    ])

    for row in results:
        writer.writerow([
            row.id, row.action_type, row.entity_type or "", str(row.entity_id) if row.entity_id else "",
            row.ip_address or "", row.created_at.isoformat() if row.created_at else "",
            row.user_name or "", row.user_email or ""
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=reporte_auditoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )


# ================================================================
# REPORTE DE TRIGGERS (Audit History)
# ================================================================

@router.get("/triggers", response_model=TriggerReportResponse)
async def get_triggers_report(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=500),
    table_name: Optional[str] = Query(None, description="Filtrar por tabla"),
    operation: Optional[str] = Query(None, description="Filtrar por operacion (INSERT, UPDATE, DELETE)"),
    changed_by: Optional[str] = Query(None, description="Filtrar por usuario que hizo el cambio"),
    date_from: Optional[datetime] = Query(None, description="Fecha desde"),
    date_to: Optional[datetime] = Query(None, description="Fecha hasta"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtener reporte de triggers (audit_history).
    Requiere rol de administrador o moderador.
    """
    offset = (page - 1) * per_page

    base_query = """
        SELECT
            ah.id, ah.table_name, ah.record_id, ah.operation,
            ah.old_data, ah.new_data, ah.changed_fields,
            ah.ip_address, ah.user_agent, ah.created_at,
            u.id as changed_by_id, u.full_name as changed_by_name,
            u.email as changed_by_email, u.role as changed_by_role,
            CASE
                WHEN ah.operation = 'INSERT' THEN 'Registro creado'
                WHEN ah.operation = 'UPDATE' THEN 'Registro actualizado (' || COALESCE(array_length(ah.changed_fields, 1), 0) || ' campos)'
                WHEN ah.operation = 'DELETE' THEN 'Registro eliminado'
                ELSE ah.operation::TEXT
            END as operation_summary,
            EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - ah.created_at)) / 3600 as hours_ago
        FROM audit_history ah
        LEFT JOIN users u ON ah.changed_by = u.id
    """

    where_clauses = []
    params = {"limit": per_page, "offset": offset}

    if table_name:
        where_clauses.append("ah.table_name = :table_name")
        params["table_name"] = table_name

    if operation:
        where_clauses.append("ah.operation = :operation")
        params["operation"] = operation

    if changed_by:
        where_clauses.append("ah.changed_by = :changed_by")
        params["changed_by"] = changed_by

    if date_from:
        where_clauses.append("ah.created_at >= :date_from")
        params["date_from"] = date_from

    if date_to:
        where_clauses.append("ah.created_at <= :date_to")
        params["date_to"] = date_to

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    query = f"{base_query} {where_sql} ORDER BY ah.created_at DESC LIMIT :limit OFFSET :offset"
    count_query = f"SELECT COUNT(*) FROM audit_history ah {where_sql}"

    results = db.execute(text(query), params).fetchall()
    total = db.execute(text(count_query), {k: v for k, v in params.items() if k not in ["limit", "offset"]}).scalar()

    items = [
        TriggerReportItem(
            id=row.id,
            table_name=row.table_name,
            record_id=row.record_id,
            operation=row.operation,
            old_data=row.old_data,
            new_data=row.new_data,
            changed_fields=row.changed_fields,
            ip_address=row.ip_address,
            user_agent=row.user_agent,
            created_at=row.created_at,
            changed_by_id=row.changed_by_id,
            changed_by_name=row.changed_by_name,
            changed_by_email=row.changed_by_email,
            changed_by_role=row.changed_by_role,
            operation_summary=row.operation_summary,
            hours_ago=row.hours_ago
        )
        for row in results
    ]

    return TriggerReportResponse(
        data=items,
        total=total or 0,
        page=page,
        per_page=per_page
    )


@router.get("/triggers/export")
async def export_triggers_report(
    table_name: Optional[str] = Query(None),
    operation: Optional[str] = Query(None),
    changed_by: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Exportar reporte de triggers a CSV.
    Requiere rol de administrador o moderador.
    """
    base_query = """
        SELECT
            ah.id, ah.table_name, ah.record_id, ah.operation,
            ah.changed_fields, ah.ip_address, ah.created_at,
            u.full_name as changed_by_name, u.email as changed_by_email
        FROM audit_history ah
        LEFT JOIN users u ON ah.changed_by = u.id
    """

    where_clauses = []
    params = {}

    if table_name:
        where_clauses.append("ah.table_name = :table_name")
        params["table_name"] = table_name

    if operation:
        where_clauses.append("ah.operation = :operation")
        params["operation"] = operation

    if changed_by:
        where_clauses.append("ah.changed_by = :changed_by")
        params["changed_by"] = changed_by

    if date_from:
        where_clauses.append("ah.created_at >= :date_from")
        params["date_from"] = date_from

    if date_to:
        where_clauses.append("ah.created_at <= :date_to")
        params["date_to"] = date_to

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
    query = f"{base_query} {where_sql} ORDER BY ah.created_at DESC"

    results = db.execute(text(query), params).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Tabla", "ID Registro", "Operacion",
        "Campos Cambiados", "IP", "Fecha", "Usuario", "Email"
    ])

    for row in results:
        changed_fields_str = ", ".join(row.changed_fields) if row.changed_fields else ""
        writer.writerow([
            row.id, row.table_name, row.record_id, row.operation,
            changed_fields_str, row.ip_address or "", row.created_at.isoformat() if row.created_at else "",
            row.changed_by_name or "", row.changed_by_email or ""
        ])

    output.seek(0)
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=reporte_triggers_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"}
    )


# ================================================================
# UTILIDADES
# ================================================================

@router.get("/tables")
async def get_audit_tables(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtener lista de tablas disponibles en audit_history.
    Requiere rol de administrador o moderador.
    """
    results = db.execute(
        text("SELECT DISTINCT table_name FROM audit_history ORDER BY table_name")
    ).fetchall()

    return [row.table_name for row in results]


@router.get("/action-types")
async def get_action_types(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtener lista de tipos de accion disponibles en activity_log.
    Requiere rol de administrador o moderador.
    """
    results = db.execute(
        text("SELECT DISTINCT action_type FROM activity_log ORDER BY action_type")
    ).fetchall()

    return [row.action_type for row in results]
