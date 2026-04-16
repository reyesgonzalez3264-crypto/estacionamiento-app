from flask import Flask, render_template, request, redirect, url_for
import psycopg2
import psycopg2.extras
import os

app = Flask(__name__)

# ---------------- DB ----------------
def get_db():
    DATABASE_URL = os.environ.get("DATABASE_URL")
    conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return conn

# ---------------- INIT ----------------
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS talonarios")
    cursor.execute("DROP TABLE IF EXISTS registros")

    cursor.execute('''
    CREATE TABLE registros (
        id SERIAL PRIMARY KEY,
        fecha TEXT,
        empleado TEXT,
        total_ingresado REAL,
        gastos REAL,
        desc_gastos TEXT,
        sueldos REAL,
        desc_sueldos TEXT,
        total_final REAL
    )
    ''')

    cursor.execute('''
    CREATE TABLE talonarios (
        id SERIAL PRIMARY KEY,
        registro_id INTEGER,
        inicio INTEGER,
        fin INTEGER,
        monto REAL
    )
    ''')

    conn.commit()
    conn.close()

init_db()

# ---------------- DASHBOARD ----------------
@app.route('/')
def dashboard():
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM registros ORDER BY fecha DESC")
    registros = cursor.fetchall()

    total_ingresos = sum([r['total_ingresado'] or 0 for r in registros])
    total_gastos = sum([r['gastos'] or 0 for r in registros])
    total_sueldos = sum([r['sueldos'] or 0 for r in registros])
    total_utilidad = sum([r['total_final'] or 0 for r in registros])

    conn.close()

    return render_template('dashboard.html', registros=registros,
                           total_ingresos=total_ingresos,
                           total_gastos=total_gastos,
                           total_sueldos=total_sueldos,
                           total_utilidad=total_utilidad)

# ---------------- AGREGAR ----------------
@app.route('/agregar', methods=['POST'])
def agregar():
    fecha = request.form['fecha']
    empleado = request.form['empleado']
    gastos = float(request.form.get('gastos') or 0)
    desc_gastos = request.form.get('desc_gastos')
    sueldos = float(request.form.get('sueldos') or 0)
    desc_sueldos = request.form.get('desc_sueldos')

    inicios = request.form.getlist('inicio[]')
    fines = request.form.getlist('fin[]')
    montos = request.form.getlist('monto[]')

    total_ingresado = 0

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
    INSERT INTO registros (fecha, empleado, total_ingresado, gastos, desc_gastos, sueldos, desc_sueldos, total_final)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    RETURNING id
    ''', (fecha, empleado, 0, gastos, desc_gastos, sueldos, desc_sueldos, 0))

    registro_id = cursor.fetchone()['id']

    for i, f, m in zip(inicios, fines, montos):
        if i and f and m:
            i = int(i)
            f = int(f)
            m = float(m)
            total_ingresado += m

            cursor.execute('''
            INSERT INTO talonarios (registro_id, inicio, fin, monto)
            VALUES (%s, %s, %s, %s)
            ''', (registro_id, i, f, m))

    total_final = total_ingresado - (gastos + sueldos)

    cursor.execute('''
    UPDATE registros SET total_ingresado=%s, total_final=%s WHERE id=%s
    ''', (total_ingresado, total_final, registro_id))

    conn.commit()
    conn.close()

    return redirect(url_for('dashboard'))

# ---------------- ELIMINAR ----------------
@app.route('/eliminar/<int:id>')
def eliminar(id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM talonarios WHERE registro_id=%s", (id,))
    cursor.execute("DELETE FROM registros WHERE id=%s", (id,))

    conn.commit()
    conn.close()
    return redirect(url_for('dashboard'))

# ---------------- EDITAR ----------------
@app.route('/editar/<int:id>', methods=['GET','POST'])
def editar(id):
    conn = get_db()
    cursor = conn.cursor()

    if request.method == 'POST':
        fecha = request.form['fecha']
        empleado = request.form['empleado']
        gastos = float(request.form.get('gastos') or 0)
        sueldos = float(request.form.get('sueldos') or 0)

        cursor.execute("""
        UPDATE registros SET fecha=%s, empleado=%s, gastos=%s, sueldos=%s WHERE id=%s
        """, (fecha, empleado, gastos, sueldos, id))

        conn.commit()
        conn.close()
        return redirect(url_for('dashboard'))

    cursor.execute("SELECT * FROM registros WHERE id=%s", (id,))
    registro = cursor.fetchone()

    conn.close()
    return render_template('editar.html', r=registro)

# ---------------- REPORTE ----------------
@app.route('/reporte/<int:id>')
def reporte(id):
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM registros WHERE id=%s", (id,))
    registro = cursor.fetchone()

    cursor.execute("SELECT * FROM talonarios WHERE registro_id=%s", (id,))
    talonarios = cursor.fetchall()

    conn.close()
    return render_template('reporte.html', r=registro, talonarios=talonarios)

# ---------------- RUN ----------------
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)