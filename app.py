from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import get_db_connection
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

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
        loginUser = request.form['loginUser']
        email = request.form['email']
        senha = request.form['senha']

        tipo_usuario = request.form.get('tipo_usuario', 'normal')

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT * FROM usuarios WHERE loginUser = %s OR email = %s', (loginUser, email))
        user = cur.fetchone()

        if user:
            flash("Usuário ou e-mail já cadastrados", 'error')
            return redirect(url_for('register'))

        hashed_senha = generate_password_hash(senha, method='pbkdf2:sha256', salt_length=8)

        cur.execute(
            'INSERT INTO usuarios (loginUser, email, senha, tipouser) VALUES (%s, %s, %s, %s)',
            (loginUser, email, hashed_senha, tipo_usuario)

        )
        conn.commit()
        cur.close()
        conn.close()

        flash("Cadastro realizado com sucesso!", 'success')
        return redirect(url_for('login'))

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
           cur.execute('INSERT INTO produtos (nome, loginUser, qtde, preco) VALUES (%s, %s, %s, %s)', (product_name, session['username'], quantity, price))
           conn.commit()
           flash('Produto cadastrado com sucesso!')
           return redirect(url_for('dashboard'))
       except Exception as e:
           flash('Erro ao cadastrar produto!', 'error')
       finally:
           cur.close()
           conn.close()
   return render_template('add_product.html')


@app.route('/sell_product//<int:product_id>', methods=['GET', 'POST'])
def sell_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT id, nome, qtde, preco FROM produtos WHERE id = %s', (product_id,))
    produto = cursor.fetchone()

    if not produto:
        flash("Produto não encontrado.", "error")
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        buyer_name = request.form['buyer_name']
        buyer_contact = request.form['buyer_contact']
        quantity_sold = int(request.form['quantity_sold'])

        if quantity_sold > produto[2]:
            flash("Estoque insuficiente para essa quantidade.", "error")
            return render_template('sell_product.html', product=produto)

        new_quantity = produto[2] - quantity_sold
        cursor.execute('UPDATE produtos SET qtde = %s WHERE id = %s', (new_quantity, product_id))

        sale_date = datetime.now()
        cursor.execute(
            'INSERT INTO vendas (produto_id, data_venda, quantidade) VALUES (%s, %s, %s)',
            (product_id, sale_date, quantity_sold)
        )
        conn.commit()

        flash(f"Venda de {quantity_sold} unidade(s) do produto {produto[1]} realizada com sucesso!", "success")
        return redirect(url_for('dashboard'))

    return render_template('sell_product.html', product=produto)


@app.route('/sales_report', methods=['GET', 'POST'])
def sales_report():
    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute('SELECT id, nome FROM produtos')
    products = cur.fetchall()

    graph = None

    if request.method == 'POST':
        product_id = request.form['product_id']

        cur.execute('SELECT data_venda, quantidade FROM vendas WHERE produto_id = %s', (product_id,))
        sales_data = cur.fetchall()

        if not sales_data:
            flash("Nenhuma venda encontrada para o produto selecionado.")
        else:
            df = pd.DataFrame(sales_data, columns=['Data', 'Quantidade'])
            df['Data'] = pd.to_datetime(df['Data'], format='%Y-%m-%d')

            end_date = datetime.today()
            start_date = end_date - timedelta(days=6)

            df = df[(df['Data'] >= start_date) & (df['Data'] <= end_date)]

            if df.empty:
                flash("Nenhuma venda encontrada para os últimos 7 dias.")
            else:
                df = df.groupby('Data', as_index=False)['Quantidade'].sum()

                all_dates = pd.date_range(start=start_date, end=end_date, freq='D')
                df = df.set_index('Data').reindex(all_dates, fill_value=0).reset_index()
                df.columns = ['Data', 'Quantidade']

                fig = px.line(df, x='Data', y='Quantidade', title='Relatório de Vendas (Últimos 7 Dias)',
                              markers=True, line_shape='linear')

                fig.update_yaxes(range=[0, df['Quantidade'].max() + 5])
                fig.update_xaxes(
                    tickmode='array',
                    tickvals=df['Data'],
                    ticktext=df['Data'].dt.strftime('%d-%m-%Y')
                )

                graph = fig.to_html(full_html=False)

    return render_template('sales_report.html', products=products, graph=graph)

@app.route('/confirm_remove_product/<int:product_id>', methods=['GET', 'POST'])
def confirm_remove_product(product_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM produtos WHERE id = %s', (product_id,))
    product = cursor.fetchone()

    if product:
        if request.method == 'POST':
            cursor.execute('DELETE FROM vendas WHERE produto_id = %s', (product_id,))

            cursor.execute('DELETE FROM produtos WHERE id = %s', (product_id,))
            conn.commit()
            cursor.close()
            conn.close()
            flash('Produto removido com sucesso!', 'success')
            return redirect(url_for('dashboard'))

        cursor.close()
        conn.close()
        return render_template('remove_product.html', product=product)

    cursor.close()
    conn.close()
    flash('Produto não encontrado.', 'error')
    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
   session.clear()
   return redirect(url_for('login'))

@app.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    if request.method == 'POST':
        email = request.form['email']
        session['reset_email'] = email
        flash(f'Um e-mail de verificação foi enviado para {email}.', 'info')
        return redirect(url_for('new_password'))
    return render_template('reset_password.html')


@app.route('/new_password', methods=['GET', 'POST'])
def new_password():
    if request.method == 'POST':
        username = request.form['username']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if len(new_password) < 8:
            flash('A senha deve ter pelo menos 8 caracteres.', 'error')
            return redirect(url_for('new_password'))

        if new_password != confirm_password:
            flash('As senhas não coincidem!', 'error')
            return redirect(url_for('new_password'))

        hashed_password = generate_password_hash(new_password)

        conn = get_db_connection()
        cur = conn.cursor()
        try:
            cur.execute('UPDATE usuarios SET senha = %s WHERE email = %s AND nome_usuario = %s',
                        (hashed_password, session.get('reset_email'), username))

            if cur.rowcount == 0:
                flash('Usuário ou e-mail inválido.', 'error')
                return redirect(url_for('new_password'))

            conn.commit()
            session.pop('reset_email', None)
            flash('Senha redefinida com sucesso. Faça login com sua nova senha.', 'success')
            return redirect(url_for('login.html'))
        except Exception as e:
            flash('Erro ao redefinir senha.', 'error')
        finally:
            cur.close()
            conn.close()

    return render_template('new_password.html')

if __name__ == '__main__':
   app.run(debug=True)
