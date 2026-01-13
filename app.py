from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from datetime import date, timedelta
from flask import Flask, request, redirect, url_for, render_template
from generar_qr import generar_qr_cliente
from flask import url_for
import os
import qrcode






# -----------------------------
# CONFIGURACIÓN
# -----------------------------

# -----------------------------
# MODELOs
# -----------------------------

app = Flask(__name__)



app.secret_key = os.environ.get("SECRET_KEY", "clave-temporal-dev")


# Detecta la base de datos en Render o usa SQLite local
DATABASE_URL = os.environ.get("DATABASE_URL")

# Compatibilidad con SQLAlchemy
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL or "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

from flask_mail import Mail, Message

# Configuración de correo (usa tu SMTP real)
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')  # tu correo
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')  # contraseña de app

mail = Mail(app)

def enviar_correo_alerta(cliente_email, asunto, mensaje):
    try:
        msg = Message(
            subject=asunto,
            recipients=[cliente_email],
            body=mensaje,
            sender=app.config['MAIL_USERNAME']
        )
        mail.send(msg)
        print(f"✅ Correo enviado a {cliente_email}")
    except Exception as e:
        print(f"❌ Error al enviar correo a {cliente_email}: {e}")

def revisar_mensualidades():
    hoy = date.today()
    mensualidades = Mensualidad.query.all()

    for m in mensualidades:
        dias_restantes = (m.fecha_vencimiento - hoy).days

        if dias_restantes == 2:
            # ⚠️ 2 días antes
            enviar_correo_alerta(
                m.cliente.email,
                "⚠️ Tu membresía está por vencer",
                f"Hola {m.cliente.nombre}, tu membresía vence el {m.fecha_vencimiento.strftime('%d/%m/%Y')}. ¡Renueva a tiempo!"
            )
        elif dias_restantes == 0:
            # ❌ Día de vencimiento
            enviar_correo_alerta(
                m.cliente.email,
                "❌ Tu membresía vence hoy",
                f"Hola {m.cliente.nombre}, tu membresía vence hoy ({m.fecha_vencimiento.strftime('%d/%m/%Y')}). Por favor acude a renovación."
            )

class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)      # <-- Cambiado a True
    password_hash = db.Column(db.String(256), nullable=True)            # <-- Cambiado a True

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)


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
        db.ForeignKey("clientes.id"),
        nullable=False
    )

    nombre = db.Column(db.String(50), nullable=False)
    apellidos = db.Column(db.String(80), nullable=False)
    monto = db.Column(db.Float, nullable=False)

    fecha_pago = db.Column(db.Date, nullable=False)
    fecha_vencimiento = db.Column(db.Date, nullable=False)

    # 📌 estado automático
    estado = db.Column(
        db.String(20),
        default="activo"
    )

    # 👇 relación ORM (no afecta nada existente)
    cliente = db.relationship("Cliente", backref="mensualidades")


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

    hoy = date.today()
    registros = Mensualidad.query.all()

    if request.method == "POST":
        nombre = request.form.get("nombre")
        apellidos = request.form.get("apellidos")
        monto = float(request.form.get("monto"))
        fecha_pago = datetime.strptime(request.form.get("fecha_pago"), "%Y-%m-%d").date()
        fecha_vencimiento = fecha_pago + timedelta(days=30)

        # 🔹 Buscar cliente por nombre + apellido
        cliente = Cliente.query.filter_by(nombre=nombre, apellido=apellidos).first()

        if not cliente:
            # 🔹 Crear cliente temporal sin correo ni contraseña
            cliente = Cliente(
                nombre=nombre,
                apellido=apellidos,
                email=None,
                password_hash=None
            )
            db.session.add(cliente)
            db.session.commit()  # Necesitamos el ID para generar el QR

        # 🔹 Crear mensualidad
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

        # 🔹 Carpeta QR
        qr_dir = os.path.join(app.static_folder, "qr")
        if not os.path.exists(qr_dir):
            os.makedirs(qr_dir)

        # 🔹 Ruta completa del QR
        nombre_qr = f"cliente_{cliente.id}.png"
        ruta_qr = os.path.join(qr_dir, nombre_qr)

        # 🔹 Generar QR siempre que no exista
        if not os.path.exists(ruta_qr):
            url_cliente = url_for("acceso_qr", cliente_id=cliente.id, _external=True)
            img = qrcode.make(url_cliente)
            img.save(ruta_qr)

        flash("✅ Cliente y mensualidad registrados correctamente. QR generado.")

        # 🔹 Recargar registros para mostrarlos inmediatamente
        registros = Mensualidad.query.all()

    # 🔹 Crear URLs de QR para el template
    qr_urls = {m.id: url_for("static", filename=f"qr/cliente_{m.cliente_id}.png") for m in registros}

    return render_template(
        "admin/mensualidades.html",
        registros=registros,
        hoy=hoy,
        qr_urls=qr_urls
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

@app.route("/qr/<int:cliente_id>")
def acceso_qr(cliente_id):
    """
    El cliente escanea su QR y se guarda el ID temporalmente.
    Lo manda a completar su registro si no tiene email ni contraseña.
    """
    session["qr_cliente_id"] = cliente_id
    return redirect(url_for("login_cliente"))


@app.route('/login-cliente', methods=['GET', 'POST'])
def login_cliente():
    qr_cliente_id = session.get("qr_cliente_id")  # Puede ser None

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        cliente = Cliente.query.filter_by(email=email).first()

        if cliente:
            # LOGIN
            if cliente.check_password(password):
                session['cliente_id'] = cliente.id
                session.pop("qr_cliente_id", None)
                return redirect(url_for("dashboard_cliente"))
            else:
                flash("❌ Contraseña incorrecta")
        else:
            # REGISTRO DESDE QR
            if not qr_cliente_id:
                flash("❌ QR inválido")
                return redirect(url_for("login_cliente"))

            cliente_temp = Cliente.query.get(qr_cliente_id)
            if not cliente_temp:
                flash("❌ Cliente no encontrado")
                return redirect(url_for("login_cliente"))

            # Guardar email y contraseña
            cliente_temp.email = email
            cliente_temp.set_password(password)
            db.session.commit()

            session['cliente_id'] = cliente_temp.id
            session.pop("qr_cliente_id", None)
            flash("✅ Registro completado. Bienvenido!")
            return redirect(url_for("dashboard_cliente"))

    # Pre-llenado del formulario si viene de QR
    registro_prellenado = None
    if qr_cliente_id:
        cliente_temp = Cliente.query.get(qr_cliente_id)
        if cliente_temp:
            registro_prellenado = {
                "nombre": cliente_temp.nombre,
                "apellido": cliente_temp.apellido,
                "email": ""  # Dejamos vacío para que ingrese su correo real
            }

    return render_template(
        'login_cliente.html',
        registro_prellenado=registro_prellenado
    )


@app.route('/registro-cliente', methods=['GET', 'POST'])
def registro_cliente():
    """
    Ruta para que un cliente se registre por sí mismo.
    """
    if request.method == "POST":
        nombre = request.form.get("nombre")
        apellido = request.form.get("apellido")
        email = request.form.get("email")
        password = request.form.get("password")

        # Verificar si ya existe un cliente con ese email
        if Cliente.query.filter_by(email=email).first():
            flash("❌ Ya existe un cliente con ese correo. Intenta iniciar sesión.")
            return redirect(url_for("registro_cliente"))

        # Guardar el cliente
        nuevo_cliente = Cliente(
            nombre=nombre,
            apellido=apellido,
            email=email
        )
        nuevo_cliente.set_password(password)

        db.session.add(nuevo_cliente)
        db.session.commit()

        session["cliente_id"] = nuevo_cliente.id
        flash("✅ Registro exitoso. Bienvenido!")

        return redirect(url_for("dashboard_cliente"))

    return render_template("registro_cliente.html")


from functools import wraps

def login_cliente_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'cliente_id' not in session:
            return redirect(url_for('login_cliente'))
        return f(*args, **kwargs)
    return wrapper


from datetime import date, timedelta

@app.route('/dashboard')
@login_cliente_required
def dashboard_cliente():
    cliente_id = session['cliente_id']

    # Obtenemos la última mensualidad del cliente
    mensualidad = Mensualidad.query.filter_by(
        cliente_id=cliente_id
    ).order_by(Mensualidad.fecha_vencimiento.desc()).first()

    hoy = date.today()

    if not mensualidad:
        estado = "sin_membresia"
        qr_url = None
    else:
        # Calculamos el estado
        if hoy > mensualidad.fecha_vencimiento:
            estado = "vencido"
        elif hoy >= mensualidad.fecha_vencimiento - timedelta(days=2):
            estado = "por_vencer"
        else:
            estado = "activo"

        # Generar QR si no existe y si no está vencido
        qr_url = generar_qr_cliente(cliente_id) if estado != "vencido" else None

    return render_template(
        "dashboard_cliente.html",
        mensualidad=mensualidad,
        estado=estado,
        qr_url=qr_url
    )


@app.route("/admin/mensualidad/crear/<int:cliente_id>", methods=["POST"])
def crear_mensualidad(cliente_id):
    if "admin_id" not in session:
        return redirect(url_for("login"))

    fecha_pago = date.today()
    fecha_vencimiento = fecha_pago + timedelta(days=30)

    nueva = Mensualidad(
        cliente_id=cliente_id,
        nombre=request.form["nombre"],
        apellidos=request.form["apellidos"],
        monto=request.form["monto"],
        fecha_pago=fecha_pago,
        fecha_vencimiento=fecha_vencimiento,
        estado="activo"
    )

    db.session.add(nueva)
    db.session.commit()
    generar_qr_cliente(cliente_id)


    flash("✅ Mensualidad creada correctamente")
    return redirect(url_for("admin_dashboard"))


@app.route("/cron/revisar-mensualidades")
def cron_revisar_mensualidades():
    token = request.args.get("token")
    if token != os.environ.get("CRON_TOKEN"):
        return "❌ No autorizado", 401

    revisar_mensualidades()
    return "✅ Mensualidades revisadas"






# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
