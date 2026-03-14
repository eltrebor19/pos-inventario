from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3
import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

app = Flask(__name__)
app.secret_key = "mi_clave_secreta_2026"

import smtplib
from email.message import EmailMessage
import shutil



def crear_tabla_configuracion():
        conexion = sqlite3.connect("pos.db")
        cursor = conexion.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS configuracion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                correo_respaldo TEXT
            )
        """)

        cursor.execute("SELECT COUNT(*) FROM configuracion")
        total = cursor.fetchone()[0]

        if total == 0:
            cursor.execute("""
                INSERT INTO configuracion (correo_respaldo)
                VALUES (?)
            """, ("",))

        conexion.commit()
        conexion.close()

def crear_tabla_gastos_empresa():
    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS gastos_empresa (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_gasto TEXT,
            fecha_pago TEXT,
            mes_pagado TEXT,
            monto REAL,
            referencia TEXT,
            empresa_suplidora TEXT,
            metodo_pago TEXT,
            estado TEXT,
            observacion TEXT,
            fecha_registro TEXT
        )
    """)

    conexion.commit()
    conexion.close()

def agregar_columnas_productos_empresa():
        conexion = sqlite3.connect("pos.db")
        cursor = conexion.cursor()

        cursor.execute("PRAGMA table_info(productos)")
        columnas = [col[1] for col in cursor.fetchall()]

        if "tipo" not in columnas:
            cursor.execute("ALTER TABLE productos ADD COLUMN tipo TEXT DEFAULT 'Sin tipo'")

        if "costo" not in columnas:
            cursor.execute("ALTER TABLE productos ADD COLUMN costo REAL DEFAULT 0")

        if "ganancia" not in columnas:
            cursor.execute("ALTER TABLE productos ADD COLUMN ganancia REAL DEFAULT 0")

        conexion.commit()
        conexion.close()

def agregar_columnas_productos_empresa():
    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    cursor.execute("PRAGMA table_info(productos)")
    columnas = [col[1] for col in cursor.fetchall()]

    if "tipo" not in columnas:
        cursor.execute("ALTER TABLE productos ADD COLUMN tipo TEXT DEFAULT 'Sin tipo'")

    if "costo" not in columnas:
        cursor.execute("ALTER TABLE productos ADD COLUMN costo REAL DEFAULT 0")

    if "ganancia" not in columnas:
        cursor.execute("ALTER TABLE productos ADD COLUMN ganancia REAL DEFAULT 0")

    conexion.commit()
    conexion.close()

def agregar_columna_factura_id_ventas():
    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    cursor.execute("PRAGMA table_info(ventas)")
    columnas = [col[1] for col in cursor.fetchall()]

    if "factura_id" not in columnas:
        cursor.execute("ALTER TABLE ventas ADD COLUMN factura_id INTEGER")
        cursor.execute("UPDATE ventas SET factura_id = id WHERE factura_id IS NULL")

    conexion.commit()
    conexion.close()

def obtener_correo_respaldo():
    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    cursor.execute("SELECT correo_respaldo FROM configuracion LIMIT 1")
    fila = cursor.fetchone()

    conexion.close()

    if fila and fila[0]:
        return fila[0]
    return ""


def guardar_correo_respaldo(correo):
    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    cursor.execute("SELECT id FROM configuracion LIMIT 1")
    fila = cursor.fetchone()

    if fila:
        cursor.execute("""
            UPDATE configuracion
            SET correo_respaldo = ?
            WHERE id = ?
        """, (correo, fila[0]))
    else:
        cursor.execute("""
            INSERT INTO configuracion (correo_respaldo)
            VALUES (?)
        """, (correo,))

    conexion.commit()
    conexion.close()

def crear_tabla_devoluciones():
    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS devoluciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            venta_id INTEGER NOT NULL,
            producto_id INTEGER NOT NULL,
            nombre_producto TEXT NOT NULL,
            cliente_nombre TEXT,
            cantidad INTEGER NOT NULL,
            motivo TEXT,
            usuario_solicita TEXT,
            fecha_solicitud TEXT,
            estado TEXT DEFAULT 'pendiente',
            usuario_confirma TEXT,
            fecha_confirmacion TEXT
        )
    """)

    conexion.commit()
    conexion.close()


@app.route("/configuracion/respaldo", methods=["GET", "POST"])
def configuracion_respaldo():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("permiso_configuracion") != 1 and session.get("rol") != "admin":
        return "No tienes permiso para acceder a Respaldo"

    mensaje = ""
    correo_respaldo = obtener_correo_respaldo()

    if request.method == "POST":
        correo_respaldo = request.form["correo_respaldo"].strip()

        if correo_respaldo == "":
            mensaje = "Debes escribir un correo"
        else:
            guardar_correo_respaldo(correo_respaldo)
            mensaje = "Correo de respaldo guardado correctamente"

        correo_respaldo = obtener_correo_respaldo()

    return render_template(
        "configuracion_respaldo.html",
        correo_respaldo=correo_respaldo,
        mensaje=mensaje
    )



def enviar_respaldo_por_correo():
    correo_destino = obtener_correo_respaldo()

    if not correo_destino:
        return False, "No hay correo de respaldo configurado"

    carpeta = "respaldos"

    if not os.path.exists(carpeta):
        os.makedirs(carpeta)

    fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo_respaldo = os.path.join(carpeta, f"backup_pos_{fecha}.db")

    shutil.copy("pos.db", archivo_respaldo)

    remitente = "mlosmaestros@gmail.com"
    clave_app = "gtnc nrmj fxng lpyi"

    msg = EmailMessage()
    msg["Subject"] = "Respaldo automático del sistema POS"
    msg["From"] = remitente
    msg["To"] = correo_destino
    msg.set_content("Adjunto respaldo de la base de datos del sistema POS.")

    with open(archivo_respaldo, "rb") as f:
        msg.add_attachment(
            f.read(),
            maintype="application",
            subtype="octet-stream",
            filename=os.path.basename(archivo_respaldo)
        )

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(remitente, clave_app)
            smtp.send_message(msg)

        return True, f"Respaldo enviado correctamente a {correo_destino}"

    except Exception as e:
        print("ERROR AL ENVIAR CORREO:", str(e))
        return False, f"Error al enviar respaldo: {str(e)}"


@app.route("/enviar_respaldo")
def enviar_respaldo():

    if "usuario" not in session:
        return redirect(url_for("login"))

    ok, mensaje = enviar_respaldo_por_correo()

    correo_respaldo = obtener_correo_respaldo()

    return render_template(
        "configuracion_respaldo.html",
        correo_respaldo=correo_respaldo,
        mensaje=mensaje
    )

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

def generar_cotizacion_pdf(cliente, items, total_general):
    carpeta = "facturas"

    if not os.path.exists(carpeta):
        os.makedirs(carpeta)

    fecha_archivo = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo = f"{carpeta}/cotizacion_{fecha_archivo}.pdf"

    c = canvas.Canvas(archivo, pagesize=letter)
    width, height = letter

    nombre_empresa = "LOS MAESTROS SR"
    direccion1 = "Calle San Juan #02"
    direccion2 = "Lotes y Servicios III, Sabana Perdida"
    telefono = "849-353-2803"
    rnc = "RNC: ____________"

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

    c.setFont("Helvetica-Bold", 16)
    c.drawString(140, height - 45, nombre_empresa)

    c.setFont("Helvetica", 10)
    c.drawString(140, height - 63, direccion1)
    c.drawString(140, height - 77, direccion2)
    c.drawString(140, height - 91, f"Tel.: {telefono}")
    c.drawString(140, height - 105, rnc)

    c.setFont("Helvetica-Bold", 16)
    c.drawString(390, height - 45, "COTIZACIÓN")

    fecha_doc = datetime.now().strftime("%d/%m/%Y %H:%M")
    c.setFont("Helvetica", 10)
    c.drawString(400, height - 80, f"Fecha: {fecha_doc}")

    c.line(40, height - 125, 570, height - 125)

    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, height - 155, "Cliente:")
    c.setFont("Helvetica", 11)
    c.drawString(95, height - 155, str(cliente))

    y = height - 220

    c.setFont("Helvetica-Bold", 10)
    c.rect(40, y, 530, 22)
    c.drawString(50, y + 7, "Descripción")
    c.drawString(285, y + 7, "Cant.")
    c.drawString(370, y + 7, "Precio")
    c.drawString(500, y + 7, "Importe")

    y -= 22
    c.setFont("Helvetica", 9)

    for item in items:
        nombre = str(item["nombre"])
        precio = float(item["precio"])
        subtotal = float(item["subtotal"])
        cantidad = str(item["cantidad"])

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

    y -= 50
    c.setFont("Helvetica-Bold", 11)
    c.drawString(360, y, "Total General:")
    c.drawRightString(560, y, f"RD$ {total_general:,.2f}")

    y -= 60
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(40, y, "Documento generado como cotización.")

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

    crear_tabla_gastos_empresa()

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    # Ventas de hoy válidas
    cursor.execute("""
        SELECT IFNULL(SUM(v.total), 0)
        FROM ventas v
        WHERE DATE(v.fecha) = DATE('now', 'localtime')
          AND NOT EXISTS (
              SELECT 1
              FROM devoluciones d
              WHERE d.venta_id = v.id
                AND d.estado = 'confirmada'
          )
    """)
    ventas_hoy = cursor.fetchone()[0]

    # Ventas del mes válidas
    cursor.execute("""
        SELECT IFNULL(SUM(v.total), 0)
        FROM ventas v
        WHERE strftime('%Y-%m', v.fecha) = strftime('%Y-%m', 'now', 'localtime')
          AND NOT EXISTS (
              SELECT 1
              FROM devoluciones d
              WHERE d.venta_id = v.id
                AND d.estado = 'confirmada'
          )
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

    # Últimas ventas válidas
    cursor.execute("""
        SELECT v.nombre_producto, v.cliente_nombre, v.cantidad, v.total, v.fecha
        FROM ventas v
        WHERE NOT EXISTS (
            SELECT 1
            FROM devoluciones d
            WHERE d.venta_id = v.id
              AND d.estado = 'confirmada'
        )
        ORDER BY v.id DESC
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

@app.route("/aplicaciones")
def aplicaciones():
    if "usuario" not in session:
        return redirect(url_for("login"))

    return render_template("aplicaciones.html")


@app.route("/inventario", methods=["GET", "POST"])
def inventario():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("permiso_inventario") != 1 and session.get("rol") != "admin":
        return "No tienes permiso para acceder a Inventario"

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()
    mensaje = ""

    if request.method == "POST":
        accion = request.form.get("accion", "").strip()

        if accion == "agregar":
            tipo = request.form["tipo"].strip()
            nombre = request.form["nombre"].strip()
            costo = float(request.form["costo"])
            ganancia = float(request.form["ganancia"])
            cantidad = int(request.form["cantidad"])

            precio = costo + (costo * ganancia / 100)

            cursor.execute("""
                SELECT id, cantidad
                FROM productos
                WHERE lower(nombre) = ? AND lower(tipo) = ?
            """, (nombre.lower(), tipo.lower()))
            producto_existente = cursor.fetchone()

            if producto_existente:
                id_producto = producto_existente[0]
                cantidad_actual = int(producto_existente[1])
                nueva_cantidad = cantidad_actual + cantidad

                cursor.execute("""
                    UPDATE productos
                    SET cantidad = ?, precio = ?, costo = ?, ganancia = ?, tipo = ?
                    WHERE id = ?
                """, (nueva_cantidad, precio, costo, ganancia, tipo, id_producto))
            else:
                cursor.execute("""
                    INSERT INTO productos (tipo, nombre, costo, ganancia, precio, cantidad)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (tipo, nombre, costo, ganancia, precio, cantidad))

            conexion.commit()
            mensaje = "Producto agregado correctamente"

        elif accion == "devolucion":
            producto_id = request.form.get("producto_id", "").strip()
            cantidad_devolver_texto = request.form.get("cantidad_devolver", "").strip()

            try:
                cantidad_devolver = int(cantidad_devolver_texto)
            except:
                cantidad_devolver = 0

            if not producto_id:
                mensaje = "Debes seleccionar un producto"
            elif cantidad_devolver <= 0:
                mensaje = "La cantidad a devolver debe ser mayor que cero"
            else:
                cursor.execute(
                    "SELECT id, nombre, cantidad FROM productos WHERE id = ?",
                    (producto_id,)
                )
                producto = cursor.fetchone()

                if producto:
                    id_producto = producto[0]
                    nombre_producto = producto[1]
                    cantidad_actual = int(producto[2])
                    nueva_cantidad = cantidad_actual + cantidad_devolver

                    cursor.execute("""
                        UPDATE productos
                        SET cantidad = ?
                        WHERE id = ?
                    """, (nueva_cantidad, id_producto))

                    conexion.commit()
                    mensaje = f"Devolución aplicada correctamente a {nombre_producto}"
                else:
                    mensaje = "Producto no encontrado"

    cursor.execute("SELECT * FROM productos ORDER BY nombre ASC")
    productos = cursor.fetchall()
    conexion.close()

    return render_template("inventario.html", productos=productos, mensaje=mensaje)

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

    if "carrito" not in session:
        session["carrito"] = []
    else:
        carrito_nuevo = []
        for item in session["carrito"]:
            carrito_nuevo.append({
                "producto_id": item.get("producto_id"),
                "descripcion": item.get("descripcion", item.get("nombre", "")),
                "precio_unitario": item.get("precio_unitario", item.get("precio", 0)),
                "cantidad": item.get("cantidad", 0),
                "unidad": item.get("unidad", "PZ"),
                "importe": item.get("importe", item.get("subtotal", 0))
            })
        session["carrito"] = carrito_nuevo
        session.modified = True

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()
    mensaje = ""
    precio_consultado = None
    nombre_precio = ""

    buscar_id = request.args.get("buscar_id", "").strip()
    buscar_cliente = request.args.get("buscar_cliente", "").strip()
    mostrar_historial = "1" if (buscar_id or buscar_cliente) else "0"

    if request.method == "POST":
        accion = request.form.get("accion", "").strip()

        if accion == "consultar_precio":
            nombre_precio_buscar = request.form.get("producto_precio_buscar", "").strip().lower()

            if nombre_precio_buscar:
                cursor.execute("""
                    SELECT id, nombre, precio, cantidad
                    FROM productos
                    WHERE lower(nombre) LIKE ?
                    ORDER BY nombre ASC
                    LIMIT 1
                """, (f"%{nombre_precio_buscar}%",))
                producto = cursor.fetchone()

                if producto:
                    nombre_precio = producto[1]
                    precio_consultado = producto[2]
                    mensaje = f"Precio consultado de {producto[1]}"
                else:
                    mensaje = "Producto no encontrado"
            else:
                mensaje = "Escribe el nombre del producto"

        elif accion == "agregar":
            producto_id = request.form.get("producto_id", "").strip()
            nombre_busqueda = request.form.get("producto_buscar", "").strip().lower()
            cantidad_texto = request.form.get("cantidad", "1").strip()

            try:
                cantidad = int(cantidad_texto)
            except:
                cantidad = 1

            producto = None

            if producto_id:
                cursor.execute(
                    "SELECT id, nombre, precio, cantidad FROM productos WHERE id = ?",
                    (producto_id,)
                )
                producto = cursor.fetchone()
            elif nombre_busqueda:
                cursor.execute("""
                    SELECT id, nombre, precio, cantidad
                    FROM productos
                    WHERE lower(nombre) LIKE ?
                    ORDER BY nombre ASC
                    LIMIT 1
                """, (f"%{nombre_busqueda}%",))
                producto = cursor.fetchone()

            if producto:
                id_producto = producto[0]
                nombre_producto = producto[1]
                precio_producto = float(producto[2])
                stock_actual = int(producto[3])

                existente = None
                for item in session["carrito"]:
                    if item["producto_id"] == id_producto:
                        existente = item
                        break

                cantidad_actual_en_lista = existente["cantidad"] if existente else 0

                if cantidad <= 0:
                    mensaje = "La cantidad debe ser mayor que cero"
                elif cantidad_actual_en_lista + cantidad > stock_actual:
                    mensaje = "No hay suficiente stock disponible"
                else:
                    if existente:
                        existente["cantidad"] += cantidad
                        existente["importe"] = existente["cantidad"] * existente["precio_unitario"]
                    else:
                        session["carrito"].append({
                            "producto_id": id_producto,
                            "descripcion": nombre_producto,
                            "precio_unitario": precio_producto,
                            "cantidad": cantidad,
                            "unidad": "PZ",
                            "importe": precio_producto * cantidad
                        })

                    session.modified = True
                    mensaje = "Producto agregado correctamente"
            else:
                mensaje = "Producto no encontrado"

        elif accion == "eliminar":
            indice = int(request.form.get("indice", -1))

            if 0 <= indice < len(session["carrito"]):
                session["carrito"].pop(indice)
                session.modified = True
                mensaje = "Producto eliminado de la lista"

        elif accion == "modificar":
            indice = int(request.form.get("indice", -1))
            nueva_cantidad_texto = request.form.get("nueva_cantidad", "1").strip()

            try:
                nueva_cantidad = int(nueva_cantidad_texto)
            except:
                nueva_cantidad = 1

            if 0 <= indice < len(session["carrito"]):
                item = session["carrito"][indice]
                producto_id = item["producto_id"]

                cursor.execute(
                    "SELECT cantidad FROM productos WHERE id = ?",
                    (producto_id,)
                )
                fila = cursor.fetchone()

                if fila:
                    stock_actual = int(fila[0])

                    if nueva_cantidad <= 0:
                        mensaje = "La cantidad debe ser mayor que cero"
                    elif nueva_cantidad > stock_actual:
                        mensaje = "No hay suficiente stock disponible"
                    else:
                        item["cantidad"] = nueva_cantidad
                        item["importe"] = item["precio_unitario"] * nueva_cantidad
                        session.modified = True
                        mensaje = "Cantidad modificada correctamente"

        elif accion == "cancelar":
            session["carrito"] = []
            session.modified = True
            mensaje = "Venta cancelada"

        elif accion == "cobrar":
            carrito = session.get("carrito", [])
            cliente_id = request.form.get("cliente_id", "").strip()
            cliente_nombre_manual = request.form.get("cliente_nombre_manual", "").strip()

            if not carrito:
                mensaje = "No hay productos en la lista"
            else:
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
                else:
                    cursor.execute("SELECT COUNT(*) FROM ventas")
                    contador = cursor.fetchone()[0] + 1
                    nombre_cliente = f"Consumidor final {contador}"

                fecha_venta = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                fecha_factura = datetime.now().strftime("%d/%m/%Y %H:%M")
                total_general = 0
                error_en_venta = False

                # crear un solo factura_id para toda la compra
                cursor.execute("SELECT IFNULL(MAX(factura_id), 0) + 1 FROM ventas")
                factura_id = cursor.fetchone()[0]

                for item in carrito:
                    producto_id = item["producto_id"]
                    nombre_producto = item["descripcion"]
                    cantidad_vender = int(item["cantidad"])
                    precio_producto = float(item["precio_unitario"])
                    total = float(item.get("importe", item.get("subtotal", 0)))

                    cursor.execute(
                        "SELECT cantidad FROM productos WHERE id = ?",
                        (producto_id,)
                    )
                    stock_fila = cursor.fetchone()

                    if not stock_fila:
                        conexion.rollback()
                        mensaje = f"El producto {nombre_producto} no existe"
                        error_en_venta = True
                        break

                    stock_actual = int(stock_fila[0])

                    if cantidad_vender > stock_actual:
                        conexion.rollback()
                        mensaje = f"No hay suficiente stock para {nombre_producto}"
                        error_en_venta = True
                        break

                    nuevo_stock = stock_actual - cantidad_vender

                    cursor.execute("""
                        INSERT INTO ventas
                        (factura_id, producto_id, nombre_producto, cantidad, precio, total, cliente_id, cliente_nombre, fecha)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        factura_id,
                        producto_id,
                        nombre_producto,
                        cantidad_vender,
                        precio_producto,
                        total,
                        id_cliente,
                        nombre_cliente,
                        fecha_venta
                    ))

                    total_general += total

                    cursor.execute(
                        "UPDATE productos SET cantidad = ? WHERE id = ?",
                        (nuevo_stock, producto_id)
                    )

                if not error_en_venta:
                    conexion.commit()

                    items_factura = []
                    for item in carrito:
                        items_factura.append({
                            "nombre": item["descripcion"],
                            "cantidad": item["cantidad"],
                            "precio": item["precio_unitario"],
                            "subtotal": item.get("importe", item.get("subtotal", 0))
                        })

                    generar_factura_pdf(
                        factura_id,
                        nombre_cliente,
                        fecha_factura,
                        items_factura,
                        total_general
                    )

                    session["carrito"] = []
                    session.modified = True
                    mensaje = "Venta registrada correctamente"

    cursor.execute("SELECT id, nombre, precio, cantidad FROM productos ORDER BY nombre ASC")
    productos = cursor.fetchall()

    cursor.execute("SELECT * FROM clientes ORDER BY nombre ASC")
    clientes = cursor.fetchall()

    sql_historial = """
        SELECT
            v.factura_id,
            GROUP_CONCAT(v.nombre_producto, ', ') AS productos,
            v.cliente_nombre,
            SUM(v.cantidad) AS total_cantidad,
            SUM(v.total) AS total_factura,
            MAX(v.fecha) AS fecha,
            COALESCE(
                (
                    SELECT d.estado
                    FROM devoluciones d
                    WHERE d.venta_id = v.id
                    ORDER BY d.id DESC
                    LIMIT 1
                ),
                ''
            ) AS estado_devolucion
        FROM ventas v
        WHERE NOT EXISTS (
            SELECT 1
            FROM devoluciones d2
            WHERE d2.venta_id = v.id
              AND d2.estado = 'confirmada'
        )
    """

    parametros = []

    if buscar_id:
        try:
            buscar_id_num = int(buscar_id)
            sql_historial += " AND v.factura_id = ?"
            parametros.append(buscar_id_num)
        except:
            sql_historial += " AND 1 = 0"

    if buscar_cliente:
        sql_historial += " AND lower(COALESCE(v.cliente_nombre, '')) LIKE ?"
        parametros.append(f"%{buscar_cliente.lower()}%")

    sql_historial += """
        GROUP BY v.factura_id, v.cliente_nombre
        ORDER BY v.factura_id DESC
        LIMIT 50
    """

    cursor.execute(sql_historial, parametros)
    historial = cursor.fetchall()

    conexion.close()

    total_carrito = sum(item.get("importe", item.get("subtotal", 0)) for item in session["carrito"])
    total_articulos = sum(item.get("cantidad", 0) for item in session["carrito"])

    return render_template(
        "ventas.html",
        productos=productos,
        clientes=clientes,
        carrito=session["carrito"],
        total_carrito=total_carrito,
        total_articulos=total_articulos,
        historial=historial,
        mensaje=mensaje,
        precio_consultado=precio_consultado,
        nombre_precio=nombre_precio,
        buscar_id=buscar_id,
        buscar_cliente=buscar_cliente,
        mostrar_historial=mostrar_historial
    )


@app.route("/imprimir_cotizacion")
def imprimir_cotizacion():
    if "usuario" not in session:
        return redirect(url_for("login"))

    carrito = session.get("carrito", [])

    if not carrito:
        return "No hay productos en la cotización"

    cliente = session.get("cliente_cotizacion", "Consumidor final")

    items = []
    total_general = 0

    for item in carrito:
        subtotal = float(item.get("importe", item.get("subtotal", 0)))
        items.append({
            "nombre": item["descripcion"],
            "cantidad": item["cantidad"],
            "precio": item["precio_unitario"],
            "subtotal": subtotal
        })
        total_general += subtotal

    archivo = generar_cotizacion_pdf(cliente, items, total_general)
    return send_file(archivo, as_attachment=False)


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
        fecha_form = request.form.get("fecha", "").strip()
        if fecha_form:
            fecha_buscar = fecha_form

    cursor.execute("SELECT COUNT(*) FROM productos")
    total_productos = int(cursor.fetchone()[0] or 0)

    cursor.execute("SELECT COUNT(*) FROM clientes")
    total_clientes = int(cursor.fetchone()[0] or 0)

    cursor.execute("""
        SELECT COUNT(DISTINCT v.factura_id)
        FROM ventas v
        WHERE NOT EXISTS (
            SELECT 1
            FROM devoluciones d
            WHERE d.venta_id = v.id
              AND d.estado = 'confirmada'
        )
    """)
    cantidad_ventas = int(cursor.fetchone()[0] or 0)

    cursor.execute("""
        SELECT IFNULL(SUM(CAST(v.total AS REAL)), 0)
        FROM ventas v
        WHERE NOT EXISTS (
            SELECT 1
            FROM devoluciones d
            WHERE d.venta_id = v.id
              AND d.estado = 'confirmada'
        )
    """)
    total_ingresos = float(cursor.fetchone()[0] or 0)

    cursor.execute("""
        SELECT v.nombre_producto, IFNULL(SUM(CAST(v.cantidad AS INTEGER)), 0) as total_vendido
        FROM ventas v
        WHERE NOT EXISTS (
            SELECT 1
            FROM devoluciones d
            WHERE d.venta_id = v.id
              AND d.estado = 'confirmada'
        )
        GROUP BY v.nombre_producto
        ORDER BY total_vendido DESC
        LIMIT 5
    """)
    productos_raw = cursor.fetchall()

    productos_mas_vendidos = []
    for producto in productos_raw:
        productos_mas_vendidos.append((
            producto[0],
            int(producto[1] or 0)
        ))

    cursor.execute("""
        SELECT
            v.factura_id,
            GROUP_CONCAT(v.nombre_producto, ', ') AS productos,
            v.cliente_nombre,
            IFNULL(SUM(CAST(v.cantidad AS INTEGER)), 0) AS total_cantidad,
            IFNULL(SUM(CAST(v.total AS REAL)), 0) AS total_factura,
            MAX(v.fecha) AS fecha
        FROM ventas v
        WHERE DATE(v.fecha) = ?
          AND NOT EXISTS (
              SELECT 1
              FROM devoluciones d
              WHERE d.venta_id = v.id
                AND d.estado = 'confirmada'
          )
        GROUP BY v.factura_id, v.cliente_nombre
        ORDER BY v.factura_id DESC
    """, (fecha_buscar,))
    ventas_raw = cursor.fetchall()

    ventas_dia = []
    for venta in ventas_raw:
        ventas_dia.append((
            venta[0],
            venta[1],
            venta[2],
            int(venta[3] or 0),
            float(venta[4] or 0),
            venta[5]
        ))

    cursor.execute("""
        SELECT IFNULL(SUM(CAST(v.total AS REAL)), 0)
        FROM ventas v
        WHERE DATE(v.fecha) = ?
          AND NOT EXISTS (
              SELECT 1
              FROM devoluciones d
              WHERE d.venta_id = v.id
                AND d.estado = 'confirmada'
          )
    """, (fecha_buscar,))
    total_dia = float(cursor.fetchone()[0] or 0)

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

@app.route("/descargar_factura/<int:factura_id>")
def descargar_factura(factura_id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    archivo = f"facturas/factura_{factura_id}.pdf"

    if os.path.exists(archivo):
        return send_file(archivo, as_attachment=True)

    return "Factura no encontrada"

    return "Factura no encontrada"


@app.route("/solicitar_devolucion", methods=["POST"])
def solicitar_devolucion():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("permiso_ventas") != 1 and session.get("rol") != "admin":
        return "No tienes permiso para solicitar devoluciones"

    venta_id = request.form.get("venta_id", "").strip()
    producto_id = request.form.get("producto_id", "").strip()
    nombre_producto = request.form.get("nombre_producto", "").strip()
    cliente_nombre = request.form.get("cliente_nombre", "").strip()
    cantidad_texto = request.form.get("cantidad", "").strip()
    motivo = request.form.get("motivo", "").strip()

    try:
        venta_id_num = int(venta_id)
    except:
        return "ID de venta inválido"

    try:
        producto_id_num = int(producto_id)
    except:
        return "ID de producto inválido"

    try:
        cantidad = int(cantidad_texto)
    except:
        cantidad = 0

    if cantidad <= 0:
        return "La cantidad a devolver debe ser mayor que cero"

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    # Buscar la venta real
    cursor.execute("""
        SELECT id, producto_id, nombre_producto, cantidad, cliente_nombre
        FROM ventas
        WHERE id = ?
    """, (venta_id_num,))
    venta = cursor.fetchone()

    if not venta:
        conexion.close()
        return "La venta no existe"

    cantidad_vendida = int(venta[3] or 0)

    # Ver si ya existe devolución pendiente o confirmada para esa venta
    cursor.execute("""
        SELECT id, estado, cantidad
        FROM devoluciones
        WHERE venta_id = ?
          AND estado IN ('pendiente', 'confirmada')
        ORDER BY id DESC
        LIMIT 1
    """, (venta_id_num,))
    devolucion_existente = cursor.fetchone()

    if devolucion_existente:
        conexion.close()
        return "Esta venta ya tiene una devolución solicitada o confirmada"

    if cantidad > cantidad_vendida:
        conexion.close()
        return f"No puedes devolver {cantidad}. Solo se vendieron {cantidad_vendida}"

    cursor.execute("""
        INSERT INTO devoluciones (
            venta_id, producto_id, nombre_producto, cliente_nombre,
            cantidad, motivo, usuario_solicita, fecha_solicitud, estado
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        venta_id_num,
        producto_id_num,
        nombre_producto,
        cliente_nombre,
        cantidad,
        motivo,
        session.get("usuario", ""),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "pendiente"
    ))

    conexion.commit()
    conexion.close()

    return redirect(request.referrer or url_for("ventas"))

@app.route("/devoluciones_pendientes")
def devoluciones_pendientes():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return "No tienes permiso para ver devoluciones"

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id, venta_id, producto_id, nombre_producto, cliente_nombre,
               cantidad, motivo, usuario_solicita, fecha_solicitud, estado
        FROM devoluciones
        WHERE estado = 'pendiente'
        ORDER BY id DESC
    """)
    devoluciones = cursor.fetchall()

    conexion.close()

    return render_template("devoluciones_pendientes.html", devoluciones=devoluciones)

def crear_tabla_seguridad_reset():
    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    cursor.execute("PRAGMA table_info(configuracion)")
    columnas = [col[1] for col in cursor.fetchall()]

    if "clave_reset" not in columnas:
        cursor.execute("ALTER TABLE configuracion ADD COLUMN clave_reset TEXT DEFAULT ''")

    cursor.execute("SELECT COUNT(*) FROM configuracion")
    total = cursor.fetchone()[0]

    if total == 0:
        cursor.execute("""
            INSERT INTO configuracion (correo_respaldo, clave_reset)
            VALUES (?, ?)
        """, ("", ""))

    conexion.commit()
    conexion.close()


def obtener_clave_reset():
    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    cursor.execute("SELECT clave_reset FROM configuracion LIMIT 1")
    fila = cursor.fetchone()
    conexion.close()

    if fila and fila[0]:
        return fila[0]
    return ""


def guardar_clave_reset(clave_reset):
    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    cursor.execute("SELECT id FROM configuracion LIMIT 1")
    fila = cursor.fetchone()

    if fila:
        cursor.execute("""
            UPDATE configuracion
            SET clave_reset = ?
            WHERE id = ?
        """, (clave_reset, fila[0]))
    else:
        cursor.execute("""
            INSERT INTO configuracion (correo_respaldo, clave_reset)
            VALUES (?, ?)
        """, ("", clave_reset))

    conexion.commit()
    conexion.close()


def borrar_archivos_de_carpeta(nombre_carpeta):
    if os.path.exists(nombre_carpeta):
        for archivo in os.listdir(nombre_carpeta):
            ruta = os.path.join(nombre_carpeta, archivo)
            if os.path.isfile(ruta):
                try:
                    os.remove(ruta)
                except:
                    pass

@app.route("/aprobar_devolucion/<int:devolucion_id>")
def aprobar_devolucion(devolucion_id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return "No tienes permiso para confirmar devoluciones"

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT id, producto_id, cantidad, estado
        FROM devoluciones
        WHERE id = ?
    """, (devolucion_id,))
    devolucion = cursor.fetchone()

    if not devolucion:
        conexion.close()
        return "Devolución no encontrada"

    if devolucion[3] != "pendiente":
        conexion.close()
        return "Esta devolución ya fue procesada"

    producto_id = devolucion[1]
    cantidad = int(devolucion[2])

    cursor.execute("SELECT cantidad FROM productos WHERE id = ?", (producto_id,))
    producto = cursor.fetchone()

    if not producto:
        conexion.close()
        return "Producto no encontrado"

    nueva_cantidad = int(producto[0]) + cantidad

    cursor.execute("""
        UPDATE productos
        SET cantidad = ?
        WHERE id = ?
    """, (nueva_cantidad, producto_id))

    cursor.execute("""
        UPDATE devoluciones
        SET estado = ?, usuario_confirma = ?, fecha_confirmacion = ?
        WHERE id = ?
    """, (
        "confirmada",
        session.get("usuario", ""),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        devolucion_id
    ))

    conexion.commit()
    conexion.close()

    return redirect(url_for("devoluciones_pendientes"))

@app.route("/rechazar_devolucion/<int:devolucion_id>")
def rechazar_devolucion(devolucion_id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return "No tienes permiso para rechazar devoluciones"

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    cursor.execute("""
        UPDATE devoluciones
        SET estado = ?, usuario_confirma = ?, fecha_confirmacion = ?
        WHERE id = ?
    """, (
        "rechazada",
        session.get("usuario", ""),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        devolucion_id
    ))

    conexion.commit()
    conexion.close()

    return redirect(url_for("devoluciones_pendientes"))



@app.route("/ver_factura/<int:factura_id>")
def ver_factura(factura_id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    archivo = f"facturas/factura_{factura_id}.pdf"

    if os.path.exists(archivo):
        return send_file(archivo)

    return "Factura no encontrada"

@app.route("/detalle_factura/<int:factura_id>")
def detalle_factura(factura_id):
    if "usuario" not in session:
        return redirect(url_for("login"))

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    cursor.execute("""
        SELECT 
            v.id,
            v.producto_id,
            v.nombre_producto,
            v.cantidad,
            v.precio,
            v.total,
            v.cliente_nombre,
            v.fecha,
            COALESCE((
                SELECT d.estado
                FROM devoluciones d
                WHERE d.venta_id = v.id
                ORDER BY d.id DESC
                LIMIT 1
            ), '') AS estado_devolucion,
            COALESCE((
                SELECT d.cantidad
                FROM devoluciones d
                WHERE d.venta_id = v.id
                ORDER BY d.id DESC
                LIMIT 1
            ), 0) AS cantidad_devolucion
        FROM ventas v
        WHERE v.factura_id = ?
        ORDER BY v.id ASC
    """, (factura_id,))
    detalles_raw = cursor.fetchall()

    detalles = []
    for item in detalles_raw:
        detalles.append((
            item[0],
            item[1],
            item[2],
            int(item[3] or 0),
            float(item[4] or 0),
            float(item[5] or 0),
            item[6],
            item[7],
            item[8],
            int(item[9] or 0)
        ))

    conexion.close()

    if not detalles:
        return "Factura no encontrada"

    return render_template(
        "detalle_factura.html",
        factura_id=factura_id,
        detalles=detalles
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

@app.route("/configuracion/seguridad", methods=["GET", "POST"])
def configuracion_seguridad():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("permiso_configuracion") != 1 and session.get("rol") != "admin":
        return "No tienes permiso para acceder a Seguridad"

    mensaje = ""
    clave_guardada = obtener_clave_reset()

    if request.method == "POST":
        accion = request.form.get("accion", "").strip()

        if accion == "guardar_clave_reset":
            clave_actual = request.form.get("clave_actual", "").strip()
            clave_reset = request.form.get("clave_reset", "").strip()
            confirmar_clave_reset = request.form.get("confirmar_clave_reset", "").strip()

            clave_guardada = obtener_clave_reset()

            if not clave_reset or not confirmar_clave_reset:
                mensaje = "Debes completar los campos de la nueva clave"
            elif not clave_reset.isdigit():
                mensaje = "La nueva clave debe contener solo números"
            elif len(clave_reset) != 16:
                mensaje = "La nueva clave debe tener exactamente 16 dígitos"
            elif clave_reset != confirmar_clave_reset:
                mensaje = "Las nuevas claves no coinciden"
            else:
                if clave_guardada:
                    if not clave_actual:
                        mensaje = "Debes escribir la clave actual para poder cambiarla"
                    elif clave_actual != clave_guardada:
                        mensaje = "La clave actual es incorrecta"
                    else:
                        guardar_clave_reset(clave_reset)
                        mensaje = "Clave de reset actualizada correctamente"
                else:
                    guardar_clave_reset(clave_reset)
                    mensaje = "Clave de reset guardada correctamente"

    return render_template("configuracion_seguridad.html", mensaje=mensaje)


@app.route("/reset_sistema_completo", methods=["POST"])
def reset_sistema_completo():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("rol") != "admin":
        return "Solo el administrador puede hacer el reset completo"

    clave_ingresada = request.form.get("clave_reset_confirmacion", "").strip()
    texto_confirmacion = request.form.get("texto_confirmacion", "").strip().upper()

    clave_guardada = obtener_clave_reset()

    if not clave_guardada:
        return "Primero debes configurar la clave de reset de 16 dígitos"

    if clave_ingresada != clave_guardada:
        return "La clave de reset es incorrecta"

    if texto_confirmacion != "CONFIRMAR BORRADO TOTAL":
        return "Debes escribir exactamente: CONFIRMAR BORRADO TOTAL"

    # ===== PASO 1: ENVIAR RESPALDO AL CORREO =====
    ok_respaldo, mensaje_respaldo = enviar_respaldo_por_correo()

    if not ok_respaldo:
        return f"No se pudo enviar el respaldo. El sistema NO fue borrado. Detalle: {mensaje_respaldo}"

    # ===== PASO 2: SI EL RESPALDO FUE ENVIADO, ENTONCES BORRAR =====
    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    try:
        cursor.execute("DELETE FROM devoluciones")
        cursor.execute("DELETE FROM ventas")
        cursor.execute("DELETE FROM clientes")
        cursor.execute("DELETE FROM productos")

        cursor.execute("""
            DELETE FROM sqlite_sequence
            WHERE name IN ('devoluciones', 'ventas', 'clientes', 'productos')
        """)

        conexion.commit()
        conexion.close()

        borrar_archivos_de_carpeta("facturas")
        borrar_archivos_de_carpeta("respaldos")

        session.pop("carrito", None)
        session.pop("cliente_cotizacion", None)

        return render_template(
            "configuracion_seguridad.html",
            mensaje=f"{mensaje_respaldo}. Luego se realizó el reset completo del sistema correctamente."
        )

    except Exception as e:
        conexion.rollback()
        conexion.close()
        return f"El respaldo sí fue enviado, pero ocurrió un error al resetear el sistema: {str(e)}"

@app.route("/configuracion/empresa")
def empresa():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("permiso_configuracion") != 1 and session.get("rol") != "admin":
        return "No tienes permiso para acceder a Empresa"

    return render_template("empresa.html")

@app.route("/gastos_empresa", methods=["GET", "POST"])
def gastos_empresa():
    if "usuario" not in session:
        return redirect(url_for("login"))

    crear_tabla_gastos_empresa()

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    if request.method == "POST":
        tipo = request.form["tipo_gasto"]
        fecha_pago = request.form["fecha_pago"]
        mes = request.form["mes_pagado"]
        monto = request.form["monto"]
        referencia = request.form["referencia"]
        empresa = request.form["empresa_suplidora"]
        metodo = request.form["metodo_pago"]
        estado = request.form["estado"]
        observacion = request.form["observacion"]

        fecha_registro = datetime.now().strftime("%Y-%m-%d")

        cursor.execute("""
            INSERT INTO gastos_empresa
            (tipo_gasto, fecha_pago, mes_pagado, monto, referencia, empresa_suplidora, metodo_pago, estado, observacion, fecha_registro)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (tipo, fecha_pago, mes, monto, referencia, empresa, metodo, estado, observacion, fecha_registro))

        conexion.commit()

    fecha_buscar = request.args.get("fecha_buscar", "").strip()
    tipo_buscar = request.args.get("tipo_buscar", "").strip()

    sql = "SELECT * FROM gastos_empresa"
    condiciones = []
    valores = []

    if fecha_buscar:
        condiciones.append("fecha_pago = ?")
        valores.append(fecha_buscar)

    if tipo_buscar:
        condiciones.append("tipo_gasto = ?")
        valores.append(tipo_buscar)

    if condiciones:
        sql += " WHERE " + " AND ".join(condiciones)

    sql += " ORDER BY tipo_gasto ASC, fecha_pago DESC, id DESC"

    cursor.execute(sql, valores)
    gastos = cursor.fetchall()

    conexion.close()

    return render_template(
        "gastos_empresa.html",
        gastos=gastos,
        fecha_buscar=fecha_buscar,
        tipo_buscar=tipo_buscar
    )

@app.route("/ganancias_empresa")
def ganancias_empresa():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("permiso_configuracion") != 1 and session.get("rol") != "admin":
        return "No tienes permiso para acceder a Ganancias de la Empresa"

    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()
    articulo = request.args.get("articulo", "").strip()

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    sql = """
        SELECT
            COALESCE(NULLIF(TRIM(p.tipo), ''), 'Sin tipo') AS tipo,
            v.nombre_producto,
            COALESCE(MAX(CAST(p.costo AS REAL)), 0) AS costo_unitario,
            COALESCE(MAX(CAST(p.ganancia AS REAL)), 0) AS porcentaje_ganancia,
            COALESCE(MAX(CAST(v.precio AS REAL)), 0) AS precio_venta,
            IFNULL(SUM(CAST(v.cantidad AS INTEGER)), 0) AS cantidad_vendida,
            IFNULL(SUM(CAST(v.cantidad AS INTEGER) * COALESCE(CAST(p.costo AS REAL), 0)), 0) AS inversion_total,
            IFNULL(SUM(CAST(v.total AS REAL)), 0) AS total_vendido,
            IFNULL(SUM(CAST(v.total AS REAL)), 0) - IFNULL(SUM(CAST(v.cantidad AS INTEGER) * COALESCE(CAST(p.costo AS REAL), 0)), 0) AS ganancia_total
        FROM ventas v
        LEFT JOIN productos p ON p.id = v.producto_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM devoluciones d
            WHERE d.venta_id = v.id
              AND d.estado = 'confirmada'
        )
    """

    parametros = []

    if fecha_desde:
        sql += " AND date(v.fecha) >= date(?)"
        parametros.append(fecha_desde)

    if fecha_hasta:
        sql += " AND date(v.fecha) <= date(?)"
        parametros.append(fecha_hasta)

    if articulo:
        sql += " AND lower(v.nombre_producto) LIKE ?"
        parametros.append(f"%{articulo.lower()}%")

    sql += """
        GROUP BY COALESCE(NULLIF(TRIM(p.tipo), ''), 'Sin tipo'), v.nombre_producto
        ORDER BY tipo ASC, v.nombre_producto ASC
    """

    cursor.execute(sql, parametros)
    ganancias = cursor.fetchall()

    total_invertido_general = 0
    total_vendido_general = 0
    ganancia_general = 0

    for g in ganancias:
        total_invertido_general += float(g[6] or 0)
        total_vendido_general += float(g[7] or 0)
        ganancia_general += float(g[8] or 0)

    conexion.close()

    return render_template(
        "ganancias_empresa.html",
        ganancias=ganancias,
        total_invertido_general=total_invertido_general,
        total_vendido_general=total_vendido_general,
        ganancia_general=ganancia_general,
        fecha_desde=fecha_desde,
        fecha_hasta=fecha_hasta,
        articulo=articulo
    )

@app.route("/ganancias_empresa_pdf")
def ganancias_empresa_pdf():
    if "usuario" not in session:
        return redirect(url_for("login"))

    if session.get("permiso_configuracion") != 1 and session.get("rol") != "admin":
        return "No tienes permiso para exportar el PDF de Ganancias de la Empresa"

    fecha_desde = request.args.get("fecha_desde", "").strip()
    fecha_hasta = request.args.get("fecha_hasta", "").strip()
    articulo = request.args.get("articulo", "").strip()

    conexion = sqlite3.connect("pos.db")
    cursor = conexion.cursor()

    sql = """
        SELECT
            COALESCE(NULLIF(TRIM(p.tipo), ''), 'Sin tipo') AS tipo,
            v.nombre_producto,
            COALESCE(MAX(CAST(p.costo AS REAL)), 0) AS costo_unitario,
            COALESCE(MAX(CAST(p.ganancia AS REAL)), 0) AS porcentaje_ganancia,
            COALESCE(MAX(CAST(v.precio AS REAL)), 0) AS precio_venta,
            IFNULL(SUM(CAST(v.cantidad AS INTEGER)), 0) AS cantidad_vendida,
            IFNULL(SUM(CAST(v.cantidad AS INTEGER) * COALESCE(CAST(p.costo AS REAL), 0)), 0) AS inversion_total,
            IFNULL(SUM(CAST(v.total AS REAL)), 0) AS total_vendido,
            IFNULL(SUM(CAST(v.total AS REAL)), 0) - IFNULL(SUM(CAST(v.cantidad AS INTEGER) * COALESCE(CAST(p.costo AS REAL), 0)), 0) AS ganancia_total
        FROM ventas v
        LEFT JOIN productos p ON p.id = v.producto_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM devoluciones d
            WHERE d.venta_id = v.id
              AND d.estado = 'confirmada'
        )
    """

    parametros = []

    if fecha_desde:
        sql += " AND date(v.fecha) >= date(?)"
        parametros.append(fecha_desde)

    if fecha_hasta:
        sql += " AND date(v.fecha) <= date(?)"
        parametros.append(fecha_hasta)

    if articulo:
        sql += " AND lower(v.nombre_producto) LIKE ?"
        parametros.append(f"%{articulo.lower()}%")

    sql += """
        GROUP BY COALESCE(NULLIF(TRIM(p.tipo), ''), 'Sin tipo'), v.nombre_producto
        ORDER BY tipo ASC, v.nombre_producto ASC
    """

    cursor.execute(sql, parametros)
    ganancias = cursor.fetchall()
    conexion.close()

    total_invertido_general = 0
    total_vendido_general = 0
    ganancia_general = 0

    for g in ganancias:
        total_invertido_general += float(g[6] or 0)
        total_vendido_general += float(g[7] or 0)
        ganancia_general += float(g[8] or 0)

    carpeta = "reportes"
    if not os.path.exists(carpeta):
        os.makedirs(carpeta)

    fecha_archivo = datetime.now().strftime("%Y%m%d_%H%M%S")
    archivo = f"{carpeta}/ganancias_empresa_{fecha_archivo}.pdf"

    c = canvas.Canvas(archivo, pagesize=letter)
    width, height = letter

    y = height - 40

    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, y, "Ganancias de la Empresa")
    y -= 25

    c.setFont("Helvetica", 10)
    filtro_texto = "Filtros: "
    if fecha_desde:
        filtro_texto += f"Desde {fecha_desde}  "
    if fecha_hasta:
        filtro_texto += f"Hasta {fecha_hasta}  "
    if articulo:
        filtro_texto += f"Articulo: {articulo}"

    if filtro_texto == "Filtros: ":
        filtro_texto += "Todos"

    c.drawString(40, y, filtro_texto)
    y -= 25

    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, y, f"Total invertido: RD$ {total_invertido_general:.2f}")
    c.drawString(230, y, f"Total vendido: RD$ {total_vendido_general:.2f}")
    c.drawString(410, y, f"Ganancia: RD$ {ganancia_general:.2f}")
    y -= 30

    c.setFont("Helvetica-Bold", 8)
    c.drawString(40, y, "Tipo")
    c.drawString(95, y, "Producto")
    c.drawString(220, y, "Costo")
    c.drawString(275, y, "%")
    c.drawString(310, y, "Precio")
    c.drawString(365, y, "Cant.")
    c.drawString(405, y, "Invertido")
    c.drawString(475, y, "Vendido")
    c.drawString(540, y, "Ganancia")
    y -= 15

    c.line(40, y, 570, y)
    y -= 15

    tipo_actual = ""

    c.setFont("Helvetica", 8)

    for g in ganancias:
        tipo = str(g[0])
        producto = str(g[1])[:20]
        costo = float(g[2] or 0)
        porcentaje = float(g[3] or 0)
        precio = float(g[4] or 0)
        cantidad = int(g[5] or 0)
        invertido = float(g[6] or 0)
        vendido = float(g[7] or 0)
        ganancia = float(g[8] or 0)

        if y < 60:
            c.showPage()
            y = height - 40

            c.setFont("Helvetica-Bold", 8)
            c.drawString(40, y, "Tipo")
            c.drawString(95, y, "Producto")
            c.drawString(220, y, "Costo")
            c.drawString(275, y, "%")
            c.drawString(310, y, "Precio")
            c.drawString(365, y, "Cant.")
            c.drawString(405, y, "Invertido")
            c.drawString(475, y, "Vendido")
            c.drawString(540, y, "Ganancia")
            y -= 15

            c.line(40, y, 570, y)
            y -= 15
            c.setFont("Helvetica", 8)

        if tipo_actual != tipo:
            c.setFont("Helvetica-Bold", 9)
            c.drawString(40, y, f"Tipo: {tipo}")
            y -= 15
            c.setFont("Helvetica", 8)
            tipo_actual = tipo

        c.drawString(40, y, tipo[:10])
        c.drawString(95, y, producto)
        c.drawRightString(260, y, f"{costo:.2f}")
        c.drawRightString(295, y, f"{porcentaje:.2f}")
        c.drawRightString(350, y, f"{precio:.2f}")
        c.drawRightString(390, y, f"{cantidad}")
        c.drawRightString(465, y, f"{invertido:.2f}")
        c.drawRightString(530, y, f"{vendido:.2f}")
        c.drawRightString(590, y, f"{ganancia:.2f}")
        y -= 15

    c.save()

    return send_file(archivo, as_attachment=False)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))





crear_tabla_configuracion()
crear_tabla_seguridad_reset()
crear_tabla_devoluciones()
agregar_columna_factura_id_ventas()
crear_tabla_configuracion()
crear_tabla_configuracion()
crear_tabla_gastos_empresa()
agregar_columnas_productos_empresa()
agregar_columnas_productos_empresa()
crear_tabla_devoluciones()
agregar_columna_factura_id_ventas()



if __name__ == "__main__":
    app.run(debug=True)