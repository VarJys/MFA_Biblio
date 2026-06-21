from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime, timezone

# Flask-Login necesita saber cómo cargar un usuario desde la BD
# Este loader se usa internamente para verificar sesiones activas
@login_manager.user_loader
def load_user(user_id):
    # Intentar cargar primero como estudiante, luego como bibliotecario
    estudiante = Estudiante.query.get(int(user_id))
    if estudiante:
        return estudiante
    return Bibliotecario.query.get(int(user_id))


class Estudiante(UserMixin, db.Model):
    __tablename__ = "estudiantes"

    id                   = db.Column(db.Integer, primary_key=True)
    codigo_estudiantil   = db.Column(db.String(20), unique=True, nullable=False)
    nombre               = db.Column(db.String(100), nullable=False)
    correo_institucional = db.Column(db.String(120), unique=True, nullable=False)
    password_hash        = db.Column(db.String(255), nullable=False)
    estado               = db.Column(db.String(10), nullable=False, default="ACTIVO")
    carrera              = db.Column(db.String(100), nullable=True)
    creado_en            = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relaciones
    prestamos  = db.relationship("Prestamo", backref="estudiante", lazy=True)
    otp_tokens = db.relationship("OTPToken", backref="estudiante", lazy=True)

    def __repr__(self):
        return f"<Estudiante {self.codigo_estudiantil} — {self.nombre}>"


class Bibliotecario(UserMixin, db.Model):
    __tablename__ = "bibliotecarios"

    id           = db.Column(db.Integer, primary_key=True)
    usuario      = db.Column(db.String(50), unique=True, nullable=False)
    password_hash= db.Column(db.String(255), nullable=False)
    totp_secret  = db.Column(db.String(32), nullable=True)
    totp_activo  = db.Column(db.Boolean, default=False)
    creado_en    = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relaciones
    prestamos = db.relationship("Prestamo", backref="bibliotecario", lazy=True)

    def __repr__(self):
        return f"<Bibliotecario {self.usuario}>"


class Libro(db.Model):
    __tablename__ = "libros"

    id               = db.Column(db.Integer, primary_key=True)
    titulo           = db.Column(db.String(200), nullable=False)
    autor            = db.Column(db.String(150), nullable=False)
    isbn             = db.Column(db.String(20), unique=True, nullable=True)
    disponible       = db.Column(db.Boolean, default=True)
    categoria        = db.Column(db.String(80), nullable=True)
    total_ejemplares = db.Column(db.Integer, default=1)
    creado_en        = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Relaciones
    prestamos = db.relationship("Prestamo", backref="libro", lazy=True)

    def __repr__(self):
        return f"<Libro {self.titulo}>"


class Prestamo(db.Model):
    __tablename__ = "prestamos"

    id                    = db.Column(db.Integer, primary_key=True)
    estudiante_id         = db.Column(db.Integer, db.ForeignKey("estudiantes.id"), nullable=False)
    libro_id              = db.Column(db.Integer, db.ForeignKey("libros.id"), nullable=False)
    bibliotecario_id      = db.Column(db.Integer, db.ForeignKey("bibliotecarios.id"), nullable=False)

    # Estados posibles: ACTIVO, PENDIENTE_CONFIRMACION, DEVUELTO, VENCIDO
    estado                = db.Column(db.String(30), nullable=False, default="ACTIVO")

    fecha_prestamo        = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    fecha_devolucion_esp  = db.Column(db.DateTime, nullable=True)
    fecha_devolucion_real = db.Column(db.DateTime, nullable=True)
    confirmado_estudiante = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Prestamo libro={self.libro_id} estudiante={self.estudiante_id} estado={self.estado}>"


class OTPToken(db.Model):
    __tablename__ = "otp_tokens"

    id              = db.Column(db.Integer, primary_key=True)
    estudiante_id   = db.Column(db.Integer, db.ForeignKey("estudiantes.id"), nullable=False)
    token_hash      = db.Column(db.String(255), nullable=False)
    creado_en       = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    expira_en       = db.Column(db.DateTime, nullable=False)
    usado           = db.Column(db.Boolean, default=False)
    intentos_fallidos = db.Column(db.Integer, default=0)

    def __repr__(self):
        return f"<OTPToken estudiante={self.estudiante_id} usado={self.usado}>"