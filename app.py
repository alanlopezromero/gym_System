from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
import os
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask import request, redirect, url_for, session, flash
from flask import Flask, render_template, request, redirect, url_for, session


# Cargar .env SOLO en local (en Render no se usa)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

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

# -----------------------------
# MODELOS DE LA BASE DE DATOS
# -----------------------------
class Usuario(db.Model):
    __tablename__ = "usuarios"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    contrasena = db.Column(db.String(100), nullable=False)

    pagos = db.relationship("Pago", backref="usuario", lazy=True)


class Membresia(db.Model):
    __tablename__ = "membresias"
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(50), nullable=False)
    precio = db.Column(db.Float, nullable=False)

    pagos = db.relationship("Pago", backref="membresia", lazy=True)


class Pago(db.Model):
    __tablename__ = "pagos"
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(
        db.Integer, db.ForeignKey("usuarios.id"), nullable=False
    )
    membresia_id = db.Column(
        db.Integer, db.ForeignKey("membresias.id"), nullable=False
    )
    fecha = db.Column(db.DateTime, default=datetime.utcnow)


class Admin(db.Model):
    __tablename__ = "admins"
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


# -----------------------------
# RUTAS
# -----------------------------
@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]

        admin = Admin.query.filter_by(usuario=usuario).first()

        if admin and check_password_hash(admin.password, password):
            session["admin_id"] = admin.id
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Credenciales incorrectas")

    return render_template("admin/login.html")

from werkzeug.security import check_password_hash

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form["usuario"]
        password = request.form["password"]

        admin = Admin.query.filter_by(usuario=usuario).first()

        if admin and check_password_hash(admin.password, password):
            session["admin_id"] = admin.id
            return redirect(url_for("panel_admin"))
        else:
            return "Usuario o contraseña incorrectos ❌"

    return render_template("login.html")

@app.route("/admin")
def panel_admin():
    if "admin_id" not in session:
        return redirect(url_for("login"))
    return render_template("admin.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))



@app.route("/admin")
def admin_dashboard():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))

    return render_template("admin/dashboard.html")




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
