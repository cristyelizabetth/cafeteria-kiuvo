# Cafetería Kiuvo

Sitio web para la cafetería de la universidad: permite **reservar almuerzos** y **comprar productos** del inventario disponible.

## Funciones (avance)

- Catálogo de almuerzos y tienda de productos.
- Carrito de compras.
- Registro e inicio de sesión (las contraseñas se guardan cifradas con hash).
- Confirmación del pedido con fecha y hora de retiro; se paga en caja.
- El inventario se descuenta al confirmar el pedido.
- Historial de pedidos del usuario.
- El administrador solo gestiona (no puede comprar ni reservar): ve los pedidos y crea o edita el menú y el inventario.

## Pendiente para la entrega final

- Filtro por categoría en almuerzos y tienda.
- Pago simulado con tarjeta.
- Cancelar un pedido y devolver el inventario.
- Que el administrador cambie el estado de los pedidos.

## Tecnologías

| Parte | Tecnología |
|---|---|
| Backend | Python 3 + Flask |
| Base de datos | SQLite (archivo `cafeteria.db`, se crea solo) |
| Frontend | HTML (plantillas Jinja2) + CSS |
| Control de versiones | Git + GitHub |

## Cómo ejecutarlo

```bash
# 1. Crear y activar un entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Mac / Linux

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Iniciar el servidor
python app.py
```

Abrir <http://127.0.0.1:5000> en el navegador.

**Cuenta de administrador de prueba:** `admin@kiuvo.edu` / `admin123`

Para empezar de cero, borra el archivo `cafeteria.db` y vuelve a iniciar la app.

## Estructura del proyecto

```
cafeteria-kiuvo/
├── app.py              # Backend: rutas, lógica y acceso a la base de datos
├── schema.sql          # Tablas de la base de datos
├── requirements.txt    # Dependencias de Python
├── templates/          # Frontend: páginas HTML
│   ├── base.html       # Plantilla base (barra de navegación, mensajes)
│   ├── _tarjeta.html   # Tarjeta de producto reutilizable
│   ├── inicio.html, catalogo.html, carrito.html, checkout.html
│   ├── pedidos.html, pedido.html, login.html, registro.html
│   └── admin_*.html    # Panel de administración
└── static/style.css    # Estilos
```

## Base de datos

- `usuarios`: nombre, email, hash de contraseña, si es administrador.
- `productos`: almuerzos y productos de tienda (columna `tipo`), precio en centavos, stock.
- `pedidos`: usuario, fecha/hora de retiro, método de pago, total, estado.
- `pedido_items`: productos de cada pedido (con copia del nombre y precio).

## Subirlo a GitHub (primera vez)

1. Crear un repositorio vacío en GitHub (sin README).
2. En la carpeta del proyecto:

```bash
git init
git add .
git commit -m "Versión inicial de la cafetería"
git branch -M main
git remote add origin https://github.com/USUARIO/cafeteria-kiuvo.git
git push -u origin main
```

## Flujo de trabajo en equipo

```bash
git pull                              # traer los últimos cambios
git checkout -b nombre-de-la-mejora   # crear una rama para tu cambio
# ... editar archivos ...
git add .
git commit -m "Describe qué cambiaste"
git push -u origin nombre-de-la-mejora
```

Después, abrir un *Pull Request* en GitHub para que el equipo revise y una el cambio a `main`.

## Notas

- `app.run(debug=True)` y la cuenta `admin123` son solo para desarrollo; no usar así en un servidor real.
