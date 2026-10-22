from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import pymysql

from migrate_sqlite_to_mysql import TABLES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify row counts after SQLite -> MySQL migration.")
    parser.add_argument("--sqlite", required=True, help="SQLite database file path")
    parser.add_argument("--mysql-url", required=True, help="MySQL URL")
    return parser.parse_args()


def parse_mysql_url(mysql_url: str) -> dict[str, object]:
    parsed = urlparse(mysql_url)
    query = parse_qs(parsed.query or "")
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": int(parsed.port or 3306),
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": str(parsed.path or "").lstrip("/"),
        "charset": str((query.get("charset") or ["utf8mb4"])[0] or "utf8mb4"),
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
    }


def count_sqlite(conn: sqlite3.Connection, table_name: str) -> int:
    return int(conn.execute(f"SELECT COUNT(1) FROM {table_name}").fetchone()[0])


def count_mysql(conn: pymysql.Connection, table_name: str) -> int:
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT COUNT(1) AS cnt FROM `{table_name}`")
        row = cursor.fetchone()
    return int(row["cnt"] or 0)


def main() -> None:
    args = parse_args()
    sqlite_path = Path(args.sqlite).expanduser().resolve()
    sqlite_conn = sqlite3.connect(sqlite_path)
    mysql_conn = pymysql.connect(**parse_mysql_url(args.mysql_url))
    failed = False
    try:
        for table_name in TABLES:
            sqlite_count = count_sqlite(sqlite_conn, table_name)
            mysql_count = count_mysql(mysql_conn, table_name)
            status = "ok" if sqlite_count == mysql_count else "mismatch"
            print(f"[{status}] {table_name}: sqlite={sqlite_count}, mysql={mysql_count}")
            if sqlite_count != mysql_count:
                failed = True
    finally:
        sqlite_conn.close()
        mysql_conn.close()
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
