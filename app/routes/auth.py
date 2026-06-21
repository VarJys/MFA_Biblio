from flask import (Blueprint, render_template, redirect,
                   url_for, request, flash, session)
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models import Estudiante, Bibliotecario
from app.modules.totp import (verificar_totp, activar_totp_bibliotecario,
                               confirmar_activacion_totp)
from app.modules.otp_email import generar_y_enviar_otp, verificar_otp
import bcrypt

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


# ─────────────────────────────────────────────
#  RUTAS COMPARTIDAS
# ─────────────────────────────────────────────

@auth_bp.route("/")
def index():
    """Ruta raíz — redirige según el tipo de usuario."""
    return redirect(url_for("auth.elegir_portal"))


@auth_bp.route("/portal", methods=["GET", "POST"])
def elegir_portal():
    """Pantalla de inicio unificada con login y toggle de rol."""
    if request.method == "POST":
        identificador = request.form.get("identificador", "").strip()
        password      = request.form.get("password", "").strip()
        rol           = request.form.get("rol", "").strip()

        if rol == "bibliotecario":
            bibliotecario = Bibliotecario.query.filter_by(
                usuario=identificador
            ).first()

            if not bibliotecario or not bcrypt.checkpw(
                password.encode("utf-8"),
                bibliotecario.password_hash.encode("utf-8")
            ):
                flash("Usuario o contraseña incorrectos.", "danger")
                return render_template("auth/portal.html")

            session["bibliotecario_pre_auth"] = bibliotecario.id

            if not bibliotecario.totp_activo:
                return redirect(url_for("auth.setup_totp"))

            return redirect(url_for("auth.verificar_totp_view"))

        elif rol == "estudiante":
            estudiante = Estudiante.query.filter_by(
                codigo_estudiantil=identificador
            ).first()

            if not estudiante or not bcrypt.checkpw(
                password.encode("utf-8"),
                estudiante.password_hash.encode("utf-8")
            ):
                flash("Código estudiantil o contraseña incorrectos.", "danger")
                return render_template("auth/portal.html")

            if estudiante.estado != "ACTIVO":
                flash("Tu cuenta no está activa. Contacta a la biblioteca.", "warning")
                return render_template("auth/portal.html")

            session["estudiante_pre_auth"] = estudiante.id

            enviado = generar_y_enviar_otp(estudiante)
            if enviado:
                flash(
                    f"Se envió un código a {estudiante.correo_institucional}.",
                    "info"
                )
            else:
                flash("No se pudo enviar el correo. Intenta de nuevo.", "danger")
                return render_template("auth/portal.html")

            return redirect(url_for("auth.verificar_otp_view"))

        else:
            flash("Rol no válido.", "danger")
            return render_template("auth/portal.html")

    return render_template("auth/portal.html")


@auth_bp.route("/logout")
@login_required
def logout():
    """Cierra la sesión activa y limpia variables de sesión."""
    session.clear()
    logout_user()
    flash("Sesión cerrada correctamente.", "info")
    return redirect(url_for("auth.elegir_portal"))


# ─────────────────────────────────────────────
#  RUTAS DEL BIBLIOTECARIO
# ─────────────────────────────────────────────

@auth_bp.route("/bibliotecario/login", methods=["GET", "POST"])
def login_bibliotecario():
    """Redirige al login unificado."""
    return redirect(url_for("auth.elegir_portal"))


@auth_bp.route("/bibliotecario/setup-totp", methods=["GET", "POST"])
def setup_totp():
    """
    Primera vez que el bibliotecario inicia sesión:
    - GET:  genera el QR y lo muestra para escanear
    - POST: verifica el primer código para confirmar que la app quedó bien configurada
    """
    bibliotecario_id = session.get("bibliotecario_pre_auth")
    if not bibliotecario_id:
        return redirect(url_for("auth.login_bibliotecario"))

    bibliotecario = Bibliotecario.query.get(bibliotecario_id)

    if request.method == "POST":
        codigo = request.form.get("codigo_totp", "").strip()

        if confirmar_activacion_totp(bibliotecario, codigo):
            flash("Autenticador configurado correctamente. Ahora inicia sesión.", "success")
            return redirect(url_for("auth.verificar_totp_view"))

        flash("Código incorrecto. Asegúrate de haber escaneado el QR correctamente.", "danger")

    # Generar QR (si ya tiene secret lo reutiliza, si no lo genera)
    datos_totp = activar_totp_bibliotecario(bibliotecario)

    return render_template(
        "auth/setup_totp.html",
        qr_base64=datos_totp["qr_base64"],
        secret=datos_totp["secret"]
    )


@auth_bp.route("/bibliotecario/verificar-totp", methods=["GET", "POST"])
def verificar_totp_view():
    """
    Paso 2 del login del bibliotecario: verificación del código TOTP.
    Si el código es válido, se emite la sesión completa con Flask-Login.
    """
    bibliotecario_id = session.get("bibliotecario_pre_auth")
    if not bibliotecario_id:
        return redirect(url_for("auth.login_bibliotecario"))

    if request.method == "POST":
        codigo = request.form.get("codigo_totp", "").strip()
        bibliotecario = Bibliotecario.query.get(bibliotecario_id)

        if verificar_totp(bibliotecario.totp_secret, codigo):
            # Limpiar variable de pre-autenticación
            session.pop("bibliotecario_pre_auth", None)
            session["rol"] = "bibliotecario"

            login_user(bibliotecario)
            flash(f"Bienvenido, {bibliotecario.usuario}.", "success")
            return redirect(url_for("admin.dashboard"))

        flash("Código TOTP incorrecto o expirado.", "danger")

    return render_template("auth/verificar_totp.html")


# ─────────────────────────────────────────────
#  RUTAS DEL ESTUDIANTE
# ─────────────────────────────────────────────

@auth_bp.route("/estudiante/login", methods=["GET", "POST"])
def login_estudiante():
    """Redirige al login unificado."""
    return redirect(url_for("auth.elegir_portal"))


@auth_bp.route("/estudiante/verificar-otp", methods=["GET", "POST"])
def verificar_otp_view():
    """
    Paso 2 del login del estudiante: verificación del OTP recibido por correo.
    Si el código es válido, se emite la sesión completa con Flask-Login.
    """
    estudiante_id = session.get("estudiante_pre_auth")
    if not estudiante_id:
        return redirect(url_for("auth.login_estudiante"))

    if request.method == "POST":
        otp_ingresado = request.form.get("otp", "").strip()
        resultado     = verificar_otp(estudiante_id, otp_ingresado)

        if resultado["valido"]:
            estudiante = Estudiante.query.get(estudiante_id)
            session.pop("estudiante_pre_auth", None)
            session["rol"] = "estudiante"

            login_user(estudiante)
            flash(f"Bienvenido, {estudiante.nombre.split()[0]}.", "success")
            return redirect(url_for("prestamos.mis_prestamos"))

        flash(resultado["mensaje"], "danger")

    return render_template("auth/verificar_otp.html")