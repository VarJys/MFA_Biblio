from flask import (Blueprint, render_template, redirect,
                   url_for, flash, session)
from flask_login import login_required, current_user
from datetime import datetime, timezone
from app import db
from app.models import Prestamo

prestamos_bp = Blueprint("prestamos", __name__, url_prefix="/prestamos")


def solo_estudiante(f):
    """
    Decorador que verifica que el usuario activo sea estudiante.
    Previene que el bibliotecario acceda al portal del estudiante.
    """
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("rol") != "estudiante":
            flash("Acceso restringido a estudiantes.", "danger")
            return redirect(url_for("auth.elegir_portal"))
        return f(*args, **kwargs)
    return wrapper


@prestamos_bp.route("/mis-prestamos")
@login_required
@solo_estudiante
def mis_prestamos():
    """
    Vista principal del estudiante:
    muestra préstamos activos y pendientes de confirmación.
    """
    prestamos_activos = Prestamo.query.filter(
        Prestamo.estudiante_id == current_user.id,
        Prestamo.estado.in_(["ACTIVO", "PENDIENTE_CONFIRMACION"])
    ).order_by(Prestamo.fecha_prestamo.desc()).all()

    return render_template(
        "prestamos/mis_prestamos.html",
        prestamos=prestamos_activos,
        ahora=datetime.now(timezone.utc)
    )


@prestamos_bp.route("/historial")
@login_required
@solo_estudiante
def historial():
    """Muestra el historial completo de préstamos del estudiante."""
    todos = Prestamo.query.filter_by(
        estudiante_id=current_user.id
    ).order_by(Prestamo.fecha_prestamo.desc()).all()

    return render_template("prestamos/historial.html", prestamos=todos)


@prestamos_bp.route("/confirmar-devolucion/<int:prestamo_id>", methods=["POST"])
@login_required
@solo_estudiante
def confirmar_devolucion(prestamo_id):
    """
    El estudiante confirma que devolvió el libro.
    Solo puede confirmar préstamos que le pertenecen
    y que estén en estado PENDIENTE_CONFIRMACION.
    Aquí se aplica el principio de no repudio:
    la devolución queda sellada con la sesión MFA del estudiante.
    """
    prestamo = Prestamo.query.get_or_404(prestamo_id)

    # Verificar que el préstamo pertenece al estudiante autenticado
    if prestamo.estudiante_id != current_user.id:
        flash("No tienes permiso para confirmar este préstamo.", "danger")
        return redirect(url_for("prestamos.mis_prestamos"))

    if prestamo.estado != "PENDIENTE_CONFIRMACION":
        flash("Este préstamo no está pendiente de confirmación.", "warning")
        return redirect(url_for("prestamos.mis_prestamos"))

    # Cerrar el préstamo con timestamp y confirmación del estudiante
    prestamo.estado                = "DEVUELTO"
    prestamo.confirmado_estudiante = True
    prestamo.fecha_devolucion_real = datetime.now(timezone.utc)

    # Volver a marcar el libro como disponible
    prestamo.libro.disponible = True

    db.session.commit()

    flash(
        f"Devolución de '{prestamo.libro.titulo}' confirmada correctamente.",
        "success"
    )
    return redirect(url_for("prestamos.mis_prestamos"))