from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection
import pandas as pd
import plotly.express as px

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
        if check_password_hash(user[1], password):
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
        flash('Por favor, faça login primeiro.', 'error')
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
        flash('Você precisa estar logado para acessar esta página.', 'error')
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

@app.route('/sell_product/<int:product_id>', methods=['GET', 'POST'])
def sell_product(product_id):
    if 'username' not in session:
        flash('Você precisa estar logado para acessar esta página.', 'error')
        return redirect(url_for('login'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT nome, qtde FROM produtos WHERE id = %s', (product_id,))
    product = cur.fetchone()
    if request.method == 'POST':
        buyer_name = request.form['buyer_name']
        buyer_contact = request.form['buyer_contact']
        quantity_sold = int(request.form['quantity'])
        if product and product[1] >= quantity_sold:
            new_quantity = product[1] - quantity_sold
            cur.execute('UPDATE produtos SET qtde = %s WHERE id = %s', (new_quantity, product_id))
            conn.commit()
            flash('Venda realizada com Sucesso')
            return redirect(url_for('dashboard'))
        else:
            flash('Quantidade insuficiente!', 'error')
    cur.close()
    conn.close()
    return render_template('sell_product.html', product=product)

@app.route('/remover_produto', methods=['GET', 'POST'])
def remover_produto():
    if request.method == 'POST':
        produto_id = request.form['produto_id']
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM produtos WHERE id = %s', (produto_id,))
        produto = cur.fetchone()
        if produto:
            cur.execute('DELETE FROM produtos WHERE id = %s', (produto_id,))
            conn.commit()
            flash('Produto removido com sucesso!', 'success')
        else:
            flash('Produto não encontrado ou erro ao acessar os dados.', 'error')
        cur.close()
        conn.close()
        return redirect(url_for('dashboard'))
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT * FROM produtos')
    produtos = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('remover_produto.html', produtos=produtos)

@app.route('/sales_report', methods=['GET', 'POST'])
def sales_report():
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT id, nome FROM produtos')
    products = cur.fetchall()
    if request.method == 'POST':
        product_id = request.form['product_id']
        cur.execute('SELECT data_venda, quantidade FROM vendas WHERE produto_id = %s', (product_id,))
        sales_data = cur.fetchall()
        dates = [sale[0] for sale in sales_data]
        quantities = [sale[1] for sale in sales_data]
        df = pd.DataFrame(sales_data, columns=['Data', 'Quantidade'])
        fig = px.line(df, x='Data', y='Quantidade', title='Relatório de Vendas')
        fig_html = fig.to_html(full_html=False)
        cur.close()
        conn.close()
        return render_template('sales_report.html', fig_html=fig_html, products=products)
    cur.close()
    conn.close()
    return render_template('sales_report.html', products=products)

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
