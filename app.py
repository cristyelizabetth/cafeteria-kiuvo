"""Cafetería Kiuvo - sitio web para reservar almuerzos y comprar productos.

Backend: Flask + SQLite.  Frontend: plantillas HTML (Jinja2) + CSS.
Para ejecutarlo:  python app.py   y abrir http://127.0.0.1:5000
"""
import os
import secrets
import sqlite3
from datetime import date, datetime
from functools import wraps

from flask import (Flask, abort, flash, g, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "cafeteria.db")
# Páginas de compra: el administrador no puede entrar a ellas.
VISTAS_DE_CLIENTE = {"inicio", "almuerzos", "tienda", "ver_carrito", "agregar_al_carrito",
                     "actualizar_carrito", "vaciar_carrito", "checkout", "mis_pedidos"}

app = Flask(__name__)
# En producción la clave debe venir de una variable de entorno.
app.secret_key = os.environ.get("SECRET_KEY", "clave-solo-para-desarrollo")


# ---------------------------------------------------------------- base de datos
def get_db():
    """Devuelve la conexión a la base de datos de la petición actual."""
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row          # permite usar fila["columna"]
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    """Crea las tablas y, si la base está vacía, carga datos de ejemplo."""
    db = sqlite3.connect(DB_PATH)
    with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
        db.executescript(f.read())

    if db.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0] == 0:
        db.execute(
            "INSERT INTO usuarios (nombre, email, password_hash, es_admin) VALUES (?, ?, ?, 1)",
            ("Administrador", "admin@kiuvo.edu", generate_password_hash("admin123")),
        )
    if db.execute("SELECT COUNT(*) FROM productos").fetchone()[0] == 0:
        ejemplos = [
            # nombre, descripción, precio (centavos), stock, categoría, tipo
            ("Pollo a la plancha", "Con arroz, ensalada fresca y tortillas.", 350, 25, "Plato fuerte", "almuerzo"),
            ("Carne guisada", "Con arroz, frijoles y vegetales salteados.", 375, 20, "Plato fuerte", "almuerzo"),
            ("Pasta con vegetales", "Opción vegetariana con salsa de tomate.", 300, 15, "Vegetariano", "almuerzo"),
            ("Sopa de res", "Con verduras, arroz y tortillas.", 325, 12, "Sopas", "almuerzo"),
            ("Café americano", "Taza de 12 oz.", 100, 60, "Bebidas", "producto"),
            ("Jugo natural", "Naranja o piña, 16 oz.", 150, 30, "Bebidas", "producto"),
            ("Agua embotellada", "600 ml.", 75, 80, "Bebidas", "producto"),
            ("Pan dulce", "Unidad, horneado del día.", 50, 40, "Panadería", "producto"),
            ("Sándwich de jamón y queso", "Pan integral.", 225, 18, "Snacks", "producto"),
            ("Galletas de avena", "Paquete de 4.", 125, 35, "Snacks", "producto"),
        ]
        db.executemany(
            "INSERT INTO productos (nombre, descripcion, precio, stock, categoria, tipo) VALUES (?, ?, ?, ?, ?, ?)",
            ejemplos,
        )
    db.commit()
    db.close()


# ------------------------------------------------------------------- utilidades
@app.template_filter("dinero")
def dinero(centavos):
    """Convierte centavos (entero) a texto: 350 -> $3.50"""
    return f"${centavos / 100:.2f}"


def csrf_token():
    """Token que se incluye en cada formulario para evitar envíos falsificados."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(16)
    return session["csrf_token"]


app.jinja_env.globals["csrf_token"] = csrf_token


@app.before_request
def antes_de_cada_peticion():
    # 1) Verificar el token en todos los formularios enviados por POST.
    if request.method == "POST":
        if request.form.get("csrf_token") != session.get("csrf_token"):
            abort(400, "Formulario inválido o sesión expirada.")
    # 2) Cargar el usuario que inició sesión (si hay).
    g.usuario = None
    if "usuario_id" in session:
        g.usuario = get_db().execute(
            "SELECT * FROM usuarios WHERE id = ?", (session["usuario_id"],)
        ).fetchone()
    # 3) El administrador solo gestiona: no puede comprar ni reservar.
    if g.usuario and g.usuario["es_admin"] and request.endpoint in VISTAS_DE_CLIENTE:
        return redirect(url_for("admin_pedidos"))


@app.context_processor
def datos_globales():
    """Variables disponibles en todas las plantillas."""
    carrito = session.get("carrito", {})
    return {"usuario": g.get("usuario"), "items_carrito": sum(carrito.values())}


def login_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if g.usuario is None:
            flash("Inicia sesión para continuar.", "aviso")
            return redirect(url_for("login", siguiente=request.path))
        return vista(*args, **kwargs)
    return envoltura


def admin_requerido(vista):
    @wraps(vista)
    def envoltura(*args, **kwargs):
        if g.usuario is None:
            return redirect(url_for("login", siguiente=request.path))
        if not g.usuario["es_admin"]:
            abort(403)
        return vista(*args, **kwargs)
    return envoltura


def entero(texto, defecto=0):
    try:
        return int(texto)
    except (TypeError, ValueError):
        return defecto


def detalle_carrito():
    """Lee el carrito de la sesión y devuelve (lista de items, total)."""
    carrito = session.get("carrito", {})
    items, total = [], 0
    for producto_id, cantidad in carrito.items():
        p = get_db().execute(
            "SELECT * FROM productos WHERE id = ? AND activo = 1", (producto_id,)
        ).fetchone()
        if p is None:
            continue
        subtotal = p["precio"] * cantidad
        total += subtotal
        items.append({"producto": p, "cantidad": cantidad, "subtotal": subtotal})
    return items, total


# ---------------------------------------------------------------------- catálogo
@app.route("/")
def inicio():
    almuerzos = get_db().execute(
        "SELECT * FROM productos WHERE tipo = 'almuerzo' AND activo = 1 LIMIT 3"
    ).fetchall()
    return render_template("inicio.html", almuerzos=almuerzos)


def mostrar_catalogo(tipo, titulo, subtitulo):
    cat_filtro = request.args.get("categoria")
    db = get_db()
    if cat_filtro:
        productos = db.execute(
            "SELECT * FROM productos WHERE tipo = ? AND categoria = ? AND activo = 1 ORDER BY nombre",
            (tipo, cat_filtro)
        ).fetchall()
    else:
        productos = db.execute(
            "SELECT * FROM productos WHERE tipo = ? AND activo = 1 ORDER BY categoria, nombre",
            (tipo,)
        ).fetchall()
    return render_template("catalogo.html", productos=productos, titulo=titulo, subtitulo=subtitulo)


@app.route("/almuerzos")
def almuerzos():
    return mostrar_catalogo("almuerzo", "Almuerzos",
                            "Reserva tu almuerzo y pasa a recogerlo sin hacer fila.")


@app.route("/tienda")
def tienda():
    return mostrar_catalogo("producto", "Tienda",
                            "Bebidas, snacks y más, según el inventario disponible.")


# ----------------------------------------------------------------------- carrito
@app.route("/carrito")
def ver_carrito():
    items, total = detalle_carrito()
    return render_template("carrito.html", items=items, total=total)


@app.route("/carrito/agregar/<int:producto_id>", methods=["POST"])
def agregar_al_carrito(producto_id):
    p = get_db().execute(
        "SELECT * FROM productos WHERE id = ? AND activo = 1", (producto_id,)
    ).fetchone()
    if p is None:
        abort(404)
    cantidad = max(1, entero(request.form.get("cantidad"), 1))
    carrito = session.get("carrito", {})
    clave = str(producto_id)            # las claves de la sesión deben ser texto
    nueva = carrito.get(clave, 0) + cantidad
    if nueva > p["stock"]:
        nueva = p["stock"]
        flash(f"Solo hay {p['stock']} unidades de {p['nombre']}.", "aviso")
    if nueva > 0:
        carrito[clave] = nueva
        flash(f"{p['nombre']} agregado al carrito.", "ok")
    session["carrito"] = carrito
    return redirect(request.referrer or url_for("ver_carrito"))


@app.route("/carrito/actualizar/<int:producto_id>", methods=["POST"])
def actualizar_carrito(producto_id):
    carrito = session.get("carrito", {})
    clave = str(producto_id)
    cantidad = entero(request.form.get("cantidad"), 0)
    if cantidad <= 0:
        carrito.pop(clave, None)
    else:
        p = get_db().execute("SELECT stock FROM productos WHERE id = ?", (producto_id,)).fetchone()
        if p is not None:
            carrito[clave] = min(cantidad, p["stock"])
            if carrito[clave] == 0:
                carrito.pop(clave)
    session["carrito"] = carrito
    return redirect(url_for("ver_carrito"))


@app.route("/carrito/vaciar", methods=["POST"])
def vaciar_carrito():
    session["carrito"] = {}
    return redirect(url_for("ver_carrito"))


# ------------------------------------------------------------------------ pedidos
@app.route("/checkout", methods=["GET", "POST"])
@login_requerido
def checkout():
    items, total = detalle_carrito()
    if not items:
        flash("Tu carrito está vacío.", "aviso")
        return redirect(url_for("almuerzos"))

    if request.method == "POST":
        fecha = request.form.get("fecha_retiro", "")
        hora = request.form.get("hora_retiro", "")
        metodo = "efectivo"     # por ahora solo se paga en caja al recoger
        error = None
        try:
            if date.fromisoformat(fecha) < date.today():
                error = "La fecha de retiro no puede ser anterior a hoy."
            datetime.strptime(hora, "%H:%M")
        except ValueError:
            error = "Indica una fecha y hora de retiro válidas."

        if error is None:
            db = get_db()
            try:
                # Todo el pedido se guarda en una sola transacción:
                # si falta inventario de algo, no se guarda nada.
                cur = db.execute(
                    "INSERT INTO pedidos (usuario_id, creado, fecha_retiro, hora_retiro,"
                    " metodo_pago, pagado, total) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (g.usuario["id"], datetime.now().strftime("%Y-%m-%d %H:%M"),
                     fecha, hora, metodo, 0, total),
                )
                pedido_id = cur.lastrowid
                for item in items:
                    p = item["producto"]
                    # Descuenta del inventario solo si alcanza el stock.
                    actualizado = db.execute(
                        "UPDATE productos SET stock = stock - ? WHERE id = ? AND stock >= ?",
                        (item["cantidad"], p["id"], item["cantidad"]),
                    )
                    if actualizado.rowcount == 0:
                        raise ValueError(f"Ya no hay suficiente inventario de {p['nombre']}.")
                    db.execute(
                        "INSERT INTO pedido_items (pedido_id, producto_id, nombre, precio, cantidad)"
                        " VALUES (?, ?, ?, ?, ?)",
                        (pedido_id, p["id"], p["nombre"], p["precio"], item["cantidad"]),
                    )
                db.commit()
            except ValueError as e:
                db.rollback()
                flash(str(e), "error")
                return redirect(url_for("ver_carrito"))
            session["carrito"] = {}
            flash("¡Pedido confirmado!", "ok")
            return redirect(url_for("ver_pedido", pedido_id=pedido_id))
        flash(error, "error")

    return render_template("checkout.html", items=items, total=total,
                           hoy=date.today().isoformat())


@app.route("/mis-pedidos")
@login_requerido
def mis_pedidos():
    pedidos = get_db().execute(
        "SELECT * FROM pedidos WHERE usuario_id = ? ORDER BY id DESC", (g.usuario["id"],)
    ).fetchall()
    return render_template("pedidos.html", pedidos=pedidos)


def buscar_pedido(pedido_id):
    """Devuelve el pedido solo si es del usuario actual (o si es admin)."""
    pedido = get_db().execute("SELECT * FROM pedidos WHERE id = ?", (pedido_id,)).fetchone()
    if pedido is None:
        abort(404)
    if pedido["usuario_id"] != g.usuario["id"] and not g.usuario["es_admin"]:
        abort(403)
    return pedido


@app.route("/pedido/<int:pedido_id>")
@login_requerido
def ver_pedido(pedido_id):
    pedido = buscar_pedido(pedido_id)
    items = get_db().execute(
        "SELECT * FROM pedido_items WHERE pedido_id = ?", (pedido_id,)
    ).fetchall()
    return render_template("pedido.html", pedido=pedido, items=items)


# ------------------------------------------------------------------------ cuentas
@app.route("/registro", methods=["GET", "POST"])
def registro():
    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not nombre or "@" not in email:
            flash("Escribe tu nombre y un correo válido.", "error")
        elif len(password) < 6:
            flash("La contraseña debe tener al menos 6 caracteres.", "error")
        else:
            db = get_db()
            try:
                # Nunca se guarda la contraseña, solo su hash.
                cur = db.execute(
                    "INSERT INTO usuarios (nombre, email, password_hash) VALUES (?, ?, ?)",
                    (nombre, email, generate_password_hash(password)),
                )
                db.commit()
            except sqlite3.IntegrityError:
                flash("Ya existe una cuenta con ese correo.", "error")
            else:
                session["usuario_id"] = cur.lastrowid
                flash(f"¡Bienvenido/a, {nombre}!", "ok")
                return redirect(url_for("inicio"))
    return render_template("registro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        u = get_db().execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
        if u is None or not check_password_hash(u["password_hash"], request.form.get("password", "")):
            flash("Correo o contraseña incorrectos.", "error")
        else:
            session["usuario_id"] = u["id"]
            if u["es_admin"]:
                session.pop("carrito", None)    # el admin no usa carrito
            siguiente = request.args.get("siguiente", "")
            # Solo se aceptan rutas internas, para no redirigir a otros sitios.
            if not siguiente.startswith("/") or siguiente.startswith("//"):
                siguiente = url_for("admin_pedidos" if u["es_admin"] else "inicio")
            return redirect(siguiente)
    return render_template("login.html")


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("inicio"))


# ----------------------------------------------------------------- administración
@app.route("/admin")
@admin_requerido
def admin_pedidos():
    pedidos = get_db().execute(
        "SELECT pedidos.*, usuarios.nombre AS cliente FROM pedidos"
        " JOIN usuarios ON usuarios.id = pedidos.usuario_id"
        " ORDER BY pedidos.fecha_retiro DESC, pedidos.hora_retiro"
    ).fetchall()
    return render_template("admin_pedidos.html", pedidos=pedidos)


@app.route("/admin/productos")
@admin_requerido
def admin_productos():
    productos = get_db().execute("SELECT * FROM productos ORDER BY tipo, categoria, nombre").fetchall()
    return render_template("admin_productos.html", productos=productos)


def leer_formulario_producto():
    """Valida el formulario de producto. Devuelve (datos, error)."""
    f = request.form
    nombre = f.get("nombre", "").strip()
    try:
        precio = round(float(f.get("precio", "")) * 100)   # dólares -> centavos
        stock = int(f.get("stock", ""))
    except ValueError:
        return None, "Precio y stock deben ser números."
    if not nombre or precio < 0 or stock < 0:
        return None, "Revisa el nombre, el precio y el stock."
    if f.get("tipo") not in ("almuerzo", "producto"):
        return None, "Tipo de producto inválido."
    datos = (nombre, f.get("descripcion", "").strip(), precio, stock,
             f.get("categoria", "").strip() or "General", f.get("tipo"),
             1 if f.get("activo") else 0)
    return datos, None


@app.route("/admin/productos/nuevo", methods=["GET", "POST"])
@admin_requerido
def admin_producto_nuevo():
    if request.method == "POST":
        datos, error = leer_formulario_producto()
        if error:
            flash(error, "error")
        else:
            db = get_db()
            db.execute("INSERT INTO productos (nombre, descripcion, precio, stock, categoria, tipo, activo)"
                       " VALUES (?, ?, ?, ?, ?, ?, ?)", datos)
            db.commit()
            flash("Producto creado.", "ok")
            return redirect(url_for("admin_productos"))
    return render_template("admin_producto_form.html", producto=None)


@app.route("/admin/productos/<int:producto_id>/editar", methods=["GET", "POST"])
@admin_requerido
def admin_producto_editar(producto_id):
    db = get_db()
    producto = db.execute("SELECT * FROM productos WHERE id = ?", (producto_id,)).fetchone()
    if producto is None:
        abort(404)
    if request.method == "POST":
        datos, error = leer_formulario_producto()
        if error:
            flash(error, "error")
        else:
            db.execute("UPDATE productos SET nombre = ?, descripcion = ?, precio = ?, stock = ?,"
                       " categoria = ?, tipo = ?, activo = ? WHERE id = ?", datos + (producto_id,))
            db.commit()
            flash("Producto actualizado.", "ok")
            return redirect(url_for("admin_productos"))
    return render_template("admin_producto_form.html", producto=producto)


# Crea la base de datos la primera vez que se inicia la aplicación.
init_db()

if __name__ == "__main__":
    app.run(debug=True)
