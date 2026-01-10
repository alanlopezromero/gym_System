from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from datetime import date, timedelta
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

class Bebida(db.Model):
    __tablename__ = "bebidas"
    id = db. Column(db.Integer,primary_key=True)
    nombre_producto = db.Column(db.String(50), nullable=False)
    produc_cantidad = db.Column(db.Integer, nullable=False)
    monto = db.Column(db.Float,nullable=False)

class Producto(db.Model):
    __tablename__ = "productos"
    id = db.Column(db.Integer, primary_key=True)
    nombre_producto = db.Column(db.String(100), nullable=False)
    produc_cantidad = db.Column(db.Integer, nullable=False)
    monto = db.Column(db.Float, nullable=False)



class Admin(db.Model):
    __tablename__ = "admins"
    id = db.Column(db.Integer, primary_key=True)
    usuario = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Mensualidad(db.Model):
    __tablename__ = "mensualidades"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    apellidos = db.Column(db.String(80), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha_pago = db.Column(db.Date, nullable=False)
    fecha_vencimiento = db.Column(db.Date, nullable=False)

class Visita(db.Model):
    __tablename__ = "visitas"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.Date, default=date.today)



with app.app_context():
    db.create_all()


from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()

    admin = Admin.query.filter_by(usuario="admin").first()
    if not admin:
        admin = Admin(
            usuario="admin",
            password=generate_password_hash("admin123")
        )
        db.session.add(admin)
        db.session.commit()
        print("✅ Admin creado")



# -----------------------------
# RUTAS
# -----------------------------

# Página principal (BIENVENIDA)
@app.route("/")
def index():
    return render_template("index.html")


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
    


@app.route("/admin/mensualidades", methods=["GET", "POST"])
def mensualidades():
    if "admin_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        nombre = request.form["nombre"]
        apellidos = request.form["apellidos"]
        monto = request.form["monto"]
        fecha_pago = datetime.strptime(request.form["fecha_pago"], "%Y-%m-%d").date()

        fecha_vencimiento = fecha_pago + timedelta(days=30)

        nueva = Mensualidad(
            nombre=nombre,
            apellidos=apellidos,
            monto=monto,
            fecha_pago=fecha_pago,
            fecha_vencimiento=fecha_vencimiento
        )
        db.session.add(nueva)
        db.session.commit()

    hoy = date.today()
    registros = Mensualidad.query.all()

    return render_template(
        "admin/mensualidades.html",
        registros=registros,
        hoy=hoy
    )
@app.route("/admin/mensualidades/eliminar/<int:id>", methods=["POST"])
def eliminar_mensualidad(id):
    if "admin_id" not in session:
        return redirect(url_for("login"))

    mensualidad = Mensualidad.query.get_or_404(id)
    db.session.delete(mensualidad)
    db.session.commit()

    return redirect(url_for("mensualidades"))


@app.route("/admin/visitas", methods=["GET", "POST"])
def visitas():
    if "admin_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        visita = Visita(
            nombre=request.form["nombre"],
            monto=request.form["monto"]
        )
        db.session.add(visita)
        db.session.commit()

    visitas = Visita.query.all()
    return render_template("admin/visitas.html", visitas=visitas)

@app.route("/admin/visitas/eliminar/<int:id>", methods=["POST"])
def eliminar_visita(id):
    if "admin_id" not in session:
        return redirect(url_for("login"))

    visita = Visita.query.get_or_404(id)
    db.session.delete(visita)
    db.session.commit()

    return redirect(url_for("visitas"))

@app.route("/admin/bebidas", methods=["GET", "POST"])
def bebidas_view():
    if "admin_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        nombre = request.form["producto"]
        cantidad = request.form["cantidad"]
        monto = float(request.form["precio"])


        nueva_bebida = Bebida(
            nombre_producto=nombre,
            produc_cantidad=cantidad,
            monto=monto
        )

        db.session.add(nueva_bebida)
        db.session.commit()

        return redirect(url_for("bebidas_view"))

    registros = Bebida.query.order_by(Bebida.id.desc()).all()

    return render_template(
        "admin/bebidas.html",
        registros=registros
    )

@app.route("/admin/bebidas/eliminar/<int:id>", methods=["POST"])
def eliminar_bebida(id):
    if "admin_id" not in session:
        return redirect(url_for("login"))

    bebida = Bebida.query.get_or_404(id)
    db.session.delete(bebida)
    db.session.commit()

    return redirect(url_for("bebidas_view"))

@app.route("/admin/productos", methods=["GET", "POST"])
def productos_view():
    if "admin_id" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":
        nombre = request.form["producto"]
        cantidad = request.form["cantidad"]
        monto = float(request.form["precio"])

        nuevo_producto = Producto(
            nombre_producto=nombre,
            produc_cantidad=cantidad,
            monto=monto
        )

        db.session.add(nuevo_producto)
        db.session.commit()

        return redirect(url_for("productos_view"))

    registros = Producto.query.order_by(Producto.id.desc()).all()

    return render_template(
        "admin/productos.html",
        registros=registros
    )

@app.route("/admin/productos/eliminar/<int:id>", methods=["POST"])
def eliminar_producto(id):
    if "admin_id" not in session:
        return redirect(url_for("login"))

    producto = Producto.query.get_or_404(id)
    db.session.delete(producto)
    db.session.commit()

    return redirect(url_for("productos_view"))




# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
