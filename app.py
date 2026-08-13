import os
from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'mi_clave_secreta'

# Forzar a Flask a no guardar en caché los archivos HTML al desarrollar
app.config['TEMPLATES_AUTO_RELOAD'] = True

# --- CONFIGURACIÓN DE SUBIDA DE IMÁGENES ---
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configuración de la conexión a MySQL
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',       # Cambia si usas otro usuario
    'password': '12345',    # Cambia según tu clave de MySQL
    'database': 'biblioteca_virtual'  # Actualizado al nombre del nuevo script
}

def obtener_conexion():
    """Crea y retorna una conexión a la base de datos MySQL."""
    try:
        conexion = mysql.connector.connect(**DB_CONFIG)
        return conexion
    except Error as e:
        print(f"Error al conectar a la base de datos: {e}")
        return None

@app.route('/')
def index():
    busqueda = request.args.get('busqueda', '').strip()
    id_categoria_str = request.args.get('categoria', '').strip()
    
    categoria_id = int(id_categoria_str) if id_categoria_str.isdigit() else None

    conexion = obtener_conexion()
    
    categorias = []
    libros = []
    autores = []

    if conexion and conexion.is_connected():
        cursor = conexion.cursor(dictionary=True)

        try:
            # A. Obtener categorías para la barra lateral
            cursor.execute("SELECT id_categoria, nombre FROM categorias ORDER BY nombre ASC")
            categorias = cursor.fetchall()

            # B. Consultar libros con filtros dinámicos
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

            # C. Consultar autores destacados desde la tabla 'autores'
            cursor.execute("SELECT nombre_autor AS autor, foto_perfil AS foto FROM autores LIMIT 4")
            autores = cursor.fetchall()

        except Error as e:
            print(f"Error en las consultas SQL: {e}")
        finally:
            cursor.close()
            conexion.close()

    return render_template(
        'index.html',
        libros=libros,
        categorias=categorias,
        autores=autores,
        categoria_actual=categoria_id,
        busqueda=busqueda
    )

# RUTA 1: Muestra la vista/formulario para agregar libro (Petición GET)
@app.route('/agregar-libro', methods=['GET'])
def agregar_libro():
    conexion = obtener_conexion()
    categorias = []
    autores = []
    
    if conexion and conexion.is_connected():
        try:
            cursor = conexion.cursor(dictionary=True)
            cursor.execute("SELECT id_categoria, nombre FROM categorias ORDER BY nombre ASC")
            categorias = cursor.fetchall()

            cursor.execute("SELECT id_autor, nombre_autor FROM autores ORDER BY nombre_autor ASC")
            autores = cursor.fetchall()
        except Error as e:
            print(f"Error al obtener categorías/autores: {e}")
        finally:
            cursor.close()
            conexion.close()

    return render_template('agregar_libro.html', categorias=categorias, autores=autores)


# RUTA 2: Recibe y guarda los datos del formulario (Petición POST)
@app.route('/guardar-libro', methods=['POST'])
def guardar_libro():
    titulo = request.form.get('titulo')
    id_autor = request.form.get('id_autor')
    stock = request.form.get('stock', 0)
    descripcion = request.form.get('descripcion')
    id_categoria = request.form.get('id_categoria')

    # Validar que el stock no supere las 10 unidades
    try:
        stock = int(stock)
        if stock > 10:
            stock = 10
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
        try:
            cursor = conexion.cursor()
            query = """
                INSERT INTO libros (titulo, descripcion, stock, id_categoria, id_autor, imagen_portada)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (titulo, descripcion, stock, id_categoria, id_autor, nombre_imagen))
            conexion.commit()
            flash('¡Libro agregado exitosamente!', 'exito')
        except Error as e:
            print(f"Error al insertar libro en la base de datos: {e}")
            flash('Error al intentar guardar el libro.', 'error')
        finally:
            cursor.close()
            conexion.close()

    return redirect(url_for('index'))


# ==========================================
# NUEVA RUTA: Muestra los últimos 10 préstamos
# ==========================================
@app.route('/ultimos-prestamos')
def ultimos_prestamos():
    conexion = obtener_conexion()
    prestamos = []

    if conexion and conexion.is_connected():
        try:
            cursor = conexion.cursor(dictionary=True)
            # Consultamos la vista que creamos en MySQL
            cursor.execute("SELECT * FROM vista_ultimos_prestamos")
            prestamos = cursor.fetchall()
        except Error as e:
            print(f"Error al obtener los últimos préstamos: {e}")
        finally:
            cursor.close()
            conexion.close()

    return render_template('ultimos_prestamos.html', prestamos=prestamos)


if __name__ == '__main__':
    app.run(debug=True)