import pyotp
import qrcode
import io
import base64
from app import db

# Nombre que aparece en Google Authenticator al escanear el QR
NOMBRE_EMISOR = "BiblioAuth"

def generar_secret():
    """
    Genera una clave secreta aleatoria de 32 caracteres en base32.
    Esta clave se guarda en la BD y se comparte con Google Authenticator
    al momento del registro del bibliotecario.
    Nunca debe exponerse después del registro inicial.
    """
    return pyotp.random_base32()


def generar_uri_totp(secret, usuario):
    """
    Genera la URI estándar otpauth:// que codifica el QR.
    Google Authenticator lee esta URI al escanear el código QR
    y configura automáticamente la generación de TOTP.

    Formato: otpauth://totp/BiblioAuth:usuario?secret=XXX&issuer=BiblioAuth
    """
    totp = pyotp.TOTP(secret)
    return totp.provisioning_uri(
        name=usuario,
        issuer_name=NOMBRE_EMISOR
    )


def generar_qr_base64(secret, usuario):
    """
    Genera el código QR como imagen PNG codificada en base64.
    Se devuelve como string para incrustarla directamente en HTML:
    <img src="data:image/png;base64,{{ qr_base64 }}">

    Esto evita guardar la imagen en disco.
    """
    uri = generar_uri_totp(secret, usuario)

    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=6,
        border=4,
    )
    qr.add_data(uri)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    # Convertir imagen a bytes en memoria sin guardar en disco
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)

    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def verificar_totp(secret, codigo_ingresado):
    """
    Verifica si el código ingresado por el bibliotecario es válido.

    PyOTP compara el código contra el intervalo actual y los dos
    intervalos adyacentes (±30 segundos) para tolerar pequeñas
    diferencias de reloj entre el servidor y el dispositivo.

    Retorna True si el código es válido, False si no lo es.
    """
    if not secret or not codigo_ingresado:
        return False

    totp = pyotp.TOTP(secret)

    # valid_window=1 permite un intervalo de tolerancia de ±30 segundos
    return totp.verify(codigo_ingresado, valid_window=1)


def activar_totp_bibliotecario(bibliotecario):
    """
    Flujo completo de activación TOTP para un bibliotecario nuevo:
    1. Genera la clave secreta
    2. La guarda en la BD
    3. Retorna el QR en base64 para mostrarlo en pantalla

    Se llama la primera vez que el bibliotecario inicia sesión.
    Después de escanear el QR, totp_activo se marca como True.
    """
    secret = generar_secret()

    bibliotecario.totp_secret = secret
    db.session.commit()

    qr_base64 = generar_qr_base64(secret, bibliotecario.usuario)

    return {
        "secret": secret,
        "qr_base64": qr_base64
    }


def confirmar_activacion_totp(bibliotecario, codigo_ingresado):
    """
    El bibliotecario escanea el QR e ingresa el primer código
    para confirmar que la app quedó configurada correctamente.
    Solo después de esta confirmación se marca totp_activo = True.

    Retorna True si la activación fue exitosa, False si el código
    no coincide (QR mal escaneado o clock skew excesivo).
    """
    if verificar_totp(bibliotecario.totp_secret, codigo_ingresado):
        bibliotecario.totp_activo = True
        db.session.commit()
        return True
    return False