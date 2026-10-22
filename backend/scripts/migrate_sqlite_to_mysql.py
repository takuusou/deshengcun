from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

import pymysql


TABLES = [
    "users",
    "auth_sessions",
    "cadre_managers",
    "cadre_authorizations",
    "cadre_stepup_secrets",
    "cadre_stepup_sessions",
    "privacy_consents",
    "audit_logs",
    "roster_import_batches",
    "villager_roster",
    "villager_registry",
    "request_rate_limits",
    "village_metrics",
    "open_items",
    "gov_services",
    "notices",
    "meetings",
    "volunteer_events",
    "volunteer_signups",
    "ledgers",
    "villager_requests",
    "gov_service_applications",
    "stored_files",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate deshengcun SQLite data to MySQL 8.0.")
    parser.add_argument("--sqlite", required=True, help="SQLite database file path")
    parser.add_argument("--mysql-url", required=True, help="MySQL URL, e.g. mysql+pymysql://user:pass@host:3306/db")
    parser.add_argument("--truncate", action="store_true", help="Truncate target tables before importing")
    return parser.parse_args()


def parse_mysql_url(mysql_url: str) -> dict[str, object]:
    parsed = urlparse(mysql_url)
    if parsed.scheme not in {"mysql", "mysql+pymysql"}:
        raise SystemExit("mysql-url must start with mysql:// or mysql+pymysql://")
    query = parse_qs(parsed.query or "")
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": int(parsed.port or 3306),
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": str(parsed.path or "").lstrip("/"),
        "charset": str((query.get("charset") or ["utf8mb4"])[0] or "utf8mb4"),
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": False,
    }


def fetch_table_rows(conn: sqlite3.Connection, table_name: str) -> list[dict[str, object]]:
    rows = conn.execute(f"SELECT * FROM {table_name}").fetchall()
    return [dict(row) for row in rows]


def import_table(mysql_conn: pymysql.Connection, table_name: str, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    columns = list(rows[0].keys())
    placeholders = ", ".join(["%s"] * len(columns))
    column_sql = ", ".join(f"`{column}`" for column in columns)
    sql = f"INSERT INTO `{table_name}` ({column_sql}) VALUES ({placeholders})"
    payload = [[row.get(column) for column in columns] for row in rows]
    with mysql_conn.cursor() as cursor:
        cursor.executemany(sql, payload)


def main() -> None:
    args = parse_args()
    sqlite_path = Path(args.sqlite).expanduser().resolve()
    if not sqlite_path.is_file():
        raise SystemExit(f"SQLite file not found: {sqlite_path}")

    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    mysql_conn = pymysql.connect(**parse_mysql_url(args.mysql_url))

    try:
        with mysql_conn.cursor() as cursor:
            if args.truncate:
                for table_name in reversed(TABLES):
                    cursor.execute(f"DELETE FROM `{table_name}`")
                mysql_conn.commit()

        for table_name in TABLES:
            rows = fetch_table_rows(sqlite_conn, table_name)
            import_table(mysql_conn, table_name, rows)
            mysql_conn.commit()
            print(f"[ok] imported {table_name}: {len(rows)} rows")
    finally:
        sqlite_conn.close()
        mysql_conn.close()


if __name__ == "__main__":
    main()
