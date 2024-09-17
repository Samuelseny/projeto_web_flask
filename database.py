import psycopg2

def get_db_connection():
    conn = psycopg2.connect(
        dbname='projeto_web',
        user='postgres',
        password='mingaudoce',
        host='localhost',
        port='5432'
    )
    return conn

try:
    conn = get_db_connection()
    print("Conexão ao banco de dados estabelecida com sucesso!")
    conn.close()
except Exception as e:
    print(f"Erro ao conectar ao banco de dados: {e}")
