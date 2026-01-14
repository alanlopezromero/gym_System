from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
import os
import re  # Asegúrate de tener esto al inicio del archivo
from flask_mail import Mail, Message
from flask import Flask
from flask_mail import Mail
# -----------------------------
# CONFIGURACIÓN
# -----------------------------

# -----------------------------
# MODELOs
# -----------------------------

app = Flask(__name__)




# -----------------------------
# SECRET KEY
# -----------------------------
app.secret_key = os.environ.get("SECRET_KEY", "clave-temporal-dev")

# -----------------------------
# BASE DE DATOS
# -----------------------------
DATABASE_URL = os.environ.get("DATABASE_URL")

# Para compatibilidad con Heroku/Render PostgreSQL
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL or "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# -----------------------------
# CORREO (Flask-Mail)
# -----------------------------
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True       # TLS para puerto 587
app.config['MAIL_USE_SSL'] = False      # No usar SSL si TLS está activo
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')  # correo
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')  # contraseña de app
app.config['MAIL_DEFAULT_SENDER'] = ("Gym System", os.environ.get('MAIL_USERNAME'))

mail = Mail(app)

def enviar_correo(destinatario, asunto, nombre=None, fecha_vencimiento=None, mensaje_personalizado=None):
    """
    Envía un correo usando Flask-Mail.

    Parámetros:
    - destinatario: str, email del usuario
    - asunto: str, asunto del correo
    - nombre: str, nombre del usuario (opcional)
    - fecha_vencimiento: str, fecha de vencimiento (opcional)
    - mensaje_personalizado: str, si quieres enviar un mensaje diferente al predeterminado
    """
    try:
        if mensaje_personalizado:
            cuerpo = mensaje_personalizado
        elif nombre and fecha_vencimiento:
            cuerpo = f"""
Hola {nombre},

Hemos recibido tu pago de mensualidad.
Tu próxima fecha de vencimiento es: {fecha_vencimiento}

Gracias por tu preferencia.
            """
        else:
            cuerpo = "Este es un mensaje automático de tu sistema."

        msg = Message(
            subject=asunto,
            recipients=[destinatario],
            body=cuerpo,
            sender=app.config['MAIL_DEFAULT_SENDER']
        )

        mail.send(msg)
        print(f"✅ Correo enviado a {destinatario}")
    except Exception as e:
        print(f"❌ Error al enviar correo a {destinatario}: {e}")

def revisar_mensualidades():
    hoy = date.today()
    mensualidades = Mensualidad.query.all()

    for m in mensualidades:
        dias_restantes = (m.fecha_vencimiento - hoy).days

        if dias_restantes == 2:
            # ⚠️ 2 días antes
            enviar_correo(
                destinatario=m.cliente.email,
                asunto="⚠️ Tu membresía está por vencer",
                mensaje_personalizado=f"Hola {m.cliente.nombre}, tu membresía vence el {m.fecha_vencimiento.strftime('%d/%m/%Y')}. ¡Renueva a tiempo!"
            )
        elif dias_restantes == 0:
            # ❌ Día de vencimiento
            enviar_correo(
                destinatario=m.cliente.email,
                asunto="❌ Tu membresía vence hoy",
                mensaje_personalizado=f"Hola {m.cliente.nombre}, tu membresía vence hoy ({m.fecha_vencimiento.strftime('%d/%m/%Y')}). Por favor acude a renovación."
            )


class Cliente(db.Model):
    __tablename__ = "clientes"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False, unique=True)



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


from werkzeug.security import generate_password_hash

with app.app_context():
    db.create_all()

    admin = Admin.query.filter_by(usuario="adminJuan").first()
    if not admin:
        admin = Admin(
            usuario="adminJuan",
            password=generate_password_hash("system58")
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
        nombre = request.form.get("nombre").strip()
        apellidos = request.form.get("apellidos").strip()
        email = request.form.get("email").strip().lower()  # Nuevo campo

        # ✅ VALIDACIÓN DEL EMAIL
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash("❌ Email inválido")
            return redirect(url_for("mensualidades"))

        monto = float(request.form.get("monto"))
        fecha_pago = datetime.strptime(request.form.get("fecha_pago"), "%Y-%m-%d").date()
        fecha_vencimiento = fecha_pago + timedelta(days=30)

        # 🔒 BUSCAR CLIENTE EXISTENTE POR EMAIL
        cliente = Cliente.query.filter_by(email=email).first()
        if not cliente:
            cliente = Cliente(nombre=nombre, apellido=apellidos, email=email)
            db.session.add(cliente)
            db.session.commit()  # ID real

        # 🔒 CREAR MENSUALIDAD
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

        # 🔹 ENVIAR CORREO INMEDIATO
        asunto = "✅ Membresía YGM activa"
        enviar_correo(
            destinatario=cliente.email,
            asunto=asunto,
            nombre=cliente.nombre,
            fecha_vencimiento=fecha_vencimiento.strftime('%d/%m/%Y')
        )

        flash("✅ Mensualidad registrada y correo enviado al cliente")
        return redirect(url_for("mensualidades"))

    return render_template("admin/mensualidades.html", registros=registros, hoy=hoy)




def revisar_mensualidades():
    hoy = date.today()
    mensualidades = Mensualidad.query.all()

    for m in mensualidades:
        dias_restantes = (m.fecha_vencimiento - hoy).days

        if dias_restantes == 2:
            # Recordatorio 2 días antes
            enviar_correo(
                m.cliente.email,
                "⚠️ Tu membresía está por vencer",
                f"Hola {m.cliente.nombre}, tu membresía vence el {m.fecha_vencimiento.strftime('%d/%m/%Y')}. ¡Renueva a tiempo!"
            )
        elif dias_restantes == 0:
            # Vencimiento hoy
            enviar_correo(
                m.cliente.email,
                "❌ Tu membresía vence hoy",
                f"Hola {m.cliente.nombre}, tu membresía vence hoy ({m.fecha_vencimiento.strftime('%d/%m/%Y')}). Por favor acude a renovación."
            )


from flask_apscheduler import APScheduler

scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

@scheduler.task('cron', id='revisar_mensualidades', hour=8)
def tarea_diaria():
    with app.app_context():
        revisar_mensualidades()


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
