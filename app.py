from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from datetime import date, timedelta
import os
import qrcode



def generar_qr_cliente(cliente_id):
    ruta_qr = f"static/qr/cliente_{cliente_id}.png"

    if not os.path.exists(ruta_qr):
        img = qrcode.make(f"CLIENTE:{cliente_id}")
        img.save(ruta_qr)

    return ruta_qr

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

class Cliente(db.Model):
    __tablename__ = 'clientes'
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)  # <- AGREGAR
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
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

    if request.method == "POST":
        # Obtenemos datos del formulario
        cliente_id = request.form.get("cliente_id")
        nombre = request.form.get("nombre")
        apellidos = request.form.get("apellidos")
        monto = request.form.get("monto")
        fecha_pago_str = request.form.get("fecha_pago")

        # Validación básica
        if not monto or not fecha_pago_str:
            flash("❌ Monto y fecha son obligatorios")
            return redirect(url_for("mensualidades"))

        fecha_pago = datetime.strptime(fecha_pago_str, "%Y-%m-%d").date()
        fecha_vencimiento = fecha_pago + timedelta(days=30)

        # Si seleccionó cliente del dropdown
        if cliente_id:
            cliente = Cliente.query.get(cliente_id)
            if not cliente:
                flash("❌ Cliente no encontrado")
                return redirect(url_for("mensualidades"))
            nombre_final = cliente.nombre
            apellidos_final = cliente.apellido
            cliente_id_final = cliente.id
        else:
            # Buscar cliente por nombre + apellidos manual
            cliente = Cliente.query.filter_by(nombre=nombre, apellido=apellidos).first()
            if not cliente:
                flash("❌ Cliente no encontrado")
                return redirect(url_for("mensualidades"))
            nombre_final = nombre
            apellidos_final = apellidos
            cliente_id_final = cliente.id

        # Crear mensualidad
        nueva = Mensualidad(
            cliente_id=cliente_id_final,
            nombre=nombre_final,
            apellidos=apellidos_final,
            monto=float(monto),
            fecha_pago=fecha_pago,
            fecha_vencimiento=fecha_vencimiento,
            estado="activo"
        )
        db.session.add(nueva)
        db.session.commit()  # ✅ guarda la mensualidad

        # 🔹 Generar QR automáticamente
        generar_qr_cliente(cliente_id_final)

        flash("✅ Mensualidad registrada correctamente")
        return redirect(url_for("mensualidades"))

    # GET
    hoy = date.today()
    registros = Mensualidad.query.all()
    clientes = Cliente.query.all()
    return render_template(
        "admin/mensualidades.html",
        registros=registros,
        clientes=clientes,
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

#---------------------------------------------

@app.route('/login-cliente', methods=['GET', 'POST'])
def login_cliente():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cliente = Cliente.query.filter_by(email=email).first()

        if cliente and cliente.check_password(password):
            session['cliente_id'] = cliente.id

            # 🔐 VALIDACIÓN DE QR (SI VIENE DE UNO)
            if "qr_cliente_id" in session:
                if session["qr_cliente_id"] != cliente.id:
                    flash("❌ Este QR no corresponde a tu cuenta")
                    return redirect(url_for("login_cliente"))
                session.pop("qr_cliente_id")  # limpia el QR

            return redirect(url_for('dashboard_cliente'))
        else:
            flash('Credenciales incorrectas')

    return render_template('login_cliente.html')

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

    mensualidad = Mensualidad.query.filter_by(
        cliente_id=cliente_id
    ).order_by(Mensualidad.fecha_vencimiento.desc()).first()

    hoy = date.today()

    if not mensualidad:
        estado = "sin_membresia"
    else:
        estado = "activo"
        if hoy > mensualidad.fecha_vencimiento:
            estado = "vencido"
        elif hoy >= mensualidad.fecha_vencimiento - timedelta(days=2):
            estado = "por_vencer"

    return render_template(
        "dashboard_cliente.html",
        mensualidad=mensualidad,
        estado=estado
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

@app.route("/qr/<int:cliente_id>")
def acceso_qr(cliente_id):
    # Guardamos el cliente en sesión temporal
    session["qr_cliente_id"] = cliente_id
    return redirect(url_for("login_cliente"))





# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
