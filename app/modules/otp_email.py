import secrets
import bcrypt
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from flask import current_app
from app import db
from app.models import OTPToken

def generar_otp():
    """
    Genera un OTP numérico de 6 dígitos criptográficamente seguro.
    Usa el módulo secrets (CSPRNG) en lugar de random, que NO es
    apto para uso criptográfico.

    secrets.randbelow(900000) produce un número entre 0 y 899999.
    Sumando 100000 garantizamos siempre 6 dígitos (100000-999999).
    """
    return str(secrets.randbelow(900000) + 100000)


def guardar_otp(estudiante_id, otp_plano):
    """
    Guarda el OTP en la BD de forma segura:
    - Invalida todos los OTPs anteriores del estudiante
    - Hashea el OTP con bcrypt antes de guardarlo
    - Registra el tiempo de expiración según config

    El OTP se hashea porque si alguien accede a la BD
    no debe poder extraer tokens válidos.
    """
    # Invalidar OTPs anteriores no usados del mismo estudiante
    OTPToken.query.filter_by(
        estudiante_id=estudiante_id,
        usado=False
    ).delete()

    # Calcular tiempo de expiración
    ahora = datetime.now(timezone.utc)
    minutos = current_app.config.get("OTP_EXPIRY_MINUTES", 5)
    expira = ahora + timedelta(minutes=minutos)

    # Hashear el OTP antes de guardarlo
    otp_hash = bcrypt.hashpw(
        otp_plano.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    token = OTPToken(
        estudiante_id=estudiante_id,
        token_hash=otp_hash,
        creado_en=ahora,
        expira_en=expira,
        usado=False,
        intentos_fallidos=0
    )

    db.session.add(token)
    db.session.commit()

    return token


def verificar_otp(estudiante_id, otp_ingresado):
    """
    Verifica el OTP ingresado por el estudiante:
    1. Busca el token activo más reciente del estudiante
    2. Verifica que no haya expirado
    3. Verifica que no supere el límite de intentos fallidos
    4. Compara con bcrypt
    5. Si es válido lo marca como usado (un solo uso)

    Retorna un diccionario con:
    - valido (bool): si el OTP fue aceptado
    - mensaje (str): razón del rechazo si no es válido
    """
    ahora = datetime.now(timezone.utc)
    max_intentos = current_app.config.get("MAX_OTP_ATTEMPTS", 3)

    # Buscar el OTP activo más reciente del estudiante
    token = OTPToken.query.filter_by(
        estudiante_id=estudiante_id,
        usado=False
    ).order_by(OTPToken.creado_en.desc()).first()

    if not token:
        return {"valido": False, "mensaje": "No hay código activo. Solicita uno nuevo."}

    # Verificar expiración
    expira_aware = token.expira_en.replace(tzinfo=timezone.utc) if token.expira_en.tzinfo is None else token.expira_en
    if ahora > expira_aware:
        return {"valido": False, "mensaje": "El código ha expirado. Solicita uno nuevo."}

    # Verificar límite de intentos
    if token.intentos_fallidos >= max_intentos:
        return {"valido": False, "mensaje": "Demasiados intentos fallidos. Solicita un nuevo código."}

    # Verificar el código con bcrypt
    es_valido = bcrypt.checkpw(
        otp_ingresado.encode("utf-8"),
        token.token_hash.encode("utf-8")
    )

    if es_valido:
        # Marcar como usado — no puede reutilizarse
        token.usado = True
        db.session.commit()
        return {"valido": True, "mensaje": "Código verificado correctamente."}
    else:
        # Registrar intento fallido
        token.intentos_fallidos += 1
        db.session.commit()
        restantes = max_intentos - token.intentos_fallidos
        return {
            "valido": False,
            "mensaje": f"Código incorrecto. Intentos restantes: {restantes}"
        }


def enviar_otp_correo(destinatario, nombre, otp_plano):
    """
    Envía el OTP al correo institucional del estudiante.
    Usa smtplib con TLS sobre el puerto 587.

    Retorna True si el correo se envió, False si hubo error.
    El error se registra en consola pero no se propaga al usuario
    para no revelar detalles internos del sistema de correo.
    """
    try:
        config = current_app.config

        # Construir el mensaje
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "BiblioAuth — Tu código de verificación"
        msg["From"]    = config["MAIL_SENDER"]
        msg["To"]      = destinatario

        # Cuerpo del correo en texto plano y HTML
        cuerpo_texto = f"""
Hola {nombre},

Tu código de verificación para BiblioAuth es:

{otp_plano}

Este código es válido por {config.get('OTP_EXPIRY_MINUTES', 5)} minutos.
Si no solicitaste este código, ignora este mensaje.

— Sistema BiblioAuth
        """

        cuerpo_html = f"""
<html>
<body style="font-family: Arial, sans-serif; max-width: 480px; margin: auto;">
  <div style="background: #003366; padding: 12px 20px; border-radius: 8px 8px 0 0;">
    <h2 style="color: white; margin: 0; font-size: 18px;">📚 BiblioAuth</h2>
  </div>
  <div style="background: white; padding: 24px; border: 1px solid #DADADA; border-top: none; border-radius: 0 0 8px 8px;">
    <p>Hola <strong style="color: #003366;">{nombre}</strong>,</p>
    <p style="color: #555;">Tu código de verificación es:</p>
    <div style="font-size: 36px; font-weight: bold; letter-spacing: 8px;
                background: #f4f4f4; padding: 20px; text-align: center;
                border-radius: 8px; color: #ad3333; border: 1px solid #DADADA;">
      {otp_plano}
    </div>
    <p style="color: #888; font-size: 13px; margin-top: 20px;">
      Válido por {config.get('OTP_EXPIRY_MINUTES', 5)} minutos.<br>
      Si no solicitaste este código, ignora este mensaje.
    </p>
  </div>
</body>
</html>
        """

        msg.attach(MIMEText(cuerpo_texto, "plain"))
        msg.attach(MIMEText(cuerpo_html, "html"))

        # Enviar usando SMTP con TLS
        with smtplib.SMTP(config["MAIL_SERVER"], config["MAIL_PORT"]) as servidor:
            servidor.ehlo()
            servidor.starttls()
            servidor.login(config["MAIL_USERNAME"], config["MAIL_PASSWORD"])
            servidor.sendmail(
                config["MAIL_SENDER"],
                destinatario,
                msg.as_string()
            )

        return True

    except Exception as e:
        print(f"[ERROR] Fallo al enviar correo a {destinatario}: {e}")
        return False


def generar_y_enviar_otp(estudiante):
    """
    Función principal que orquesta el flujo completo OTP del estudiante:
    1. Genera el OTP en texto plano
    2. Lo guarda hasheado en la BD
    3. Lo envía al correo institucional

    Retorna True si todo el proceso fue exitoso, False si el correo falló.
    """
    otp_plano = generar_otp()
    guardar_otp(estudiante.id, otp_plano)
    enviado = enviar_otp_correo(
        destinatario=estudiante.correo_institucional,
        nombre=estudiante.nombre.split()[0],  # Solo el primer nombre
        otp_plano=otp_plano
    )
    return enviado