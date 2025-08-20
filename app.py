import os, sqlite3
from datetime import datetime
from functools import wraps

from flask import (
    Flask, jsonify, request, render_template,
    send_file, g, session, redirect, url_for
)
import pandas as pd

# ============== Config básica y paths ==============
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.getenv('INSTANCE_DIR', os.path.join(BASE_DIR, 'instance'))
DB_PATH = os.path.join(INSTANCE_DIR, 'app.db')
os.makedirs(INSTANCE_DIR, exist_ok=True)    

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['DATABASE'] = DB_PATH

# Clave de sesión (usa env en producción)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret-change-me')

# Ajustes cookies de sesión (recomendado)
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    # SESSION_COOKIE_SECURE=True,  # habilítalo si sirves por HTTPS
)

# Credenciales admin (usa env en producción)
ADMIN_USER = os.getenv('ADMIN_USER', 'admin')
ADMIN_PASS = os.getenv('ADMIN_PASS', '1234')

# ============== DB helpers ==============
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            phone TEXT NOT NULL,
            message TEXT,
            created_at TEXT NOT NULL
        );
    """)
    db.commit()

def debug_print_db_status():
    print(f"[DB] Usando archivo: {DB_PATH}")
    with sqlite3.connect(DB_PATH) as conn:
        tables = pd.read_sql(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;",
            conn
        )
        print("[DB] Tablas disponibles:\n", tables if not tables.empty else "(ninguna)")
        if not tables.empty and 'clients' in tables['name'].values:
            df = pd.read_sql("SELECT * FROM clients LIMIT 5;", conn)
            print("[DB] Muestra de clients:\n", df)

# ============== Auth (sesión) ==============
def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('logged_in'):
            session['next'] = request.path
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            dest = session.pop('next', None) or url_for('admin')
            return redirect(dest)
        error = 'Credenciales inválidas'
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ============== Vistas ==============
@app.route('/')
def home():
    return render_template('index.html')

@app.route('/admin')
@login_required
def admin():
    return render_template('admin.html')

# ============== API ==============
# GET protegido (solo admin)
@app.route('/api/clients', methods=['GET'])
@login_required
def list_clients():
    db = get_db()
    cur = db.execute(
        'SELECT id, name, email, phone, message, created_at FROM clients ORDER BY id DESC'
    )
    rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)

# POST público (form de la landing)
@app.route('/api/clients', methods=['POST'])
def create_client():
    data = request.get_json(silent=True) or {}
    required = ['name', 'email', 'phone', 'message']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'ok': False, 'error': f"Faltan campos obligatorios: {', '.join(missing)}"}), 400
    print("Datos recibidos:", data)

    db = get_db()
    db.execute(
        'INSERT INTO clients (name, email, phone, message, created_at) VALUES (?,?,?,?,?)',
        (
            data['name'].strip(),
            data['email'].strip(),
            data['phone'].strip(),
            data['message'].strip(),
            datetime.utcnow().isoformat()
        )
    )
    db.commit()
    return jsonify({'ok': True, 'message': "Cliente guardado correctamente."})

# Export a Excel (protegido)
@app.route('/export/excel', methods=['GET'])
@login_required
def export_excel():
    try:
        db = get_db()
        cur = db.execute(
            'SELECT id, name, email, phone, message, created_at FROM clients ORDER BY id ASC'
        )
        rows = [dict(r) for r in cur.fetchall()]
        cols = ['id', 'name', 'email', 'phone', 'message', 'created_at']
        df = pd.DataFrame.from_records(rows, columns=cols) if rows else pd.DataFrame(columns=cols)

        export_path = os.path.join(INSTANCE_DIR, 'clients_export.xlsx')
        try:
            df.to_excel(export_path, index=False, engine='openpyxl')
        except PermissionError:
            return jsonify({'ok': False, 'error': 'Cierra el archivo Excel y vuelve a intentar.'}), 423

        return send_file(export_path, as_attachment=True, download_name='clients_export.xlsx')
    except Exception as e:
        return jsonify({'ok': False, 'error': f'Error exportando: {e}'}), 500

# Datos de prueba
@app.route('/api/seed', methods=['POST'])
@login_required
def seed():
    db = get_db()
    db.execute(
        'INSERT INTO clients (name, email, phone, message, created_at) VALUES (?,?,?,?,?)',
        ('Prueba Uno', 'uno@demo.com', '3000000000', 'Mensaje de prueba 1', datetime.utcnow().isoformat())
    )
    db.execute(
        'INSERT INTO clients (name, email, phone, message, created_at) VALUES (?,?,?,?,?)',
        ('Prueba Dos', 'dos@demo.com', '3000000001', 'Mensaje de prueba 2', datetime.utcnow().isoformat())
    )
    db.commit()
    return jsonify({'ok': True, 'message': 'Datos de prueba insertados.'})

# ============== Main ==============
if __name__ == '__main__':
    # Limpia confusiones previas: elimina DB en raíz si existe
    legacy = os.path.join(BASE_DIR, 'app.db')
    if os.path.exists(legacy):
        try:
            os.remove(legacy)
            print(f"[DB] Eliminado DB antiguo en raíz: {legacy}")
        except Exception as e:
            print(f"[DB] Aviso: no se pudo eliminar {legacy}: {e}")

    with app.app_context():
        init_db()
        debug_print_db_status()

    port = int(os.getenv("PORT", "5000"))
    app.run(host='0.0.0.0', port=port, debug=False)
