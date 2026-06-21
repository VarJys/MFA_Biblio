from app.modules.audit import registrar
from datetime import datetime, timezone
from app import db

class LogAuditoria(db.Model):
    """
    Tabla de auditoría inmutable.
    Registra cada operación crítica del sistema con su actor y timestamp.
    Ninguna operación debería poder borrar registros de esta tabla.
    """
    __tablename__ = "log_auditoria"

    id          = db.Column(db.Integer, primary_key=True)
    timestamp   = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    actor_id    = db.Column(db.Integer, nullable=False)
    actor_rol   = db.Column(db.String(20), nullable=False)  # bibliotecario / estudiante
    accion      = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.String(255), nullable=True)
    ip_origen   = db.Column(db.String(45), nullable=True)

    def __repr__(self):
        return f"<Log {self.timestamp} | {self.actor_rol} {self.actor_id} | {self.accion}>"


def registrar(actor_id, actor_rol, accion, descripcion="", ip=""):
    """
    Registra un evento en el log de auditoría.

    Acciones definidas:
    - LOGIN_EXITOSO
    - LOGIN_FALLIDO
    - TOTP_CONFIGURADO
    - PRESTAMO_REGISTRADO
    - DEVOLUCION_REGISTRADA
    - DEVOLUCION_CONFIRMADA
    - SESION_CERRADA
    """
    from app.modules.audit import LogAuditoria
    entrada = LogAuditoria(
        actor_id    = actor_id,
        actor_rol   = actor_rol,
        accion      = accion,
        descripcion = descripcion,
        ip_origen   = ip
    )
    db.session.add(entrada)
    db.session.commit()