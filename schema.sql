-- Estructura de la base de datos de la cafetería (SQLite)

CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre        TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    es_admin      INTEGER NOT NULL DEFAULT 0
);

-- Un mismo catálogo guarda almuerzos y productos de la tienda.
-- tipo = 'almuerzo' o 'producto'. El precio se guarda en centavos.
CREATE TABLE IF NOT EXISTS productos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT NOT NULL,
    descripcion TEXT NOT NULL DEFAULT '',
    precio      INTEGER NOT NULL CHECK (precio >= 0),
    stock       INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    categoria   TEXT NOT NULL DEFAULT 'General',
    tipo        TEXT NOT NULL CHECK (tipo IN ('almuerzo', 'producto')),
    activo      INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS pedidos (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario_id   INTEGER NOT NULL REFERENCES usuarios(id),
    creado       TEXT NOT NULL,
    fecha_retiro TEXT NOT NULL,
    hora_retiro  TEXT NOT NULL,
    metodo_pago  TEXT NOT NULL CHECK (metodo_pago IN ('tarjeta', 'efectivo')),
    pagado       INTEGER NOT NULL DEFAULT 0,
    total        INTEGER NOT NULL,
    estado       TEXT NOT NULL DEFAULT 'pendiente'
                 CHECK (estado IN ('pendiente', 'listo', 'entregado', 'cancelado'))
);

-- Se copia nombre y precio para que el historial no cambie
-- si luego el administrador edita el producto.
CREATE TABLE IF NOT EXISTS pedido_items (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id   INTEGER NOT NULL REFERENCES pedidos(id),
    producto_id INTEGER NOT NULL REFERENCES productos(id),
    nombre      TEXT NOT NULL,
    precio      INTEGER NOT NULL,
    cantidad    INTEGER NOT NULL CHECK (cantidad > 0)
);
