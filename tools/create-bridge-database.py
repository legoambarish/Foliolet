"""Create only the isolated demo database. Existing wallet_dev is untouched."""
import psycopg
with psycopg.connect('host=127.0.0.1 port=55433 user=foliolet dbname=postgres', autocommit=True) as connection:
    if not connection.execute('SELECT 1 FROM pg_database WHERE datname = %s', ('foliolet_bridge',)).fetchone():
        connection.execute('CREATE DATABASE foliolet_bridge')
print('Isolated foliolet_bridge database ready')
