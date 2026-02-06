"""
CRUD para recompensas y créditos.
Incluye métodos que utilizan stored procedures para operaciones críticas.
"""
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, text
from uuid import UUID
from datetime import datetime
from app.crud.base import CRUDBase
from app.models.credits import RewardsCatalog, RewardClaim, CreditsLedger
from app.schemas.reward import RewardCreate, RewardUpdate


class CRUDReward(CRUDBase[RewardsCatalog, RewardCreate, RewardUpdate]):
    """CRUD específico para recompensas."""

    def get_active_rewards(
        self, db: Session, *, limit: int = 30
    ) -> List[RewardsCatalog]:
        """
        Obtener recompensas activas con stock disponible.

        Args:
            db: Sesion de base de datos
            limit: Limite de registros (default 30)

        Returns:
            Lista de recompensas activas
        """
        return (
            db.query(RewardsCatalog)
            .filter(
                RewardsCatalog.is_active == True,
                RewardsCatalog.stock_quantity > 0
            )
            .order_by(RewardsCatalog.credits_cost)
            .limit(limit)
            .all()
        )

    def get_all_rewards(
        self, db: Session, *, include_inactive: bool = False, skip: int = 0, limit: int = 50
    ) -> List[RewardsCatalog]:
        """
        Obtener todas las recompensas.

        Args:
            db: Sesión de base de datos
            include_inactive: Incluir recompensas inactivas
            skip: Registros a saltar
            limit: Límite de registros

        Returns:
            Lista de recompensas
        """
        query = db.query(RewardsCatalog)

        if not include_inactive:
            query = query.filter(RewardsCatalog.is_active == True)

        return (
            query
            .order_by(RewardsCatalog.credits_cost)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def claim_reward(
        self, db: Session, *, user_id: UUID, reward_id: int
    ) -> RewardClaim:
        """
        Crear una reclamación de recompensa.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            reward_id: ID de la recompensa

        Returns:
            Reclamación creada

        Raises:
            ValueError: Si la recompensa no está disponible o no hay stock
        """
        # Verificar que la recompensa existe y está activa
        reward = self.get(db, id=reward_id)
        if not reward or not reward.is_active:
            raise ValueError("Recompensa no disponible")

        if reward.stock_quantity <= 0:
            raise ValueError("Recompensa sin stock disponible")

        # Verificar que el usuario tiene suficientes créditos
        from app.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("Usuario no encontrado")

        # Calcular balance actual del usuario
        balance = self.get_user_balance(db, user_id=user_id)
        if balance < reward.credits_cost:
            raise ValueError(f"Créditos insuficientes. Necesitas {reward.credits_cost}, tienes {balance}")

        # Crear reclamación
        claim = RewardClaim(
            user_id=user_id,
            reward_id=reward_id,
            credits_spent=reward.credits_cost,
            status='pending'
        )
        db.add(claim)

        # Reducir stock
        reward.stock_quantity -= 1

        # Registrar transacción de créditos
        ledger_entry = CreditsLedger(
            user_id=user_id,
            transaction_type='reward_claim',
            amount=-reward.credits_cost,
            balance_after=balance - reward.credits_cost,
            reference_id=None,  # Se actualizará después con claim.id
            description=f"Reclamación de recompensa: {reward.name}"
        )
        db.add(ledger_entry)

        db.commit()
        db.refresh(claim)
        return claim

    def get_user_claims(
        self, db: Session, *, user_id: UUID, limit: int = 30
    ) -> List[RewardClaim]:
        """
        Obtener reclamaciones de un usuario.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            limit: Límite de registros (default 30)

        Returns:
            Lista de reclamaciones del usuario
        """
        return (
            db.query(RewardClaim)
            .filter(RewardClaim.user_id == user_id)
            .order_by(desc(RewardClaim.created_at))
            .limit(limit)
            .all()
        )

    def get_pending_claims(
        self, db: Session, *, skip: int = 0, limit: int = 20
    ) -> List[RewardClaim]:
        """
        Obtener reclamaciones pendientes (para admin).

        Args:
            db: Sesión de base de datos
            skip: Registros a saltar
            limit: Límite de registros

        Returns:
            Lista de reclamaciones pendientes
        """
        return (
            db.query(RewardClaim)
            .filter(RewardClaim.status == 'pending')
            .order_by(RewardClaim.created_at)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def update_claim_status(
        self, db: Session, *, claim_id: int, status: str, notes: Optional[str] = None
    ) -> Optional[RewardClaim]:
        """
        Actualizar estado de una reclamación (admin).

        Args:
            db: Sesión de base de datos
            claim_id: ID de la reclamación
            status: Nuevo estado
            notes: Notas de la actualización

        Returns:
            Reclamación actualizada o None
        """
        claim = db.query(RewardClaim).filter(RewardClaim.id == claim_id).first()
        if not claim:
            return None

        claim.status = status
        if notes:
            claim.notes = notes

        if status == 'approved':
            claim.approved_at = datetime.utcnow()
        elif status == 'delivered':
            claim.delivered_at = datetime.utcnow()

        db.commit()
        db.refresh(claim)
        return claim

    def get_user_balance(self, db: Session, *, user_id: UUID) -> int:
        """
        Obtener balance actual de créditos de un usuario.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            Balance de créditos
        """
        last_entry = (
            db.query(CreditsLedger)
            .filter(CreditsLedger.user_id == user_id)
            .order_by(desc(CreditsLedger.created_at))
            .first()
        )

        return last_entry.balance_after if last_entry else 0

    def get_user_transactions(
        self, db: Session, *, user_id: UUID, limit: int = 50
    ) -> List[CreditsLedger]:
        """
        Obtener transacciones de créditos de un usuario.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            limit: Límite de registros (default 50)

        Returns:
            Lista de transacciones
        """
        return (
            db.query(CreditsLedger)
            .filter(CreditsLedger.user_id == user_id)
            .order_by(desc(CreditsLedger.created_at))
            .limit(limit)
            .all()
        )

    def add_credits_transaction(
        self,
        db: Session,
        *,
        user_id: UUID,
        transaction_type: str,
        amount: int,
        reference_id: Optional[UUID] = None,
        description: Optional[str] = None
    ) -> CreditsLedger:
        """
        Registrar una transacción de créditos.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            transaction_type: Tipo de transacción
            amount: Cantidad (positiva para crédito, negativa para débito)
            reference_id: ID de referencia (exchange, reward, etc.)
            description: Descripción de la transacción

        Returns:
            Transacción creada
        """
        # Obtener balance actual
        current_balance = self.get_user_balance(db, user_id=user_id)
        new_balance = current_balance + amount

        # Validar que no quede negativo
        if new_balance < 0:
            raise ValueError(f"Saldo insuficiente. Balance actual: {current_balance}, intento: {amount}")

        # Crear transacción
        transaction = CreditsLedger(
            user_id=user_id,
            transaction_type=transaction_type,
            amount=amount,
            balance_after=new_balance,
            reference_id=reference_id,
            description=description
        )
        db.add(transaction)
        db.commit()
        db.refresh(transaction)
        return transaction

    # ================================================================
    # METODOS CON STORED PROCEDURES
    # Garantizan atomicidad y validacion de reglas de negocio
    # ================================================================

    def sp_claim_reward(
        self,
        db: Session,
        *,
        user_id: UUID,
        reward_id: int
    ) -> Dict[str, Any]:
        """
        Reclamar recompensa usando stored procedure.
        Garantiza atomicidad: validación de stock (FOR UPDATE),
        validación de balance, decremento de stock, registro de claim
        y transacción de créditos. Previene overselling.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            reward_id: ID de la recompensa

        Returns:
            Dict con resultado del SP (success, claim_id, reward_name,
            credits_spent, new_balance)

        Raises:
            Exception: Si el SP falla (sin stock, saldo insuficiente, etc.)
        """
        result = db.execute(
            text("SELECT sp_claim_reward(:user_id, :reward_id)"),
            {
                "user_id": str(user_id),
                "reward_id": reward_id
            }
        ).scalar()
        db.commit()
        return result

    def sp_transfer_credits(
        self,
        db: Session,
        *,
        from_user_id: UUID,
        to_user_id: UUID,
        amount: int,
        reason: str = "Transferencia manual"
    ) -> Dict[str, Any]:
        """
        Transferir créditos entre usuarios usando stored procedure.
        Garantiza atomicidad: validación de balance, registro de débito
        y crédito, notificación al receptor.

        Args:
            db: Sesión de base de datos
            from_user_id: ID del usuario que envía
            to_user_id: ID del usuario que recibe
            amount: Cantidad de créditos a transferir
            reason: Motivo de la transferencia

        Returns:
            Dict con resultado del SP (success, amount, from_new_balance,
            to_new_balance)

        Raises:
            Exception: Si el SP falla (saldo insuficiente, usuario no existe, etc.)
        """
        result = db.execute(
            text("SELECT sp_transfer_credits(:from_user, :to_user, :amount, :reason)"),
            {
                "from_user": str(from_user_id),
                "to_user": str(to_user_id),
                "amount": amount,
                "reason": reason
            }
        ).scalar()
        db.commit()
        return result


# Instancia global del CRUD
reward = CRUDReward(RewardsCatalog)
