import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
import mysql.connector
from mysql.connector import Error
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'mi_clave_secreta_biblioteca'

app.config['TEMPLATES_AUTO_RELOAD'] = True

UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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
            # 1. Categorías para la barra lateral
            cursor.execute("SELECT id_categoria, nombre FROM categorias ORDER BY nombre ASC")
            categorias = cursor.fetchall()

            # 2. Búsqueda y filtrado dinámico de libros
            query_libros = """
                SELECT l.*, a.nombre_autor AS autor 
                FROM libros l 
                LEFT JOIN autores a ON l.id_autor = a.id_autor 
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
            stock = min(int(stock), 10)
        except ValueError:
            stock = 0

        imagen = request.files.get('imagen_portada')
        nombre_imagen = 'uploads/default_libro.jpg'

        if imagen and imagen.filename != '':
            filename = secure_filename(imagen.filename)
            ruta_guardado = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagen.save(ruta_guardado)
            nombre_imagen = f"uploads/{filename}"

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