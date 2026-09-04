"""Create the MySQL database if it does not already exist."""

import os
import sys

import pymysql
from dotenv import load_dotenv

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

load_dotenv(os.path.join(ROOT, ".env"))

from config import Config


def main():
    try:
        connection = pymysql.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            port=int(Config.MYSQL_PORT),
            charset="utf8mb4",
        )
    except pymysql.Error as exc:
        print("Could not connect to MySQL. Check host, user, and password in .env")
        print(exc)
        sys.exit(1)

    db_name = Config.MYSQL_DATABASE
    with connection.cursor() as cursor:
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
    connection.close()
    print(f"Database '{db_name}' is ready. Tables are created when you start the app.")


if __name__ == "__main__":
    main()
