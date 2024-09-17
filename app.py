from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection

app = Flask(__name__)
app.secret_key = 'samuelss'

@app.route('/')
def index():
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['loginUser']
        password = request.form['senha']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT tipoUser, senha FROM usuarios WHERE loginUser = %s', (username,))
        user = cur.fetchone()
        cur.close()
        conn.close()

        if user is None:
            flash('Usuário não encontrado!', 'error')
            return redirect(url_for('login'))

        if user and check_password_hash(user[1], password):
            session['username'] = username
            session['tipoUser'] = user[0]
            return redirect(url_for('dashboard'))
        else:
            flash('Usuário ou senha inválidos!', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['loginUser']
        password = request.form['senha']
        email = request.form.get('email', '')
        user_type = request.form['tipoUser']

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute('SELECT * FROM usuarios WHERE loginUser = %s', (username,))
        existing_user = cur.fetchone()

        if existing_user:
            flash('Usuário já cadastrado!', 'error')
            return redirect(url_for('register'))

        try:
            hashed_password = generate_password_hash(password)
            cur.execute('INSERT INTO usuarios (loginUser, senha, tipoUser) VALUES (%s, %s, %s)',
                        (username, hashed_password, user_type))
            conn.commit()
            flash('Usuário cadastrado com sucesso!')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Erro ao cadastrar usuário: {e}', 'error')
        finally:
            cur.close()
            conn.close()

    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM produtos')
    products = cur.fetchall()
    cur.close()
    conn.close()

    return render_template('dashboard.html', products=products)

@app.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'username' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if session['tipoUser'] == 'normal':
            conn = get_db_connection()
            cur = conn.cursor()
            cur.execute('SELECT COUNT(*) FROM produtos WHERE loginUser = %s', (session['username'],))
            count = cur.fetchone()[0]
            cur.close()
            conn.close()
            if count >= 3:
                flash('Você já cadastrou 3 produtos!', 'error')
                return redirect(url_for('dashboard'))

        product_name = request.form['nome']
        quantity = request.form['qtde']
        price = request.form['preco']

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute('INSERT INTO produtos (nome, loginUser, qtde, preco) VALUES (%s, %s, %s, %s)',
                        (product_name, session['username'], quantity, price))
            conn.commit()
            flash('Produto cadastrado com sucesso!')
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash('Erro ao cadastrar produto!', 'error')
        finally:
            cur.close()
            conn.close()

    return render_template('add_product.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        flash(f'Um e-mail de verificação foi enviado para {email}.', 'info')
        return redirect(url_for('login'))

    return render_template('reset_password.html')

if __name__ == '__main__':
    app.run(debug=True)
