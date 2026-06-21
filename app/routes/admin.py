from flask import (Blueprint, render_template, redirect,
                   url_for, request, flash, session)
from flask_login import login_required, current_user
from datetime import datetime, timezone, timedelta
from app import db
from app.models import Estudiante, Libro, Prestamo

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


def solo_bibliotecario(f):
    """
    Decorador que verifica que el usuario activo sea bibliotecario.
    Previene que un estudiante autenticado acceda al panel admin.
    """
    from functools import wraps
    @wraps(f)
    def wrapper(*args, **kwargs):
        if session.get("rol") != "bibliotecario":
            flash("Acceso restringido al personal de biblioteca.", "danger")
            return redirect(url_for("auth.elegir_portal"))
        return f(*args, **kwargs)
    return wrapper


@admin_bp.route("/dashboard")
@login_required
@solo_bibliotecario
def dashboard():
    """Panel principal del bibliotecario con resumen del sistema."""
    total_estudiantes = Estudiante.query.filter_by(estado="ACTIVO").count()
    total_libros      = Libro.query.count()
    libros_disponibles= Libro.query.filter_by(disponible=True).count()
    prestamos_activos = Prestamo.query.filter_by(estado="ACTIVO").count()
    prestamos_pend    = Prestamo.query.filter_by(
                            estado="PENDIENTE_CONFIRMACION").count()

    return render_template(
        "admin/dashboard.html",
        total_estudiantes=total_estudiantes,
        total_libros=total_libros,
        libros_disponibles=libros_disponibles,
        prestamos_activos=prestamos_activos,
        prestamos_pendientes=prestamos_pend
    )


@admin_bp.route("/buscar-estudiante", methods=["GET", "POST"])
@login_required
@solo_bibliotecario
def buscar_estudiante():
    """Busca un estudiante por código para iniciar un préstamo."""
    estudiante = None

    if request.method == "POST":
        codigo = request.form.get("codigo_estudiantil", "").strip()
        estudiante = Estudiante.query.filter_by(
            codigo_estudiantil=codigo
        ).first()

        if not estudiante:
            flash("No se encontró ningún estudiante con ese código.", "warning")

    return render_template(
        "admin/buscar_estudiante.html",
        estudiante=estudiante
    )


@admin_bp.route("/registrar-prestamo/<int:estudiante_id>", methods=["GET", "POST"])
@login_required
@solo_bibliotecario
def registrar_prestamo(estudiante_id):
    """
    Registra un nuevo préstamo:
    - GET:  muestra los libros disponibles y datos del estudiante
    - POST: crea el préstamo en la BD y marca el libro como no disponible
    """
    estudiante = Estudiante.query.get_or_404(estudiante_id)

    if estudiante.estado != "ACTIVO":
        flash("El estudiante no está activo. No se puede registrar el préstamo.", "danger")
        return redirect(url_for("admin.buscar_estudiante"))

    # Verificar límite de 3 préstamos activos
    prestamos_activos = Prestamo.query.filter_by(
        estudiante_id=estudiante_id,
        estado="ACTIVO"
    ).count()

    if prestamos_activos >= 3:
        flash("El estudiante ya tiene 3 préstamos activos. Debe devolver uno primero.", "warning")
        return redirect(url_for("admin.buscar_estudiante"))

    libros_disponibles = Libro.query.filter_by(disponible=True).all()

    if request.method == "POST":
        libro_id = request.form.get("libro_id")
        libro    = Libro.query.get(libro_id)

        if not libro or not libro.disponible:
            flash("El libro seleccionado no está disponible.", "danger")
            return render_template(
                "admin/registrar_prestamo.html",
                estudiante=estudiante,
                libros=libros_disponibles
            )

        # Fecha de devolución esperada: 7 días
        fecha_devolucion_esp = datetime.now(timezone.utc) + timedelta(days=7)

        prestamo = Prestamo(
            estudiante_id=estudiante_id,
            libro_id=libro.id,
            bibliotecario_id=current_user.id,
            estado="ACTIVO",
            fecha_devolucion_esp=fecha_devolucion_esp
        )

        # Marcar libro como no disponible
        libro.disponible = False

        db.session.add(prestamo)
        db.session.commit()

        flash(
            f"Préstamo registrado: '{libro.titulo}' → {estudiante.nombre}. "
            f"Devolución esperada: {fecha_devolucion_esp.strftime('%d/%m/%Y')}.",
            "success"
        )
        return redirect(url_for("admin.dashboard"))

    return render_template(
        "admin/registrar_prestamo.html",
        estudiante=estudiante,
        libros=libros_disponibles
    )


@admin_bp.route("/registrar-devolucion/<int:prestamo_id>", methods=["POST"])
@login_required
@solo_bibliotecario
def registrar_devolucion(prestamo_id):
    """
    El bibliotecario registra la recepción física del libro.
    El préstamo queda en PENDIENTE_CONFIRMACION hasta que
    el estudiante confirme desde su portal.
    """
    prestamo = Prestamo.query.get_or_404(prestamo_id)

    if prestamo.estado != "ACTIVO":
        flash("Este préstamo no está en estado ACTIVO.", "warning")
        return redirect(url_for("admin.listar_prestamos"))

    prestamo.estado = "PENDIENTE_CONFIRMACION"
    db.session.commit()

    flash(
        f"Devolución registrada. Esperando confirmación del estudiante "
        f"{prestamo.estudiante.nombre}.",
        "info"
    )
    return redirect(url_for("admin.listar_prestamos"))


@admin_bp.route("/prestamos")
@login_required
@solo_bibliotecario
def listar_prestamos():
    """Lista todos los préstamos activos y pendientes de confirmación."""
    prestamos = Prestamo.query.filter(
        Prestamo.estado.in_(["ACTIVO", "PENDIENTE_CONFIRMACION"])
    ).order_by(Prestamo.fecha_prestamo.desc()).all()

    return render_template("admin/listar_prestamos.html", prestamos=prestamos)