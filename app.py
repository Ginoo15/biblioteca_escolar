import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'mi_clave_secreta_biblioteca'

app.config['TEMPLATES_AUTO_RELOAD'] = True

# Guardar imágenes directamente en static
STATIC_FOLDER = os.path.join(app.root_path, 'static')
app.config['UPLOAD_FOLDER'] = STATIC_FOLDER

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '12345',  # Ajusta tu contraseña aquí
    'database': 'biblioteca_virtual'
}

def obtener_conexion():
    try:
        conexion = mysql.connector.connect(**DB_CONFIG)
        return conexion
    except Error as e:
        print(f"Error de conexión a la BD: {e}")
        return None

# ==========================================
# POBLADO Y VERIFICACIÓN DE DATOS DEMO
# ==========================================
def asegurar_datos_demo():
    """Asegura que existan categorías, autores y libros basados en el script SQL."""
    conexion = obtener_conexion()
    if not conexion or not conexion.is_connected():
        return

    cursor = conexion.cursor(dictionary=True)
    try:
        # 1. Categorías
        categorias_demo = [
            ("Acción y Aventura",),
            ("Terror y Suspenso",),
            ("Ciencia Ficción",),
            ("Historia y Biografías",),
            ("Matemáticas y Ciencias",),
            ("Infantil y Juvenil",),
            ("Cómics y Manga",),
            ("Literatura Clásica",)
        ]
        cursor.executemany(
            "INSERT IGNORE INTO categorias (nombre) VALUES (%s)", 
            categorias_demo
        )

        # 2. Autores
        autores_demo = [
            ("Antoine de Saint-Exupéry", "uploads/elprincito.webp"),
            ("Gabriel García Márquez", "uploads/cienaños.webp"),
            ("Stephen King", "uploads/default_autor.jpg"),
            ("J.K. Rowling", "uploads/default_autor.jpg"),
            ("Michael Crichton", "uploads/default_autor.jpg"),
            ("Vegetta777 y Willyrex", "uploads/default_autor.jpg"),
            ("Marvel / Panini Comics", "uploads/default_autor.jpg"),
            ("Kentaro Miura", "uploads/default_autor.jpg"),
            ("George Orwell", "uploads/default_autor.jpg"),
            ("Natalia y Mayden", "uploads/default_autor.jpg")
        ]
        cursor.executemany(
            "INSERT IGNORE INTO autores (nombre_autor, foto_perfil) VALUES (%s, %s)", 
            autores_demo
        )
        conexion.commit()

        # 3. Mapear IDs dinámicamente
        cursor.execute("SELECT id_categoria, nombre FROM categorias")
        cats = {row['nombre']: row['id_categoria'] for row in cursor.fetchall()}

        cursor.execute("SELECT id_autor, nombre_autor FROM autores")
        auts = {row['nombre_autor']: row['id_autor'] for row in cursor.fetchall()}

        # 4. Verificar presencia de libros
        cursor.execute("SELECT COUNT(*) as total FROM libros")
        total_libros = cursor.fetchone()['total']

        if total_libros < 5:
            libros_a_insertar = [
                ('El Principito', 'Un viaje poético sobre la infancia y la amistad.', 8, 'uploads/elprincito.webp', cats.get('Acción y Aventura'), auts.get('Antoine de Saint-Exupéry')),
                ('Cien Años de Soledad', 'La saga familiar de los Buendía en Macondo.', 5, 'uploads/cienaños.webp', cats.get('Literatura Clásica'), auts.get('Gabriel García Márquez')),
                ('IT (Eso)', 'Un grupo de niños enfrenta a una entidad maligna en Derry.', 4, 'uploads/9788497593793.jpg', cats.get('Terror y Suspenso'), auts.get('Stephen King')),
                ('Harry Potter y la Piedra Filosofal', 'El inicio de las aventuras del joven mago.', 9, 'uploads/ee23df3a67f6f27ab8645debc9f6d5e3.jpg', cats.get('Infantil y Juvenil'), auts.get('J.K. Rowling')),
                ('Parque Jurásico', 'Un parque temático con dinosaurios clonados se sale de control tras una falla de seguridad.', 5, 'uploads/6866ada085d4f.jpeg', cats.get('Ciencia Ficción'), auts.get('Michael Crichton')),
                ('Wigetta y el Báculo Dorado', 'Una aventura llena de misterio y realidad aumentada con Vegetta y Willyrex.', 8, 'uploads/71RAk23GX-L._SL1500_.jpg', cats.get('Infantil y Juvenil'), auts.get('Vegetta777 y Willyrex')),
                ('Predator: La Etapa Original', 'Colección de cómics clásicos del cazador extraterrestre.', 4, 'uploads/91bLksEsWXL._SY522_.jpg', cats.get('Cómics y Manga'), auts.get('Marvel / Panini Comics')),
                ('Berserk Vol. 30', 'Guts continúa su viaje enfrentando monstruosidades y fuerzas oscuras.', 3, 'uploads/91ReT4NNI0L._SL1500_.jpg', cats.get('Cómics y Manga'), auts.get('Kentaro Miura')),
                ('1984', 'Novela distópica sobre el control estatal y la vigilancia constante del Gran Hermano.', 6, 'uploads/1984.jpg', cats.get('Literatura Clásica'), auts.get('George Orwell')),
                ('Cómo sobrevivir a un apocalipsis zombi con ExpCaseros', 'Guía práctica e ilustrada con experimentos y consejos para salir con vida.', 7, 'uploads/9788427045514.webp', cats.get('Infantil y Juvenil'), auts.get('Natalia y Mayden')),
                ('El Arte de Berserk', 'Recopilación del arte técnico e ilustraciones del universo creado por Kentaro Miura.', 2, 'uploads/berserk.webp', cats.get('Cómics y Manga'), auts.get('Kentaro Miura'))
            ]
            
            query = """
                INSERT INTO libros (titulo, descripcion, stock, imagen_portada, id_categoria, id_autor)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.executemany(query, libros_a_insertar)
            conexion.commit()

    except Error as e:
        print(f"Error verificando datos demo: {e}")
    finally:
        cursor.close()
        conexion.close()

# Ejecutar verificación inicial de datos
asegurar_datos_demo()

# ==========================================
# RUTA PRINCIPAL / CATÁLOGO DE LIBROS
# ==========================================
@app.route('/')
def index():
    busqueda = request.args.get('busqueda', '').strip()
    id_categoria_str = request.args.get('categoria', '').strip()
    
    categoria_id = int(id_categoria_str) if id_categoria_str.isdigit() else None

    conexion = obtener_conexion()
    categorias = []
    libros = []

    if conexion and conexion.is_connected():
        cursor = conexion.cursor(dictionary=True)
        try:
            # 1. Categorías para el menú de filtros
            cursor.execute("SELECT id_categoria, nombre FROM categorias ORDER BY nombre ASC")
            categorias = cursor.fetchall()

            # 2. Búsqueda y filtrado dinámico de libros
            query_libros = """
                SELECT l.*, a.nombre_autor AS autor, c.nombre AS categoria_nombre 
                FROM libros l 
                LEFT JOIN autores a ON l.id_autor = a.id_autor 
                LEFT JOIN categorias c ON l.id_categoria = c.id_categoria
                WHERE 1=1
            """
            params_libros = []

            if busqueda:
                query_libros += " AND (l.titulo LIKE %s OR a.nombre_autor LIKE %s)"
                params_libros.extend([f"%{busqueda}%", f"%{busqueda}%"])

            if categoria_id:
                query_libros += " AND l.id_categoria = %s"
                params_libros.append(categoria_id)

            query_libros += " ORDER BY l.id_libro DESC"
            cursor.execute(query_libros, params_libros)
            libros = cursor.fetchall()

            # Sanitizado de rutas de imagen para compatibilidad con url_for('static', ...)
            for libro in libros:
                if libro.get('imagen_portada'):
                    libro['imagen_portada'] = libro['imagen_portada'].replace('uploads/', '')

        except Error as e:
            print(f"Error en consulta index: {e}")
        finally:
            cursor.close()
            conexion.close()

    return render_template(
        'index.html',
        libros=libros,
        categorias=categorias,
        categoria_actual=categoria_id,
        busqueda=busqueda
    )

# ==========================================
# GESTIÓN DE USUARIOS
# ==========================================
@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        dni = request.form.get('dni', '').strip()
        nombre = request.form.get('nombre', '').strip()
        apellido = request.form.get('apellido', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        if not (dni and nombre and apellido and email and password):
            flash('Por favor completa todos los campos requeridos.', 'error')
            return redirect(url_for('registro'))

        pass_hash = generate_password_hash(password)

        conexion = obtener_conexion()
        if conexion and conexion.is_connected():
            cursor = conexion.cursor(dictionary=True)
            try:
                cursor.execute("SELECT id_usuario FROM usuarios WHERE email = %s OR dni = %s", (email, dni))
                usuario_existente = cursor.fetchone()

                if usuario_existente:
                    flash('El correo o DNI ingresado ya se encuentra registrado.', 'error')
                    return redirect(url_for('registro'))

                query = """
                    INSERT INTO usuarios (dni, nombre, apellido, email, password_hash)
                    VALUES (%s, %s, %s, %s, %s)
                """
                cursor.execute(query, (dni, nombre, apellido, email, pass_hash))
                conexion.commit()

                flash('¡Registro exitoso! Ya puedes iniciar sesión con tu cuenta.', 'exito')
                return redirect(url_for('login'))

            except Error as e:
                conexion.rollback()
                print(f"Error al registrar usuario: {e}")
                flash('Ocurrió un error interno al registrar el usuario.', 'error')
            finally:
                cursor.close()
                conexion.close()

    return render_template('registro.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()

        conexion = obtener_conexion()
        if conexion and conexion.is_connected():
            cursor = conexion.cursor(dictionary=True)
            try:
                cursor.execute("SELECT * FROM usuarios WHERE email = %s", (email,))
                usuario = cursor.fetchone()

                if usuario and check_password_hash(usuario['password_hash'], password):
                    session['id_usuario'] = usuario['id_usuario']
                    session['nombre_completo'] = f"{usuario['nombre']} {usuario['apellido']}"
                    flash(f"¡Bienvenido/a {usuario['nombre']}!", 'exito')
                    return redirect(url_for('index'))
                else:
                    flash('Credenciales incorrectas. Revisa tu correo y contraseña.', 'error')

            except Error as e:
                print(f"Error en login: {e}")
                flash('Ocurrió un error al intentar iniciar sesión.', 'error')
            finally:
                cursor.close()
                conexion.close()

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Has cerrado sesión correctamente.', 'exito')
    return redirect(url_for('index'))

# ==========================================
# SOLICITUD DE PRÉSTAMOS
# ==========================================
@app.route('/solicitar-prestamo', methods=['GET', 'POST'])
def solicitar_prestamo():
    if request.method == 'POST':
        id_usuario = request.form.get('id_usuario')
        id_libro = request.form.get('id_libro')
        fecha_limite = request.form.get('fecha_limite_devolucion')

        if not (id_usuario and id_libro and fecha_limite):
            flash('Por favor completa todos los campos del préstamo.', 'error')
            return redirect(url_for('solicitar_prestamo'))

        conexion = obtener_conexion()
        if conexion and conexion.is_connected():
            cursor = conexion.cursor(dictionary=True)
            try:
                cursor.execute("SELECT stock, titulo FROM libros WHERE id_libro = %s", (id_libro,))
                libro = cursor.fetchone()

                if not libro or libro['stock'] <= 0:
                    flash('El libro seleccionado no cuenta con unidades disponibles.', 'error')
                    return redirect(url_for('solicitar_prestamo'))

                query_prestamo = """
                    INSERT INTO prestamos (id_usuario, id_libro, fecha_retiro, fecha_limite_devolucion)
                    VALUES (%s, %s, CURRENT_DATE(), %s)
                """
                cursor.execute(query_prestamo, (id_usuario, id_libro, fecha_limite))

                cursor.execute("UPDATE libros SET stock = stock - 1 WHERE id_libro = %s", (id_libro,))

                conexion.commit()
                flash(f'¡Préstamo de "{libro["titulo"]}" registrado con éxito!', 'exito')
                return redirect(url_for('ultimos_prestamos'))

            except Error as e:
                conexion.rollback()
                print(f"Error procesando préstamo: {e}")
                flash('Error al procesar el préstamo.', 'error')
            finally:
                cursor.close()
                conexion.close()

    # Petición GET
    id_libro_preseleccionado = request.args.get('id_libro')
    conexion = obtener_conexion()
    libros = []
    usuarios = []

    if conexion and conexion.is_connected():
        cursor = conexion.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id_libro, titulo, stock FROM libros WHERE stock > 0 ORDER BY titulo ASC")
            libros = cursor.fetchall()

            cursor.execute("""
                SELECT id_usuario, dni, nombre, apellido, 
                       CONCAT(nombre, ' ', apellido) AS nombre_completo 
                FROM usuarios 
                ORDER BY apellido ASC
            """)
            usuarios = cursor.fetchall()
        except Error as e:
            print(f"Error al cargar formulario de préstamos: {e}")
        finally:
            cursor.close()
            conexion.close()

    return render_template(
        'solicitar_prestamo.html', 
        libros=libros, 
        usuarios=usuarios, 
        id_libro_preseleccionado=id_libro_preseleccionado
    )

# ==========================================
# VISTA Y ADMINISTRACIÓN
# ==========================================
@app.route('/ultimos-prestamos')
def ultimos_prestamos():
    conexion = obtener_conexion()
    prestamos = []

    if conexion and conexion.is_connected():
        cursor = conexion.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM vista_ultimos_prestamos")
            prestamos = cursor.fetchall()
        except Error as e:
            print(f"Error consultando vista_ultimos_prestamos: {e}")
        finally:
            cursor.close()
            conexion.close()

    return render_template('ultimos_prestamos.html', prestamos=prestamos)

@app.route('/agregar-libro', methods=['GET', 'POST'])
def agregar_libro():
    if request.method == 'POST':
        titulo = request.form.get('titulo')
        id_autor = request.form.get('id_autor')
        stock = request.form.get('stock', 0)
        descripcion = request.form.get('descripcion')
        id_categoria = request.form.get('id_categoria')

        try:
            stock = min(max(0, int(stock)), 10)
        except ValueError:
            stock = 0

        imagen = request.files.get('imagen_portada')
        nombre_imagen = 'default_libro.jpg'

        if imagen and imagen.filename != '':
            filename = secure_filename(imagen.filename)
            ruta_guardado = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagen.save(ruta_guardado)
            nombre_imagen = filename

        conexion = obtener_conexion()
        if conexion and conexion.is_connected():
            cursor = conexion.cursor()
            try:
                query = """
                    INSERT INTO libros (titulo, descripcion, stock, id_categoria, id_autor, imagen_portada)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (titulo, descripcion, stock, id_categoria, id_autor, nombre_imagen))
                conexion.commit()
                flash('¡Libro agregado exitosamente!', 'exito')
            except Error as e:
                print(f"Error guardando libro: {e}")
                flash('Error al intentar guardar el libro.', 'error')
            finally:
                cursor.close()
                conexion.close()

        return redirect(url_for('index'))

    conexion = obtener_conexion()
    categorias = []
    autores = []
    if conexion and conexion.is_connected():
        cursor = conexion.cursor(dictionary=True)
        try:
            cursor.execute("SELECT id_categoria, nombre FROM categorias ORDER BY nombre ASC")
            categorias = cursor.fetchall()

            cursor.execute("SELECT id_autor, nombre_autor FROM autores ORDER BY nombre_autor ASC")
            autores = cursor.fetchall()
        except Error as e:
            print(f"Error obteniendo datos para formulario de agregar libro: {e}")
        finally:
            cursor.close()
            conexion.close()

    return render_template('agregar_libro.html', categorias=categorias, autores=autores)

if __name__ == '__main__':
    app.run(debug=True)