from sqlalchemy.pool import NullPool
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from sqlalchemy import text
from twilio.rest import Client
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave-temporal-dev")

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "poolclass": NullPool,
        "connect_args": {"sslmode": "require"}
    }
else:
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

from flask_apscheduler import APScheduler

if os.environ.get("RENDER") is None:
    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()

    @scheduler.task("cron", id="aviso_dos_dias", hour=9)
    def tarea_aviso_dos_dias():
        with app.app_context():
            aviso_dos_dias_antes()


def enviar_whatsapp(telefono, mensaje):
    try:
        account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_whatsapp = os.environ.get("TWILIO_WHATSAPP_FROM")

        
        # 👇 ESTE PRINT ES EL QUE AGREGAS
        print("📲 FROM WHATSAPP:", from_whatsapp)
        client = Client(account_sid, auth_token)

        client.messages.create(
            from_=from_whatsapp,
            to=f"whatsapp:+52{telefono}",
            body=mensaje
        )

        print("✅ WhatsApp enviado correctamente")

    except Exception as e:
        print("❌ Error enviando WhatsApp:", e)

def aviso_dos_dias_antes():
    hoy = date.today()
    objetivo = hoy + timedelta(days=2)

    resultados = (
        db.session.query(Mensualidad, Cliente)
        .join(Cliente, Mensualidad.cliente_id == Cliente.id)
        .filter(
            Mensualidad.fecha_vencimiento == objetivo,
            Mensualidad.estado == "activo"
        )
        .all()
    )

    for mensualidad, cliente in resultados:
        mensaje = (
            f"⚠️ *YGM ARCADIA'S*\n\n"
            f"Hola *{cliente.nombre}* 👋\n\n"
            f"Tu mensualidad vence en *2 días* 📅\n"
            f"🗓 Fecha de vencimiento: {mensualidad.fecha_vencimiento.strftime('%d/%m/%Y')}\n\n"
            f"Sigue entrenando y nunca dejes el YGM ARCADIA'S💪"
        )

        enviar_whatsapp(cliente.telefono, mensaje)




class Cliente(db.Model):
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    telefono = db.Column(db.String(20), nullable=False)




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

    # 🔗 relación con cliente
    cliente_id = db.Column(
        db.Integer,
        db.ForeignKey("clientes.id", ondelete="CASCADE"),
        nullable=False
    )

    # 🔹 Datos duplicados para historial (NO se rompen aunque el cliente cambie)
    nombre = db.Column(db.String(50), nullable=False)
    apellidos = db.Column(db.String(80), nullable=False)

    monto = db.Column(db.Float, nullable=False)

    fecha_pago = db.Column(db.Date, nullable=False)
    fecha_vencimiento = db.Column(db.Date, nullable=False)

    # 📌 estado automático
    estado = db.Column(
        db.String(20),
        nullable=False,
        default="activo"
    )

    # 👇 relación ORM
    cliente = db.relationship(
        "Cliente",
        backref=db.backref("mensualidades", lazy=True)
    )



class Visita(db.Model):
    __tablename__ = "visitas"
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    monto = db.Column(db.Float, nullable=False)
    fecha = db.Column(db.Date, default=date.today)



def calcular_estado_mensualidad(mensualidad):
    hoy = date.today()

    if hoy > mensualidad.fecha_vencimiento:
        return "vencido"
    elif hoy >= mensualidad.fecha_vencimiento - timedelta(days=2):
        return "por_vencer"
    else:
        return "activo"





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
# -----------------------------
# RUTA DE TEST DB
# -----------------------------
from sqlalchemy import text

@app.route("/test-db")
def test_db():
    try:
        db.session.execute(text("SELECT 1"))
        return "Conexión a la base de datos exitosa ✅"
    except Exception as e:
        return f"Error: {e}"

@app.route("/admin/mensualidades", methods=["GET", "POST"])
def mensualidades():
    if "admin_id" not in session:
        return redirect(url_for("login"))

    hoy = date.today()
    registros = Mensualidad.query.order_by(Mensualidad.id.desc()).all()

    if request.method == "POST":
        # 📥 DATOS DEL FORMULARIO
        nombre = request.form.get("nombre").strip()
        apellidos = request.form.get("apellidos").strip()
        telefono = request.form.get("telefono").strip()

        monto = float(request.form.get("monto"))
        fecha_pago = datetime.strptime(
            request.form.get("fecha_pago"),
            "%Y-%m-%d"
        ).date()
        fecha_vencimiento = fecha_pago + timedelta(days=30)

        # 🔍 BUSCAR CLIENTE POR TELÉFONO (más confiable)
        cliente = Cliente.query.filter_by(telefono=telefono).first()

        # ➕ CREAR CLIENTE SI NO EXISTE
        if not cliente:
            cliente = Cliente(
                nombre=nombre,
                apellido=apellidos,
                telefono=telefono
            )
            db.session.add(cliente)
            db.session.commit()

        # ➕ CREAR MENSUALIDAD
        nueva = Mensualidad(
            cliente_id=cliente.id,
            nombre=cliente.nombre,
            apellidos=cliente.apellido,
            monto=monto,
            fecha_pago=fecha_pago,
            fecha_vencimiento=fecha_vencimiento,
            estado="activo"
        )
        db.session.add(nueva)
        db.session.commit()

        # 📲 MENSAJE WHATSAPP DE REGISTRO
        mensaje_registro = (
            f"🏋️‍♂️ *YGM ARCADIA'S*\n\n"
            f"Hola *{cliente.nombre}* 👋\n"
            f"Tu mensualidad fue registrada correctamente ✅\n\n"
            f"📅 Vence el: {fecha_vencimiento.strftime('%d/%m/%Y')}\n\n"
            f"¡Gracias por entrenar con nosotros 💪!"
        )
        enviar_whatsapp(cliente.telefono, mensaje_registro)

        flash("✅ Mensualidad registrada y WhatsApp enviado correctamente")
        return redirect(url_for("mensualidades"))

    # 🔔 Actualizar estado de mensualidades para avisos
    for m in registros:
        dias_restantes = (m.fecha_vencimiento - hoy).days
        if dias_restantes < 0:
            m.estado = "vencido"
        elif dias_restantes <= 2:
            m.estado = "por_vencer"
        else:
            m.estado = "activo"
    db.session.commit()

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

@app.route("/admin/mensualidades/total")
def total_mensualidades():
    if "admin_id" not in session:
        return {"total": 0}

    total = db.session.query(
        db.func.sum(Mensualidad.monto)
    ).scalar() or 0

    return {"total": round(total, 2)}



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


@app.route("/admin/visitas/total")
def total_visitas():
    if "admin_id" not in session:
        return {"total": 0}

    total = db.session.query(
        db.func.sum(Visita.monto)
    ).scalar() or 0

    return {"total": round(total, 2)}


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


@app.route("/admin/bebidas/total")
def total_bebidas():
    if "admin_id" not in session:    
        return {"total": 0}

    total = db.session.query(
        db.func.sum(Bebida.monto)
    ).scalar() or 0

    return {"total": round(total, 2)}

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