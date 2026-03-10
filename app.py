from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

app = Flask(__name__)
app.secret_key = "mi_clave_secreta_2026"

def generar_inventario_pdf():
    carpeta = "facturas"

    if not os.path.exists(carpeta):
        os.makedirs(carpeta)

    archivo = f"{carpeta}/inventario.pdf"

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()
    cursor.execute("""
        SELECT id, nombre, precio, cantidad
        FROM productos
        ORDER BY nombre ASC
    """)
    productos = cursor.fetchall()
    conexion.close()

    c = canvas.Canvas(archivo, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Inventario del Sistema")

    c.setFont("Helvetica", 10)
    c.drawString(50, height - 70, f"Fecha de impresión: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

    y = height - 110

    c.setFont("Helvetica-Bold", 10)
    c.rect(40, y, 530, 22)
    c.drawString(50, y + 7, "ID")
    c.drawString(100, y + 7, "Producto")
    c.drawString(340, y + 7, "Precio")
    c.drawString(470, y + 7, "Cantidad")

    y -= 22
    c.setFont("Helvetica", 10)

    total_productos = 0

    for producto in productos:
        id_producto = str(producto[0])
        nombre = str(producto[1])
        precio = float(producto[2])
        cantidad = int(producto[3])

        total_productos += cantidad

        c.rect(40, y, 530, 22)
        c.drawString(50, y + 7, id_producto)
        c.drawString(100, y + 7, nombre[:32])

        # columnas alineadas
        c.drawRightString(420, y + 7, f"RD$ {precio:,.2f}")
        c.drawRightString(520, y + 7, str(cantidad))

        y -= 22

        if y < 80:
            c.showPage()
            width, height = letter
            y = height - 60

            c.setFont("Helvetica-Bold", 10)
            c.rect(40, y, 530, 22)
            c.drawString(50, y + 7, "ID")
            c.drawString(100, y + 7, "Producto")
            c.drawRightString(420, y + 7, "Precio")
            c.drawRightString(520, y + 7, "Cantidad")

            y -= 22
            c.setFont("Helvetica", 10)

    y -= 20
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, f"Total de productos registrados: {len(productos)}")
    c.drawString(320, y, f"Total de unidades en inventario: {total_productos}")

    c.save()
    return archivo

def generar_factura_pdf(factura_id, cliente, fecha, items, total_general):
    carpeta = "facturas"

    if not os.path.exists(carpeta):
        os.makedirs(carpeta)

    archivo = f"{carpeta}/factura_{factura_id}.pdf"

    c = canvas.Canvas(archivo, pagesize=letter)
    width, height = letter

    # ===== DATOS EMPRESA =====
    nombre_empresa = "LOS MAESTROS SR"
    direccion1 = "Calle San Juan #02"
    direccion2 = "Lotes y Servicios III, Sabana Perdida"
    telefono = "849-353-2803"
    rnc = "RNC: ____________"
    ncf = f"NCF: B010000{factura_id:04d}"

    # ===== LOGO =====
    logo_path = "static/logo.png"
    if os.path.exists(logo_path):
        try:
            logo = ImageReader(logo_path)
            c.drawImage(
                logo,
                40,
                height - 105,
                width=70,
                height=55,
                preserveAspectRatio=True,
                mask='auto'
            )
        except:
            pass

    # ===== ENCABEZADO =====
    c.setFont("Helvetica-Bold", 16)
    c.drawString(140, height - 45, nombre_empresa)

    c.setFont("Helvetica", 10)
    c.drawString(140, height - 63, direccion1)
    c.drawString(140, height - 77, direccion2)
    c.drawString(140, height - 91, f"Tel.: {telefono}")
    c.drawString(140, height - 105, rnc)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(430, height - 45, "FACTURA")

    c.setFont("Helvetica", 10)
    c.drawString(400, height - 68, f"Factura No.: {factura_id}")
    c.drawString(400, height - 84, ncf)
    c.drawString(400, height - 100, f"Fecha: {fecha}")

    # Línea separadora
    c.line(40, height - 125, 570, height - 125)

    # ===== CLIENTE =====
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, height - 155, "Cliente:")
    c.setFont("Helvetica", 11)
    c.drawString(95, height - 155, str(cliente))

    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, height - 175, "Condición:")
    c.setFont("Helvetica", 11)
    c.drawString(105, height - 175, "Contado")

    # ===== TABLA =====
    y = height - 220

    c.setFont("Helvetica-Bold", 10)
    c.rect(40, y, 530, 22)
    c.drawString(50, y + 7, "Descripción")
    c.drawString(285, y + 7, "Cant.")
    c.drawString(370, y + 7, "Precio")
    c.drawString(500, y + 7, "Importe")

    y -= 22
    c.setFont("Helvetica", 9)

    subtotal_general = 0

    for item in items:
        nombre = str(item["nombre"])
        precio = float(item["precio"])
        subtotal = float(item["subtotal"])
        cantidad = str(item["cantidad"])
        subtotal_general += subtotal

        c.rect(40, y, 530, 22)
        c.drawString(50, y + 7, nombre[:32])
        c.drawRightString(315, y + 7, cantidad)
        c.drawRightString(460, y + 7, f"{precio:,.2f}")
        c.drawRightString(560, y + 7, f"{subtotal:,.2f}")

        y -= 22

        if y < 180:
            c.showPage()
            width, height = letter
            y = height - 60

            c.setFont("Helvetica-Bold", 10)
            c.rect(40, y, 530, 22)
            c.drawString(50, y + 7, "Descripción")
            c.drawString(285, y + 7, "Cant.")
            c.drawString(370, y + 7, "Precio")
            c.drawString(500, y + 7, "Importe")

            y -= 22
            c.setFont("Helvetica", 9)

    # ===== TOTALES =====
    itbis = subtotal_general * 0.18
    total_con_itbis = subtotal_general + itbis

    y -= 60

    c.setFont("Helvetica-Bold", 11)
    c.drawString(360, y + 40, "Subtotal:")
    c.drawRightString(560, y + 40, f"RD$ {subtotal_general:,.2f}")

    c.drawString(360, y + 20, "ITBIS (18%):")
    c.drawRightString(560, y + 20, f"RD$ {itbis:,.2f}")

    c.drawString(360, y, "Total General:")
    c.drawRightString(560, y, f"RD$ {total_con_itbis:,.2f}")

    # ===== PIE =====
    y -= 70
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(40, y, "Gracias por preferirnos.")

    c.setFont("Helvetica", 7)
    c.drawString(40, y - 14, "Nota: Los artículos electrónicos no están sujetos a garantía.")

    c.save()
    return archivo


@app.route("/")
def inicio():
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    mensaje = ""

    if request.method == "POST":
        usuario = request.form["usuario"]
        clave = request.form["clave"]

        conexion = sqlite3.connect("pos.db")
        cursor = conexion.cursor()

        cursor.execute("""
            SELECT id, nombre, usuario, clave, rol,
                   permiso_inventario,
                   permiso_ventas,
                   permiso_clientes,
                   permiso_reportes,
                   permiso_configuracion
            FROM usuarios
            WHERE usuario = ? AND clave = ?
        """, (usuario, clave))

        usuario_encontrado = cursor.fetchone()
        conexion.close()

        if usuario_encontrado:
            session["usuario_id"] = usuario_encontrado[0]
            session["nombre"] = usuario_encontrado[1]
            session["usuario"] = usuario_encontrado[2]
            session["rol"] = usuario_encontrado[4]
            session["permiso_inventario"] = usuario_encontrado[5]
            session["permiso_ventas"] = usuario_encontrado[6]
            session["permiso_clientes"] = usuario_encontrado[7]
            session["permiso_reportes"] = usuario_encontrado[8]
            session["permiso_configuracion"] = usuario_encontrado[9]

            return redirect(url_for("panel"))
        else:
            mensaje = "Usuario o contraseña incorrectos"

    return render_template("login.html", mensaje=mensaje)


@app.route("/panel")
def panel():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return render_template("panel.html", usuario=session["usuario"])

@app.route("/inicio")
def inicio_panel():
    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    # Ventas de hoy
    cursor.execute("""
        SELECT IFNULL(SUM(total), 0)
        FROM ventas
        WHERE DATE(fecha) = DATE('now', 'localtime')
    """)
    ventas_hoy = cursor.fetchone()[0]

    # Ventas del mes
    cursor.execute("""
        SELECT IFNULL(SUM(total), 0)
        FROM ventas
        WHERE strftime('%Y-%m', fecha) = strftime('%Y-%m', 'now', 'localtime')
    """)
    ventas_mes = cursor.fetchone()[0]

    # Productos con poco stock
    cursor.execute("""
        SELECT nombre, cantidad
        FROM productos
        WHERE cantidad <= 5
        ORDER BY cantidad ASC
    """)
    productos_bajos = cursor.fetchall()

    # Últimas ventas
    cursor.execute("""
        SELECT nombre_producto, cliente_nombre, cantidad, total, fecha
        FROM ventas
        ORDER BY id DESC
        LIMIT 5
    """)
    ultimas_ventas = cursor.fetchall()

    conexion.close()

    return render_template(
        "inicio_panel.html",
        ventas_hoy=ventas_hoy,
        ventas_mes=ventas_mes,
        productos_bajos=productos_bajos,
        ultimas_ventas=ultimas_ventas
    )


@app.route("/inventario", methods=["GET", "POST"])
def inventario():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("permiso_inventario") != 1 and session.get("rol") != "admin":
        return "No tienes permiso para acceder a Inventario"

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"].strip().lower()
        precio = float(request.form["precio"])
        cantidad = int(request.form["cantidad"])

        cursor.execute("SELECT id, cantidad FROM productos WHERE lower(nombre) = ?", (nombre,))
        producto_existente = cursor.fetchone()

        if producto_existente:
            id_producto = producto_existente[0]
            cantidad_actual = int(producto_existente[1])
            nueva_cantidad = cantidad_actual + cantidad

            cursor.execute("""
                UPDATE productos
                SET cantidad = ?, precio = ?
                WHERE id = ?
            """, (nueva_cantidad, precio, id_producto))
        else:
            cursor.execute("""
                INSERT INTO productos (nombre, precio, cantidad)
                VALUES (?, ?, ?)
            """, (nombre, precio, cantidad))

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


@app.route("/editar_producto/<int:id>", methods=["GET", "POST"])
def editar_producto(id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    if request.method == "POST":
        nombre = request.form["nombre"]
        precio = request.form["precio"]
        cantidad = request.form["cantidad"]

        cursor.execute("""
            UPDATE productos
            SET nombre = ?, precio = ?, cantidad = ?
            WHERE id = ?
        """, (nombre, precio, cantidad, id))

        conexion.commit()
        conexion.close()

        return redirect(url_for("inventario"))

    cursor.execute("SELECT * FROM productos WHERE id = ?", (id,))
    producto = cursor.fetchone()
    conexion.close()

    return render_template("editar_producto.html", producto=producto)


@app.route("/ventas", methods=["GET", "POST"])
def ventas():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("permiso_ventas") != 1 and session.get("rol") != "admin":
        return "No tienes permiso para acceder a Ventas"


    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()
    mensaje = ""

    if request.method == "POST":
        producto_id = request.form["producto_id"]
        cliente_id = request.form.get("cliente_id", "").strip()
        cliente_nombre_manual = request.form.get("cliente_nombre_manual", "").strip()
        cantidad_vender = int(request.form["cantidad"])

        cursor.execute("SELECT * FROM productos WHERE id = ?", (producto_id,))
        producto = cursor.fetchone()

        nombre_cliente = ""
        id_cliente = 0

        if cliente_id:
            cursor.execute("SELECT * FROM clientes WHERE id = ?", (cliente_id,))
            cliente = cursor.fetchone()

            if cliente:
                id_cliente = cliente[0]
                nombre_cliente = cliente[1]

        elif cliente_nombre_manual:
            nombre_cliente = cliente_nombre_manual
            id_cliente = 0

        else:
            cursor.execute("SELECT COUNT(*) FROM ventas")
            cantidad_ventas = cursor.fetchone()[0] + 1
            nombre_cliente = f"Consumidor final {cantidad_ventas}"
            id_cliente = 0

        if producto and nombre_cliente:
            id_producto = producto[0]
            nombre_producto = producto[1]
            precio_producto = float(producto[2])
            stock_actual = int(producto[3])

            if cantidad_vender <= stock_actual and cantidad_vender > 0:
                total = cantidad_vender * precio_producto
                nuevo_stock = stock_actual - cantidad_vender
                fecha_venta = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute(
                    """
                    INSERT INTO ventas
                    (producto_id, nombre_producto, cantidad, precio, total, cliente_id, cliente_nombre, fecha)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        id_producto,
                        nombre_producto,
                        cantidad_vender,
                        precio_producto,
                        total,
                        id_cliente,
                        nombre_cliente,
                        fecha_venta
                    )
                )

                venta_id = cursor.lastrowid

                cursor.execute(
                    "UPDATE productos SET cantidad = ? WHERE id = ?",
                    (nuevo_stock, id_producto)
                )

                conexion.commit()

                fecha_factura = datetime.now().strftime("%d/%m/%Y %H:%M")

                items = [
                    {
                        "nombre": nombre_producto,
                        "cantidad": cantidad_vender,
                        "precio": precio_producto,
                        "subtotal": total
                    }
                ]

                generar_factura_pdf(
                    venta_id,
                    nombre_cliente,
                    fecha_factura,
                    items,
                    total
                )

                mensaje = "Venta registrada correctamente"
            else:
                mensaje = "No hay suficiente stock"
        else:
            mensaje = "Debes seleccionar un producto válido"

    cursor.execute("SELECT * FROM productos ORDER BY nombre ASC")
    productos = cursor.fetchall()

    cursor.execute("SELECT * FROM clientes ORDER BY nombre ASC")
    clientes = cursor.fetchall()

    cursor.execute("SELECT * FROM ventas ORDER BY id DESC")
    historial = cursor.fetchall()

    cursor.execute("SELECT IFNULL(SUM(total), 0) FROM ventas")
    total_vendido = cursor.fetchone()[0]

    conexion.close()

    return render_template(
        "ventas.html",
        productos=productos,
        clientes=clientes,
        historial=historial,
        mensaje=mensaje,
        total_vendido=total_vendido
    )


@app.route("/clientes", methods=["GET", "POST"])
def clientes():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("permiso_clientes") != 1 and session.get("rol") != "admin":
        return "No tienes permiso para acceder a Clientes"

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


@app.route("/eliminar_cliente/<int:id>")
def eliminar_cliente(id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    cursor.execute("DELETE FROM clientes WHERE id = ?", (id,))
    conexion.commit()
    conexion.close()

    return redirect(url_for("clientes"))


@app.route("/reportes", methods=["GET", "POST"])
def reportes():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("permiso_reportes") != 1 and session.get("rol") != "admin":
        return "No tienes permiso para acceder a Reportes"

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    fecha_buscar = datetime.now().strftime("%Y-%m-%d")

    if request.method == "POST":
        fecha_buscar = request.form["fecha"]

    # Tarjetas generales
    cursor.execute("SELECT COUNT(*) FROM productos")
    total_productos = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM clientes")
    total_clientes = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM ventas")
    cantidad_ventas = cursor.fetchone()[0]

    cursor.execute("SELECT IFNULL(SUM(total), 0) FROM ventas")
    total_ingresos = cursor.fetchone()[0]

    cursor.execute("""
        SELECT nombre_producto, SUM(cantidad) as total_vendido
        FROM ventas
        GROUP BY nombre_producto
        ORDER BY total_vendido DESC
        LIMIT 5
    """)
    productos_mas_vendidos = cursor.fetchall()

    # Reporte por día
    cursor.execute(
        """
        SELECT id, nombre_producto, cliente_nombre, cantidad, precio, total, fecha
        FROM ventas
        WHERE DATE(fecha) = ?
        ORDER BY id DESC
        """,
        (fecha_buscar,)
    )
    ventas_dia = cursor.fetchall()

    cursor.execute(
        """
        SELECT IFNULL(SUM(total), 0)
        FROM ventas
        WHERE DATE(fecha) = ?
        """,
        (fecha_buscar,)
    )
    total_dia = cursor.fetchone()[0]

    conexion.close()

    return render_template(
        "reporte_diario.html",
        total_productos=total_productos,
        total_clientes=total_clientes,
        cantidad_ventas=cantidad_ventas,
        total_ingresos=total_ingresos,
        productos_mas_vendidos=productos_mas_vendidos,
        ventas_dia=ventas_dia,
        total_dia=total_dia,
        fecha_buscar=fecha_buscar
    )
@app.route("/imprimir_inventario_pdf")
def imprimir_inventario_pdf():
    if "usuario" not in session:
        return redirect(url_for("login"))

    archivo = generar_inventario_pdf()
    return send_file(archivo, as_attachment=False)

@app.route("/descargar_factura/<int:venta_id>")
def descargar_factura(venta_id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    archivo = f"facturas/factura_{venta_id}.pdf"

    if os.path.exists(archivo):
        return send_file(archivo, as_attachment=True)

    return "Factura no encontrada"

@app.route("/ver_factura/<int:venta_id>")
def ver_factura(venta_id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    archivo = f"facturas/factura_{venta_id}.pdf"

    if os.path.exists(archivo):
        return send_file(archivo)

    return "Factura no encontrada"
@app.route("/reporte_diario", methods=["GET", "POST"])
def reporte_diario():
    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    fecha_buscar = datetime.now().strftime("%Y-%m-%d")

    if request.method == "POST":
        fecha_buscar = request.form["fecha"]

    cursor.execute(
        """
        SELECT id, nombre_producto, cliente_nombre, cantidad, precio, total, fecha
        FROM ventas
        WHERE DATE(fecha) = ?
        ORDER BY id DESC
        """,
        (fecha_buscar,)
    )
    ventas_dia = cursor.fetchall()

    cursor.execute(
        """
        SELECT IFNULL(SUM(total), 0)
        FROM ventas
        WHERE DATE(fecha) = ?
        """,
        (fecha_buscar,)
    )
    total_dia = cursor.fetchone()[0]

    conexion.close()

    return render_template(
        "reporte_diario.html",
        ventas_dia=ventas_dia,
        total_dia=total_dia,
        fecha_buscar=fecha_buscar
    )

@app.route("/configuracion")
def configuracion():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("permiso_configuracion") != 1 and session.get("rol") != "admin":
        return "No tienes permiso para acceder a Configuración"

    return render_template("configuracion.html")

@app.route("/configuracion/usuarios", methods=["GET", "POST"])
def configuracion_usuarios():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("permiso_configuracion") != 1 and session.get("rol") != "admin":
        return "No tienes permiso para acceder a Configuración"

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()
    mensaje = ""

    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        usuario = request.form["usuario"].strip()
        clave = request.form["clave"].strip()
        rol = request.form["rol"].strip()

        permiso_inventario = 1 if request.form.get("permiso_inventario") == "on" else 0
        permiso_ventas = 1 if request.form.get("permiso_ventas") == "on" else 0
        permiso_clientes = 1 if request.form.get("permiso_clientes") == "on" else 0
        permiso_reportes = 1 if request.form.get("permiso_reportes") == "on" else 0
        permiso_configuracion = 1 if request.form.get("permiso_configuracion") == "on" else 0

        cursor.execute("SELECT id FROM usuarios WHERE usuario = ?", (usuario,))
        existe = cursor.fetchone()

        if existe:
            mensaje = "Ese usuario ya existe"
        else:
            cursor.execute("""
                INSERT INTO usuarios (
                    nombre, usuario, clave, rol,
                    permiso_inventario, permiso_ventas,
                    permiso_clientes, permiso_reportes,
                    permiso_configuracion
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                nombre, usuario, clave, rol,
                permiso_inventario, permiso_ventas,
                permiso_clientes, permiso_reportes,
                permiso_configuracion
            ))
            conexion.commit()
            mensaje = "Usuario creado correctamente"

    cursor.execute("""
        SELECT id, nombre, usuario, rol,
               permiso_inventario, permiso_ventas,
               permiso_clientes, permiso_reportes,
               permiso_configuracion
        FROM usuarios
        ORDER BY id DESC
    """)
    usuarios = cursor.fetchall()

    conexion.close()

    return render_template("configuracion_usuarios.html", usuarios=usuarios, mensaje=mensaje)

@app.route("/editar_usuario/<int:id>", methods=["GET", "POST"])
def editar_usuario(id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("permiso_configuracion") != 1 and session.get("rol") != "admin":
        return "No tienes permiso para editar usuarios"

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()
    mensaje = ""

    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        usuario = request.form["usuario"].strip()
        rol = request.form["rol"].strip()

        permiso_inventario = 1 if request.form.get("permiso_inventario") == "on" else 0
        permiso_ventas = 1 if request.form.get("permiso_ventas") == "on" else 0
        permiso_clientes = 1 if request.form.get("permiso_clientes") == "on" else 0
        permiso_reportes = 1 if request.form.get("permiso_reportes") == "on" else 0
        permiso_configuracion = 1 if request.form.get("permiso_configuracion") == "on" else 0

        cursor.execute("""
            SELECT id FROM usuarios
            WHERE usuario = ? AND id != ?
        """, (usuario, id))
        existe = cursor.fetchone()

        if existe:
            mensaje = "Ese nombre de usuario ya pertenece a otro usuario"
        else:
            cursor.execute("""
                UPDATE usuarios
                SET nombre = ?, usuario = ?, rol = ?,
                    permiso_inventario = ?, permiso_ventas = ?,
                    permiso_clientes = ?, permiso_reportes = ?,
                    permiso_configuracion = ?
                WHERE id = ?
            """, (
                nombre, usuario, rol,
                permiso_inventario, permiso_ventas,
                permiso_clientes, permiso_reportes,
                permiso_configuracion,
                id
            ))
            conexion.commit()
            conexion.close()
            return redirect(url_for("configuracion"))

    cursor.execute("""
        SELECT id, nombre, usuario, rol,
               permiso_inventario, permiso_ventas,
               permiso_clientes, permiso_reportes,
               permiso_configuracion
        FROM usuarios
        WHERE id = ?
    """, (id,))
    usuario_editar = cursor.fetchone()

    conexion.close()

    if not usuario_editar:
        return "Usuario no encontrado"

    return render_template("editar_usuario.html", usuario_editar=usuario_editar, mensaje=mensaje)


@app.route("/cambiar_clave/<int:id>", methods=["GET", "POST"])
def cambiar_clave(id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("permiso_configuracion") != 1 and session.get("rol") != "admin":
        return "No tienes permiso para cambiar contraseñas"

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()
    mensaje = ""

    cursor.execute("SELECT id, nombre, usuario FROM usuarios WHERE id = ?", (id,))
    usuario_clave = cursor.fetchone()

    if not usuario_clave:
        conexion.close()
        return "Usuario no encontrado"

    if request.method == "POST":
        nueva_clave = request.form["nueva_clave"].strip()
        confirmar_clave = request.form["confirmar_clave"].strip()

        if nueva_clave == "" or confirmar_clave == "":
            mensaje = "Debes completar ambos campos"
        elif nueva_clave != confirmar_clave:
            mensaje = "Las contraseñas no coinciden"
        else:
            cursor.execute("""
                UPDATE usuarios
                SET clave = ?
                WHERE id = ?
            """, (nueva_clave, id))
            conexion.commit()
            conexion.close()
            return redirect(url_for("configuracion_usuarios"))

    conexion.close()
    return render_template("cambiar_clave.html", usuario_clave=usuario_clave, mensaje=mensaje)


@app.route("/eliminar_usuario/<int:id>")
def eliminar_usuario(id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("permiso_configuracion") != 1 and session.get("rol") != "admin":
        return "No tienes permiso para eliminar usuarios"

    if id == session.get("usuario_id"):
        return "No puedes eliminar el usuario con el que estás logueado"

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    cursor.execute("DELETE FROM usuarios WHERE id = ?", (id,))
    conexion.commit()
    conexion.close()

    return redirect(url_for("configuracion"))

@app.route("/configuracion/preferencias")
def preferencias():
    if "usuario" not in session:
        return redirect(url_for("login"))

    version_actual = "1.0.0"

    return render_template("preferencias.html", version=version_actual)

@app.route("/buscar_actualizacion")
def buscar_actualizacion():

    version_actual = "1.0.0"
    version_disponible = "1.1.0"

    if version_disponible > version_actual:
        mensaje = f"Hay una nueva versión disponible: {version_disponible}"
    else:
        mensaje = "Tu sistema está actualizado."

    return render_template(
        "preferencias.html",
        version=version_actual,
        mensaje=mensaje
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True)