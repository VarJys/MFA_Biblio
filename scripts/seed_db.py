import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import create_app, db
from app.models import Estudiante, Bibliotecario, Libro
import bcrypt

app = create_app()

def hashear(password):
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

def seed():
    with app.app_context():
        try:
            print("Limpiando datos existentes...")
            db.session.query(Estudiante).delete()
            db.session.query(Bibliotecario).delete()
            db.session.query(Libro).delete()
            db.session.commit()
            print("  OK — tablas limpias")

            print("Insertando estudiantes...")
            estudiantes = [
                Estudiante(
                    codigo_estudiantil="2021-1045",
                    nombre="Laura Gómez",
                    correo_institucional="l.gomez@univ.edu.co",
                    password_hash=hashear("laura123"),
                    estado="ACTIVO",
                    carrera="Ingeniería de Sistemas"
                ),
                Estudiante(
                    codigo_estudiantil="202301",
                    nombre="Jeyson Varela  ",
                    correo_institucional="varelajeyson44@gmail.com",
                    password_hash=hashear("jeyson123"),
                    estado="ACTIVO",
                    carrera="Derecho"
                ),
                Estudiante(
                    codigo_estudiantil="2018-0071",
                    nombre="María Suárez",
                    correo_institucional="m.suarez@univ.edu.co",
                    password_hash=hashear("maria123"),
                    estado="INACTIVO",
                    carrera="Medicina"
                ),
                Estudiante(
                    codigo_estudiantil="2022-1190",
                    nombre="Wilson Rojas",
                    correo_institucional="w.rojas@univ.edu.co",
                    password_hash=hashear("wilson123"),
                    estado="ACTIVO",
                    carrera="Contaduría"
                ),
            ]
            db.session.add_all(estudiantes)
            db.session.commit()
            print(f"  OK — {len(estudiantes)} estudiantes insertados")

            print("Insertando bibliotecario...")
            bibliotecario = Bibliotecario(
                usuario="admin_biblioteca",
                password_hash=hashear("admin123"),
                totp_activo=False
            )
            db.session.add(bibliotecario)
            db.session.commit()
            print("  OK — bibliotecario creado: admin_biblioteca / admin123")

            print("Insertando libros...")
            libros = [
                Libro(titulo="Redes de Computadores", autor="Andrew Tanenbaum",
                      isbn="978-0132126953", disponible=True, categoria="Tecnología"),
                Libro(titulo="Ingeniería de Software", autor="Ian Sommerville",
                      isbn="978-0133943030", disponible=True, categoria="Tecnología"),
                Libro(titulo="El Quijote", autor="Miguel de Cervantes",
                      isbn="978-8467032109", disponible=True, categoria="Literatura"),
                Libro(titulo="Cálculo Diferencial", autor="James Stewart",
                      isbn="978-6074816600", disponible=True, categoria="Matemáticas"),
                Libro(titulo="Sistemas Operativos Modernos", autor="Andrew Tanenbaum",
                      isbn="978-6074428155", disponible=False, categoria="Tecnología"),
            ]
            db.session.add_all(libros)
            db.session.commit()
            print(f"  OK — {len(libros)} libros insertados")

            print("\n✓ BD inicializada correctamente")

        except Exception as e:
            db.session.rollback()
            print(f"\n✗ Error durante el seed: {e}")
            raise

if __name__ == "__main__":
    seed()