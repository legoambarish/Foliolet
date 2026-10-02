"""Create only this project's development database; no existing database is modified."""
import psycopg

with psycopg.connect("host=127.0.0.1 port=55432 user=wallet dbname=postgres", autocommit=True) as connection:
    if not connection.execute("SELECT 1 FROM pg_database WHERE datname = %s", ("wallet_dev",)).fetchone():
        connection.execute("CREATE DATABASE wallet_dev")
print("wallet_dev database is ready")
