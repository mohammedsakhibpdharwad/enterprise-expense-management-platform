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
