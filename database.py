from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = "mi_clave_secreta_2026"


def crear_bd():
    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario TEXT NOT NULL UNIQUE,
            clave TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            precio REAL NOT NULL,
            cantidad INTEGER NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ventas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            producto_id INTEGER NOT NULL,
            nombre_producto TEXT NOT NULL,
            cantidad INTEGER NOT NULL,
            precio REAL NOT NULL,
            total REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            telefono TEXT,
            correo TEXT,
            direccion TEXT
        )
    """)

    cursor.execute("SELECT * FROM usuarios WHERE usuario = ?", ("admin",))
    usuario_encontrado = cursor.fetchone()

    if not usuario_encontrado:
        cursor.execute(
            "INSERT INTO usuarios (usuario, clave) VALUES (?, ?)",
            ("admin", "1234")
        )

    conexion.commit()
    conexion.close()


@app.route("/")
def inicio():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    mensaje = ""

    if request.method == "POST":
        usuario = request.form["usuario"]
        clave = request.form["clave"]

        conexion = sqlite3.connect("pos.db")
        cursor = conexion.cursor()

        cursor.execute(
            "SELECT * FROM usuarios WHERE usuario = ? AND clave = ?",
            (usuario, clave)
        )
        usuario_encontrado = cursor.fetchone()

        conexion.close()

        if usuario_encontrado:
            session["usuario"] = usuario
            return redirect(url_for("panel"))
        else:
            mensaje = "Usuario o contraseña incorrectos"

    return render_template("login.html", mensaje=mensaje)


@app.route("/panel")
def panel():
    if "usuario" not in session:
        return redirect(url_for("login"))

    return render_template("panel.html", usuario=session["usuario"])


@app.route("/inventario", methods=["GET", "POST"])
def inventario():
    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"]
        precio = request.form["precio"]
        cantidad = request.form["cantidad"]

        cursor.execute(
            "INSERT INTO productos (nombre, precio, cantidad) VALUES (?, ?, ?)",
            (nombre, precio, cantidad)
        )
        conexion.commit()

    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()

    conexion.close()

    return render_template("inventario.html", productos=productos)


@app.route("/eliminar_producto/<int:id>")
def eliminar_producto(id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    cursor.execute("DELETE FROM productos WHERE id = ?", (id,))
    conexion.commit()
    conexion.close()

    return redirect(url_for("inventario"))


@app.route("/ventas", methods=["GET", "POST"])
def ventas():
    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    mensaje = ""

    if request.method == "POST":
        producto_id = request.form["producto_id"]
        cantidad_vender = int(request.form["cantidad"])

        cursor.execute("SELECT * FROM productos WHERE id = ?", (producto_id,))
        producto = cursor.fetchone()

        if producto:
            id_producto = producto[0]
            nombre_producto = producto[1]
            precio_producto = float(producto[2])
            stock_actual = int(producto[3])

            if cantidad_vender <= stock_actual and cantidad_vender > 0:
                total = cantidad_vender * precio_producto
                nuevo_stock = stock_actual - cantidad_vender

                cursor.execute(
                    "INSERT INTO ventas (producto_id, nombre_producto, cantidad, precio, total) VALUES (?, ?, ?, ?, ?)",
                    (id_producto, nombre_producto, cantidad_vender, precio_producto, total)
                )

                cursor.execute(
                    "UPDATE productos SET cantidad = ? WHERE id = ?",
                    (nuevo_stock, id_producto)
                )

                conexion.commit()
                mensaje = "Venta registrada correctamente"
            else:
                mensaje = "No hay suficiente stock"

    cursor.execute("SELECT * FROM productos")
    productos = cursor.fetchall()

    cursor.execute("SELECT * FROM ventas ORDER BY id DESC")
    historial = cursor.fetchall()

    cursor.execute("SELECT IFNULL(SUM(total), 0) FROM ventas")
    total_vendido = cursor.fetchone()[0]

    conexion.close()

    return render_template(
        "ventas.html",
        productos=productos,
        historial=historial,
        mensaje=mensaje,
        total_vendido=total_vendido
    )


@app.route("/clientes", methods=["GET", "POST"])
def clientes():
    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    mensaje = ""

    if request.method == "POST":
        nombre = request.form["nombre"]
        telefono = request.form["telefono"]
        correo = request.form["correo"]
        direccion = request.form["direccion"]

        cursor.execute(
            "INSERT INTO clientes (nombre, telefono, correo, direccion) VALUES (?, ?, ?, ?)",
            (nombre, telefono, correo, direccion)
        )

        conexion.commit()
        mensaje = "Cliente agregado correctamente"

    cursor.execute("SELECT * FROM clientes ORDER BY id DESC")
    lista_clientes = cursor.fetchall()

    conexion.close()

    return render_template(
        "clientes.html",
        clientes=lista_clientes,
        mensaje=mensaje
    )


@app.route("/reportes")
def reportes():
    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    cursor.execute("SELECT COUNT(*) FROM productos")
    total_productos = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM clientes")
    total_clientes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ventas")
    cantidad_ventas = cursor.fetchone()[0]

    cursor.execute("SELECT IFNULL(SUM(total), 0) FROM ventas")
    total_ingresos = cursor.fetchone()[0]

    cursor.execute("""
        SELECT nombre_producto, SUM(cantidad) AS total_vendido
        FROM ventas
        GROUP BY nombre_producto
        ORDER BY total_vendido DESC
        LIMIT 5
    """)
    productos_mas_vendidos = cursor.fetchall()

    conexion.close()

    return render_template(
        "reportes.html",
        total_productos=total_productos,
        total_clientes=total_clientes,
        cantidad_ventas=cantidad_ventas,
        total_ingresos=total_ingresos,
        productos_mas_vendidos=productos_mas_vendidos
    )


@app.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect(url_for("login"))


if __name__ == "__main__":
    crear_bd()
    app.run(debug=True)