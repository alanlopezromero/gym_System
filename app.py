from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# -----------------------------
# CONFIGURACIÓN
# -----------------------------

# -----------------------------
# MODELOS
# -----------------------------

app = Flask(__name__)
app.secret_key = "clave_super_secreta"


app.secret_key = os.environ.get("SECRET_KEY", "clave-temporal-dev")


# Detecta la base de datos en Render o usa SQLite local
DATABASE_URL = os.environ.get("DATABASE_URL")

# Compatibilidad con SQLAlchemy
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL or "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    contrasena = db.Column(db.String(200), nullable=False)

class Membresia(db.Model):
    __tablename__ = "membresias"
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)
    precio = db.Column(db.Float, nullable=False)

class Pago(db.Model):
    __tablename__ = "pagos"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False)
    membresia_id = db.Column(db.Integer, db.ForeignKey("membresias.id"), nullable=False)
    fecha = db.Column(db.DateTime, default=datetime.utcnow)

class Admin(db.Model):
    __tablename__ = "admins"
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

with app.app_context():
    db.create_all()


# -----------------------------
# RUTAS
# -----------------------------

# Página principal (BIENVENIDA)
@app.route("/")
def index():
    return render_template("index.html")

# Login admin
# Login admin
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]

        admin = Admin.query.filter_by(usuario=usuario).first()

        if admin and check_password_hash(admin.password, password):
            session["admin_id"] = admin.id
            return redirect(url_for("admin_dashboard"))  # ✅ AQUÍ
        else:
            flash("Usuario o contraseña incorrectos ❌")

    return render_template("login.html")


# Panel admin (PROTEGIDO)
@app.route("/admin")
def admin_dashboard():
    if "admin_id" not in session:
        return redirect(url_for("login"))

    return render_template("admin/dashboard.html")

# Cerrar sesión
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# Test DB
@app.route("/test-db")
def test_db():
    try:
        db.session.execute("SELECT 1")
        return "Conexión a la base de datos exitosa ✅"
    except Exception as e:
        return f"Error: {e}"

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
