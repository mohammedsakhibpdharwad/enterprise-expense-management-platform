from contextlib import contextmanager

import mysql.connector
from mysql.connector import Error

from config import Config


def get_db_connection():
    """Return a new MySQL connection using application config."""
    try:
        connection = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            port=Config.MYSQL_PORT,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DATABASE,
        )
        return connection
    except Error as exc:
        raise RuntimeError(f"Database connection failed: {exc}") from exc


@contextmanager
def db_session(dictionary=True, commit=True):
    connection = get_db_connection()
    cursor = connection.cursor(dictionary=dictionary)
    try:
        yield connection, cursor
        if commit:
            connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


def fetch_all(sql, params=None):
    with db_session(commit=False) as (_conn, cursor):
        cursor.execute(sql, params or ())
        return cursor.fetchall()


def fetch_one(sql, params=None):
    with db_session(commit=False) as (_conn, cursor):
        cursor.execute(sql, params or ())
        return cursor.fetchone()


def execute(sql, params=None):
    with db_session(commit=True) as (_conn, cursor):
        cursor.execute(sql, params or ())
        return cursor.lastrowid, cursor.rowcount
