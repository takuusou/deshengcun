from __future__ import annotations

import hashlib
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qs, unquote, urlparse

try:
    import pymysql
    from pymysql.cursors import DictCursor
    from pymysql.err import IntegrityError as MySQLIntegrityError
except ImportError:  # pragma: no cover - optional dependency in local sqlite mode
    pymysql = None
    DictCursor = None
    MySQLIntegrityError = sqlite3.IntegrityError

from .runtime_config import (
    get_backend_db_path,
    get_database_backend,
    get_database_url,
)


BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = get_backend_db_path()
DATA_DIR = DB_PATH.parent
MYSQL_SCHEMA_PATH = BASE_DIR / "sql" / "mysql_schema.sql"
DB_BACKEND = get_database_backend()
DBIntegrityError = (sqlite3.IntegrityError, MySQLIntegrityError)
logger = logging.getLogger(__name__)


class QueryResult:
    def __init__(self, cursor: Any) -> None:
        self._cursor = cursor
        self.lastrowid = getattr(cursor, "lastrowid", 0)

    def fetchone(self) -> Any:
        return self._cursor.fetchone()

    def fetchall(self) -> list[Any]:
        return list(self._cursor.fetchall() or [])


class MySQLConnectionAdapter:
    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def _adapt_query(self, query: str) -> str:
        return str(query or "").replace("?", "%s")

    def execute(self, query: str, params: Iterable[Any] | None = None) -> QueryResult:
        cursor = self._connection.cursor()
        cursor.execute(self._adapt_query(query), tuple(params or ()))
        return QueryResult(cursor)

    def executemany(self, query: str, seq_of_params: Iterable[Iterable[Any]]) -> QueryResult:
        cursor = self._connection.cursor()
        cursor.executemany(self._adapt_query(query), [tuple(item) for item in seq_of_params])
        return QueryResult(cursor)

    def commit(self) -> None:
        self._connection.commit()

    def rollback(self) -> None:
        self._connection.rollback()

    def close(self) -> None:
        self._connection.close()


def _parse_mysql_database_url(database_url: str) -> dict[str, Any]:
    parsed = urlparse(database_url)
    if parsed.scheme not in {"mysql", "mysql+pymysql"}:
        raise RuntimeError("当前 DATABASE_URL 不是 MySQL 连接串。")
    query = parse_qs(parsed.query or "")
    database_name = str(parsed.path or "").lstrip("/")
    if not database_name:
        raise RuntimeError("MySQL 连接串缺少数据库名。")
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": int(parsed.port or 3306),
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": database_name,
        "charset": str((query.get("charset") or ["utf8mb4"])[0] or "utf8mb4"),
    }


def get_connection() -> sqlite3.Connection | MySQLConnectionAdapter:
    if DB_BACKEND == "mysql":
        if pymysql is None:
            raise RuntimeError("MySQL 模式缺少 PyMySQL 依赖，请先安装 requirements.txt。")
        mysql_kwargs = {
            "cursorclass": DictCursor,
            "autocommit": False,
            "connect_timeout": 5,
            "read_timeout": 10,
            "write_timeout": 10,
            **_parse_mysql_database_url(get_database_url()),
        }
        last_error: Exception | None = None
        for attempt in range(1, 4):
            try:
                connection = pymysql.connect(**mysql_kwargs)
                return MySQLConnectionAdapter(connection)
            except Exception as exc:  # pragma: no cover - runtime connectivity branch
                last_error = exc
                if attempt >= 3:
                    break
                logger.warning(
                    "mysql_connect_retry: attempt=%s host=%s port=%s database=%s error=%s",
                    attempt,
                    mysql_kwargs.get("host", ""),
                    mysql_kwargs.get("port", 3306),
                    mysql_kwargs.get("database", ""),
                    exc,
                )
                time.sleep(1)
        assert last_error is not None
        raise last_error

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _table_columns(conn: sqlite3.Connection | MySQLConnectionAdapter, table_name: str) -> set[str]:
    if DB_BACKEND == "mysql":
        database_name = _parse_mysql_database_url(get_database_url())["database"]
        rows = conn.execute(
            """
            SELECT COLUMN_NAME AS column_name
            FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
            """,
            (database_name, table_name),
        ).fetchall()
        return {str(row["column_name"] or "") for row in rows}
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def _table_indexes(conn: sqlite3.Connection | MySQLConnectionAdapter, table_name: str) -> set[str]:
    if DB_BACKEND == "mysql":
        database_name = _parse_mysql_database_url(get_database_url())["database"]
        rows = conn.execute(
            """
            SELECT INDEX_NAME AS index_name
            FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = ? AND TABLE_NAME = ?
            """,
            (database_name, table_name),
        ).fetchall()
        return {str(row["index_name"] or "") for row in rows}
    rows = conn.execute(f"PRAGMA index_list({table_name})").fetchall()
    return {str(row["name"] or "") for row in rows}


def _ensure_index(conn: sqlite3.Connection | MySQLConnectionAdapter, table_name: str, index_name: str, ddl: str) -> None:
    if index_name in _table_indexes(conn, table_name):
        return
    conn.execute(ddl)


def _ensure_columns(
    conn: sqlite3.Connection | MySQLConnectionAdapter,
    table_name: str,
    column_defs: Iterable[tuple[str, str]],
) -> None:
    existing = _table_columns(conn, table_name)
    for column_name, column_def in column_defs:
        if column_name in existing:
            continue
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_def}")


def _looks_like_sha256_hex(text: str) -> bool:
    value = str(text or "").strip().lower()
    return len(value) == 64 and all(ch in "<CONFIGURE_CONTACT_PHONE>abcdef" for ch in value)


def _hash_session_token(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def _load_mysql_schema_statements() -> list[str]:
    text = MYSQL_SCHEMA_PATH.read_text(encoding="utf-8")
    statements: list[str] = []
    current: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        current.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(current).rstrip().rstrip(";"))
            current = []
    if current:
        statements.append("\n".join(current).rstrip().rstrip(";"))
    return [statement for statement in statements if statement.strip()]


def _init_mysql_db() -> None:
    conn = get_connection()
    try:
        for statement in _load_mysql_schema_statements():
            conn.execute(statement)
        conn.commit()
    finally:
        conn.close()


def _init_sqlite_db() -> None:
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.executescript(
            """
            CREATE TABLE IF NOT EXISTS notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                publisher TEXT NOT NULL,
                photo_urls TEXT NOT NULL DEFAULT '[]',
                is_home_top INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS notice_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                openid TEXT NOT NULL DEFAULT '',
                template_id TEXT NOT NULL DEFAULT '',
                subscription_status TEXT NOT NULL DEFAULT 'unknown',
                is_enabled INTEGER NOT NULL DEFAULT 0,
                last_request_scene TEXT NOT NULL DEFAULT '',
                last_request_result_json TEXT NOT NULL DEFAULT '{}',
                last_error_code TEXT NOT NULL DEFAULT '',
                last_error_message TEXT NOT NULL DEFAULT '',
                last_requested_at TEXT NOT NULL DEFAULT '',
                last_subscribed_at TEXT NOT NULL DEFAULT '',
                last_unsubscribed_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS notice_delivery_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                notice_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                openid TEXT NOT NULL DEFAULT '',
                template_id TEXT NOT NULL DEFAULT '',
                delivery_status TEXT NOT NULL DEFAULT 'pending',
                errcode INTEGER NOT NULL DEFAULT 0,
                errmsg TEXT NOT NULL DEFAULT '',
                response_json TEXT NOT NULL DEFAULT '{}',
                sent_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(notice_id, user_id, template_id),
                FOREIGN KEY(notice_id) REFERENCES notices(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS meetings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic TEXT NOT NULL,
                summary TEXT NOT NULL,
                owner TEXT NOT NULL,
                meeting_time TEXT NOT NULL,
                photo_urls TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS volunteer_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                detail TEXT NOT NULL,
                event_time TEXT NOT NULL,
                quota INTEGER NOT NULL,
                created_by TEXT NOT NULL,
                photo_urls TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS volunteer_signups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id INTEGER NOT NULL,
                participant_openid TEXT NOT NULL,
                participant_name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(event_id, participant_openid),
                FOREIGN KEY(event_id) REFERENCES volunteer_events(id)
            );

            CREATE TABLE IF NOT EXISTS training_programs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                schedule_text TEXT NOT NULL DEFAULT '',
                location TEXT NOT NULL DEFAULT '',
                target TEXT NOT NULL DEFAULT '',
                signup_deadline TEXT NOT NULL DEFAULT '',
                end_date TEXT NOT NULL DEFAULT '',
                contact_phone TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS training_signups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                program_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                phone_ciphertext TEXT NOT NULL DEFAULT '',
                phone_hash TEXT NOT NULL DEFAULT '',
                phone_masked TEXT NOT NULL DEFAULT '',
                openid TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(program_id, phone),
                FOREIGN KEY(program_id) REFERENCES training_programs(id)
            );

            CREATE TABLE IF NOT EXISTS volunteer_activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                schedule_text TEXT NOT NULL DEFAULT '',
                location TEXT NOT NULL DEFAULT '',
                target TEXT NOT NULL DEFAULT '',
                detail TEXT NOT NULL DEFAULT '',
                signup_deadline TEXT NOT NULL DEFAULT '',
                end_date TEXT NOT NULL DEFAULT '',
                contact_phone TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'open',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS volunteer_activity_signups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                phone_ciphertext TEXT NOT NULL DEFAULT '',
                phone_hash TEXT NOT NULL DEFAULT '',
                phone_masked TEXT NOT NULL DEFAULT '',
                openid TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(activity_id, phone),
                FOREIGN KEY(activity_id) REFERENCES volunteer_activities(id)
            );

            CREATE TABLE IF NOT EXISTS proposals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                user_openid TEXT NOT NULL DEFAULT '',
                villager_name TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS local_product (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                subtitle TEXT NOT NULL DEFAULT '',
                cover_url TEXT NOT NULL DEFAULT '',
                detail_img_url TEXT NOT NULL DEFAULT '',
                history TEXT NOT NULL DEFAULT '',
                craft TEXT NOT NULL DEFAULT '',
                flavor TEXT NOT NULL DEFAULT '',
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS ledgers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT NOT NULL,
                owner TEXT NOT NULL,
                photo_urls TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                openid TEXT NOT NULL UNIQUE,
                unionid TEXT NOT NULL DEFAULT '',
                nickname TEXT NOT NULL DEFAULT '',
                avatar_url TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                phone_ciphertext TEXT NOT NULL DEFAULT '',
                phone_hash TEXT NOT NULL DEFAULT '',
                phone_masked TEXT NOT NULL DEFAULT '',
                phone_last4 TEXT NOT NULL DEFAULT '',
                phone_bound INTEGER NOT NULL DEFAULT 0,
                phone_verified_at TEXT NOT NULL DEFAULT '',
                real_name TEXT NOT NULL DEFAULT '',
                gender TEXT NOT NULL DEFAULT '',
                id_card_masked TEXT NOT NULL DEFAULT '',
                id_card_last4 TEXT NOT NULL DEFAULT '',
                id_card_hash TEXT NOT NULL DEFAULT '',
                id_card_encrypted TEXT NOT NULL DEFAULT '',
                face_photo_url TEXT NOT NULL DEFAULT '',
                face_verified_at TEXT NOT NULL DEFAULT '',
                role TEXT NOT NULL DEFAULT 'villager',
                role_request TEXT NOT NULL DEFAULT 'villager',
                realname_status TEXT NOT NULL DEFAULT 'unsubmitted',
                face_status TEXT NOT NULL DEFAULT 'unsubmitted',
                auth_status TEXT NOT NULL DEFAULT 'unverified',
                roster_match_status TEXT NOT NULL DEFAULT 'unmatched',
                village_group TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS auth_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS cadre_managers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manager_name TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS cadre_authorizations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                real_name TEXT NOT NULL UNIQUE,
                office_title TEXT NOT NULL DEFAULT '',
                user_id INTEGER UNIQUE,
                openid TEXT UNIQUE,
                unionid TEXT UNIQUE,
                role_level TEXT NOT NULL DEFAULT 'cadre',
                can_export_full_id INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'active',
                last_bound_at TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS admin_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login_name TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                real_name TEXT NOT NULL,
                cadre_authorization_id INTEGER NOT NULL UNIQUE,
                role_key TEXT NOT NULL DEFAULT 'cadre',
                password_hash TEXT NOT NULL,
                password_algorithm TEXT NOT NULL DEFAULT 'argon2id',
                status TEXT NOT NULL DEFAULT 'active',
                password_reset_required INTEGER NOT NULL DEFAULT 0,
                security_policy_version INTEGER NOT NULL DEFAULT 1,
                mfa_secret_encrypted TEXT NOT NULL DEFAULT '',
                mfa_enabled INTEGER NOT NULL DEFAULT 0,
                mfa_enrolled_at TEXT NOT NULL DEFAULT '',
                mfa_recovery_codes_hashes TEXT NOT NULL DEFAULT '[]',
                mfa_last_counter INTEGER NOT NULL DEFAULT 0,
                failed_login_count INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT NOT NULL DEFAULT '',
                last_login_at TEXT NOT NULL DEFAULT '',
                last_login_ip TEXT NOT NULL DEFAULT '',
                last_login_user_agent TEXT NOT NULL DEFAULT '',
                password_changed_at TEXT NOT NULL DEFAULT '',
                created_by_admin_user_id INTEGER,
                updated_by_admin_user_id INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(cadre_authorization_id) REFERENCES cadre_authorizations(id),
                FOREIGN KEY(created_by_admin_user_id) REFERENCES admin_users(id),
                FOREIGN KEY(updated_by_admin_user_id) REFERENCES admin_users(id)
            );

            CREATE TABLE IF NOT EXISTS admin_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                admin_user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                session_type TEXT NOT NULL DEFAULT 'password',
                login_ip TEXT NOT NULL DEFAULT '',
                login_user_agent TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                revoked_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(admin_user_id) REFERENCES admin_users(id)
            );

            CREATE TABLE IF NOT EXISTS cadre_stepup_secrets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                password_algorithm TEXT NOT NULL DEFAULT 'argon2id',
                failed_count INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS cadre_stepup_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                last_used_at TEXT NOT NULL,
                revoked_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS roster_import_batches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                imported_by TEXT NOT NULL,
                imported_count INTEGER NOT NULL,
                skipped_count INTEGER NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS villager_roster (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                full_name TEXT NOT NULL,
                id_last4 TEXT NOT NULL,
                id_hash TEXT NOT NULL DEFAULT '',
                group_name TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                FOREIGN KEY(batch_id) REFERENCES roster_import_batches(id)
            );

            CREATE TABLE IF NOT EXISTS privacy_consents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                policy_version TEXT NOT NULL,
                consent_type TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                withdrawn_at TEXT NOT NULL DEFAULT '',
                UNIQUE(user_id, policy_version, consent_type),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                actor_user_id INTEGER,
                actor_admin_user_id INTEGER,
                actor_type TEXT NOT NULL DEFAULT 'villager',
                action TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_id TEXT NOT NULL DEFAULT '',
                detail_json TEXT NOT NULL DEFAULT '',
                ip TEXT NOT NULL DEFAULT '',
                user_agent TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                FOREIGN KEY(actor_user_id) REFERENCES users(id),
                FOREIGN KEY(actor_admin_user_id) REFERENCES admin_users(id)
            );

            CREATE TABLE IF NOT EXISTS village_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                metric_key TEXT NOT NULL UNIQUE,
                metric_label TEXT NOT NULL,
                metric_value TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                updated_by TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS open_profile (
                id INTEGER PRIMARY KEY,
                village_intro TEXT NOT NULL DEFAULT '',
                village_photo_url TEXT NOT NULL DEFAULT '',
                updated_by TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS open_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                section_key TEXT NOT NULL,
                title TEXT NOT NULL,
                summary TEXT NOT NULL DEFAULT '',
                fields_json TEXT NOT NULL DEFAULT '[]',
                content TEXT NOT NULL DEFAULT '',
                photo_urls TEXT NOT NULL DEFAULT '[]',
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS villager_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                request_type TEXT NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                contact_phone TEXT NOT NULL DEFAULT '',
                contact_phone_ciphertext TEXT NOT NULL DEFAULT '',
                contact_phone_hash TEXT NOT NULL DEFAULT '',
                contact_phone_masked TEXT NOT NULL DEFAULT '',
                reporter_name TEXT NOT NULL DEFAULT '',
                reporter_real_name TEXT NOT NULL DEFAULT '',
                reporter_id_card_hash TEXT NOT NULL DEFAULT '',
                photo_urls TEXT NOT NULL DEFAULT '[]',
                reply_photo_urls TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'pending',
                reply_text TEXT NOT NULL DEFAULT '',
                handled_by TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                handled_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS request_rate_limits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scope TEXT NOT NULL,
                bucket_key TEXT NOT NULL,
                window_start TEXT NOT NULL,
                request_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(scope, bucket_key, window_start)
            );

            CREATE TABLE IF NOT EXISTS gov_services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_key TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                subtitle TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'government',
                icon_emoji TEXT NOT NULL DEFAULT '',
                theme_color TEXT NOT NULL DEFAULT '',
                contact_name TEXT NOT NULL DEFAULT '',
                contact_phone TEXT NOT NULL DEFAULT '',
                intro TEXT NOT NULL DEFAULT '',
                action_label TEXT NOT NULL DEFAULT '',
                detail_type TEXT NOT NULL DEFAULT 'info_apply',
                detail_payload TEXT NOT NULL DEFAULT '{}',
                is_enabled INTEGER NOT NULL DEFAULT 1,
                sort_order INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS gov_service_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                service_key TEXT NOT NULL,
                service_title TEXT NOT NULL,
                applicant_name TEXT NOT NULL,
                applicant_phone TEXT NOT NULL DEFAULT '',
                applicant_phone_ciphertext TEXT NOT NULL DEFAULT '',
                applicant_phone_hash TEXT NOT NULL DEFAULT '',
                applicant_phone_masked TEXT NOT NULL DEFAULT '',
                selected_option TEXT NOT NULL DEFAULT '',
                note TEXT NOT NULL DEFAULT '',
                extra_fields TEXT NOT NULL DEFAULT '{}',
                sensitive_extra_fields_encrypted TEXT NOT NULL DEFAULT '',
                applicant_id_card_hash TEXT NOT NULL DEFAULT '',
                application_fingerprint_hash TEXT NOT NULL DEFAULT '',
                reply_photo_urls TEXT NOT NULL DEFAULT '[]',
                status TEXT NOT NULL DEFAULT 'pending',
                cadre_reply TEXT NOT NULL DEFAULT '',
                handled_by TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                handled_at TEXT NOT NULL DEFAULT '',
                FOREIGN KEY(service_id) REFERENCES gov_services(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS villager_registry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL UNIQUE,
                village_name TEXT NOT NULL DEFAULT '得胜村',
                group_name TEXT NOT NULL DEFAULT '',
                real_name TEXT NOT NULL DEFAULT '',
                gender TEXT NOT NULL DEFAULT '',
                phone TEXT NOT NULL DEFAULT '',
                phone_ciphertext TEXT NOT NULL DEFAULT '',
                phone_hash TEXT NOT NULL DEFAULT '',
                phone_masked TEXT NOT NULL DEFAULT '',
                phone_last4 TEXT NOT NULL DEFAULT '',
                id_card_masked TEXT NOT NULL DEFAULT '',
                id_card_last4 TEXT NOT NULL DEFAULT '',
                id_card_hash TEXT NOT NULL DEFAULT '',
                id_card_encrypted TEXT NOT NULL DEFAULT '',
                face_photo_url TEXT NOT NULL DEFAULT '',
                realname_submitted_at TEXT NOT NULL DEFAULT '',
                face_verified_at TEXT NOT NULL DEFAULT '',
                auth_status TEXT NOT NULL DEFAULT 'unverified',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS stored_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scene TEXT NOT NULL,
                filename TEXT NOT NULL,
                storage_provider TEXT NOT NULL DEFAULT 'local',
                bucket_name TEXT NOT NULL DEFAULT '',
                object_key TEXT NOT NULL DEFAULT '',
                content_type TEXT NOT NULL DEFAULT '',
                size_bytes INTEGER NOT NULL DEFAULT 0,
                sha256_hex TEXT NOT NULL DEFAULT '',
                uploaded_by_user_id INTEGER,
                is_private INTEGER NOT NULL DEFAULT 1,
                source_path TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'active',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(scene, filename),
                FOREIGN KEY(uploaded_by_user_id) REFERENCES users(id)
            );
            """
        )
        _ensure_columns(
            conn,
            "users",
            (
                ("unionid", "unionid TEXT NOT NULL DEFAULT ''"),
                ("phone_ciphertext", "phone_ciphertext TEXT NOT NULL DEFAULT ''"),
                ("phone_hash", "phone_hash TEXT NOT NULL DEFAULT ''"),
                ("phone_masked", "phone_masked TEXT NOT NULL DEFAULT ''"),
                ("phone_last4", "phone_last4 TEXT NOT NULL DEFAULT ''"),
                ("phone_verified_at", "phone_verified_at TEXT NOT NULL DEFAULT ''"),
                ("gender", "gender TEXT NOT NULL DEFAULT ''"),
                ("id_card_last4", "id_card_last4 TEXT NOT NULL DEFAULT ''"),
                ("id_card_encrypted", "id_card_encrypted TEXT NOT NULL DEFAULT ''"),
                ("face_photo_url", "face_photo_url TEXT NOT NULL DEFAULT ''"),
                ("face_verified_at", "face_verified_at TEXT NOT NULL DEFAULT ''"),
                ("roster_match_status", "roster_match_status TEXT NOT NULL DEFAULT 'unmatched'"),
                ("village_group", "village_group TEXT NOT NULL DEFAULT ''"),
            ),
        )
        _ensure_columns(
            conn,
            "villager_registry",
            (
                ("phone_ciphertext", "phone_ciphertext TEXT NOT NULL DEFAULT ''"),
                ("phone_hash", "phone_hash TEXT NOT NULL DEFAULT ''"),
                ("phone_masked", "phone_masked TEXT NOT NULL DEFAULT ''"),
                ("phone_last4", "phone_last4 TEXT NOT NULL DEFAULT ''"),
            ),
        )
        _ensure_columns(
            conn,
            "audit_logs",
            (
                ("actor_admin_user_id", "actor_admin_user_id INTEGER"),
                ("actor_type", "actor_type TEXT NOT NULL DEFAULT 'villager'"),
                ("ip", "ip TEXT NOT NULL DEFAULT ''"),
                ("user_agent", "user_agent TEXT NOT NULL DEFAULT ''"),
            ),
        )
        _ensure_columns(
            conn,
            "cadre_authorizations",
            (
                ("office_title", "office_title TEXT NOT NULL DEFAULT ''"),
            ),
        )
        cursor.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires_at
            ON auth_sessions(expires_at);

            CREATE INDEX IF NOT EXISTS idx_cadre_authorizations_status
            ON cadre_authorizations(status);

            CREATE INDEX IF NOT EXISTS idx_admin_users_login_name
            ON admin_users(login_name);

            CREATE INDEX IF NOT EXISTS idx_admin_users_status_role
            ON admin_users(status, role_key);

            CREATE INDEX IF NOT EXISTS idx_admin_sessions_user_expires
            ON admin_sessions(admin_user_id, expires_at);

            CREATE INDEX IF NOT EXISTS idx_admin_sessions_revoked
            ON admin_sessions(revoked_at);

            CREATE INDEX IF NOT EXISTS idx_cadre_stepup_sessions_expires_at
            ON cadre_stepup_sessions(expires_at);

            CREATE INDEX IF NOT EXISTS idx_request_rate_limits_scope_bucket_window
            ON request_rate_limits(scope, bucket_key, window_start);

            CREATE INDEX IF NOT EXISTS idx_notices_created_at
            ON notices(created_at);

            CREATE INDEX IF NOT EXISTS idx_notice_subscriptions_enabled
            ON notice_subscriptions(is_enabled, template_id, updated_at);

            CREATE INDEX IF NOT EXISTS idx_notice_delivery_logs_notice_user
            ON notice_delivery_logs(notice_id, user_id, template_id);

            CREATE INDEX IF NOT EXISTS idx_meetings_created_at
            ON meetings(created_at);

            CREATE INDEX IF NOT EXISTS idx_volunteer_events_created_at
            ON volunteer_events(created_at);

            CREATE INDEX IF NOT EXISTS idx_volunteer_signups_event_openid
            ON volunteer_signups(event_id, participant_openid);

            CREATE INDEX IF NOT EXISTS idx_training_programs_dates
            ON training_programs(status, signup_deadline, end_date);

            CREATE INDEX IF NOT EXISTS idx_training_signups_program_phone
            ON training_signups(program_id, phone);

            CREATE INDEX IF NOT EXISTS idx_volunteer_activities_dates
            ON volunteer_activities(status, signup_deadline, end_date);

            CREATE INDEX IF NOT EXISTS idx_volunteer_activity_signups_activity_phone
            ON volunteer_activity_signups(activity_id, phone);

            CREATE INDEX IF NOT EXISTS idx_proposals_created_at
            ON proposals(created_at);

            CREATE UNIQUE INDEX IF NOT EXISTS idx_training_signups_openid_program
            ON training_signups(openid, program_id);

            CREATE UNIQUE INDEX IF NOT EXISTS idx_volunteer_activity_signups_openid_activity
            ON volunteer_activity_signups(openid, activity_id);

            CREATE INDEX IF NOT EXISTS idx_local_product_sort
            ON local_product(sort_order, id);

            CREATE INDEX IF NOT EXISTS idx_users_id_card_hash
            ON users(id_card_hash);

            CREATE INDEX IF NOT EXISTS idx_villager_roster_match
            ON villager_roster(status, full_name, id_hash);

            CREATE INDEX IF NOT EXISTS idx_open_items_section_sort
            ON open_items(section_key, sort_order, id);

            CREATE INDEX IF NOT EXISTS idx_villager_requests_user_status_created
            ON villager_requests(user_id, status, created_at);

            CREATE INDEX IF NOT EXISTS idx_gov_service_apps_user_status_created
            ON gov_service_applications(user_id, status, created_at);

            CREATE INDEX IF NOT EXISTS idx_gov_service_apps_service_status_created
            ON gov_service_applications(service_id, status, created_at);

            CREATE INDEX IF NOT EXISTS idx_stored_files_scene_filename
            ON stored_files(scene, filename);

            CREATE INDEX IF NOT EXISTS idx_audit_logs_admin_action
            ON audit_logs(actor_admin_user_id, action, created_at);
            """
        )
        session_rows = cursor.execute(
            "SELECT id, token FROM auth_sessions WHERE token IS NOT NULL AND token != ''"
        ).fetchall()
        for row in session_rows:
            token = str(row["token"] or "")
            if _looks_like_sha256_hex(token):
                continue
            cursor.execute(
                "UPDATE auth_sessions SET token = ? WHERE id = ?",
                (_hash_session_token(token), row["id"]),
            )
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    if DB_BACKEND == "mysql":
        _init_mysql_db()
    else:
        _init_sqlite_db()

    conn = get_connection()
    try:
        if DB_BACKEND == "mysql":
            _ensure_columns(
                conn,
                "audit_logs",
                (
                    ("actor_admin_user_id", "actor_admin_user_id BIGINT NULL"),
                    ("actor_type", "actor_type VARCHAR(20) NOT NULL DEFAULT 'villager'"),
                    ("ip", "ip VARCHAR(64) NOT NULL DEFAULT ''"),
                    ("user_agent", "user_agent VARCHAR(255) NOT NULL DEFAULT ''"),
                ),
            )
            _ensure_index(
                conn,
                "users",
                "idx_users_id_card_hash",
                "CREATE INDEX idx_users_id_card_hash ON users(id_card_hash)",
            )
            _ensure_index(
                conn,
                "villager_roster",
                "idx_villager_roster_match",
                "CREATE INDEX idx_villager_roster_match ON villager_roster(status, full_name, id_hash)",
            )
            _ensure_columns(
                conn,
                "cadre_authorizations",
                (
                    ("office_title", "office_title VARCHAR(60) NOT NULL DEFAULT ''"),
                ),
            )
            _ensure_columns(
                conn,
                "admin_users",
                (
                    ("mfa_secret_encrypted", "mfa_secret_encrypted LONGTEXT NULL"),
                    ("security_policy_version", "security_policy_version INT NOT NULL DEFAULT 0"),
                    ("mfa_enabled", "mfa_enabled TINYINT(1) NOT NULL DEFAULT 0"),
                    ("mfa_enrolled_at", "mfa_enrolled_at VARCHAR(40) NOT NULL DEFAULT ''"),
                    ("mfa_recovery_codes_hashes", "mfa_recovery_codes_hashes LONGTEXT NULL"),
                    ("mfa_last_counter", "mfa_last_counter BIGINT NOT NULL DEFAULT 0"),
                ),
            )
            _ensure_columns(
                conn,
                "admin_sessions",
                (
                    ("session_type", "session_type VARCHAR(20) NOT NULL DEFAULT 'password'"),
                ),
            )
            _ensure_columns(
                conn,
                "villager_requests",
                (
                    ("reporter_real_name", "reporter_real_name VARCHAR(60) NOT NULL DEFAULT ''"),
                    ("reporter_id_card_hash", "reporter_id_card_hash CHAR(64) NOT NULL DEFAULT ''"),
                    ("contact_phone_ciphertext", "contact_phone_ciphertext LONGTEXT NULL"),
                    ("contact_phone_hash", "contact_phone_hash CHAR(64) NOT NULL DEFAULT ''"),
                    ("contact_phone_masked", "contact_phone_masked VARCHAR(32) NOT NULL DEFAULT ''"),
                ),
            )
            _ensure_columns(
                conn,
                "gov_service_applications",
                (
                    ("applicant_phone_ciphertext", "applicant_phone_ciphertext LONGTEXT NULL"),
                    ("applicant_phone_hash", "applicant_phone_hash CHAR(64) NOT NULL DEFAULT ''"),
                    ("applicant_phone_masked", "applicant_phone_masked VARCHAR(32) NOT NULL DEFAULT ''"),
                    ("sensitive_extra_fields_encrypted", "sensitive_extra_fields_encrypted LONGTEXT NULL"),
                    ("applicant_id_card_hash", "applicant_id_card_hash CHAR(64) NOT NULL DEFAULT ''"),
                    ("application_fingerprint_hash", "application_fingerprint_hash CHAR(64) NOT NULL DEFAULT ''"),
                ),
            )
            for signup_table in ("training_signups", "volunteer_activity_signups"):
                _ensure_columns(
                    conn,
                    signup_table,
                    (
                        ("phone_ciphertext", "phone_ciphertext LONGTEXT NULL"),
                        ("phone_hash", "phone_hash CHAR(64) NOT NULL DEFAULT ''"),
                        ("phone_masked", "phone_masked VARCHAR(32) NOT NULL DEFAULT ''"),
                    ),
                )
            _ensure_index(
                conn,
                "villager_requests",
                "idx_villager_requests_identity_created",
                "CREATE INDEX idx_villager_requests_identity_created ON villager_requests(reporter_id_card_hash, reporter_real_name, created_at)",
            )
        else:
            _ensure_columns(
                conn,
                "audit_logs",
                (
                    ("actor_admin_user_id", "actor_admin_user_id INTEGER"),
                    ("actor_type", "actor_type TEXT NOT NULL DEFAULT 'villager'"),
                    ("ip", "ip TEXT NOT NULL DEFAULT ''"),
                    ("user_agent", "user_agent TEXT NOT NULL DEFAULT ''"),
                ),
            )
            _ensure_columns(
                conn,
                "cadre_authorizations",
                (
                    ("office_title", "office_title TEXT NOT NULL DEFAULT ''"),
                ),
            )
            _ensure_columns(
                conn,
                "admin_users",
                (
                    ("mfa_secret_encrypted", "mfa_secret_encrypted TEXT NOT NULL DEFAULT ''"),
                    ("security_policy_version", "security_policy_version INTEGER NOT NULL DEFAULT 0"),
                    ("mfa_enabled", "mfa_enabled INTEGER NOT NULL DEFAULT 0"),
                    ("mfa_enrolled_at", "mfa_enrolled_at TEXT NOT NULL DEFAULT ''"),
                    ("mfa_recovery_codes_hashes", "mfa_recovery_codes_hashes TEXT NOT NULL DEFAULT '[]'"),
                    ("mfa_last_counter", "mfa_last_counter INTEGER NOT NULL DEFAULT 0"),
                ),
            )
            _ensure_columns(
                conn,
                "admin_sessions",
                (
                    ("session_type", "session_type TEXT NOT NULL DEFAULT 'password'"),
                ),
            )
            _ensure_columns(
                conn,
                "villager_requests",
                (
                    ("reporter_real_name", "reporter_real_name TEXT NOT NULL DEFAULT ''"),
                    ("reporter_id_card_hash", "reporter_id_card_hash TEXT NOT NULL DEFAULT ''"),
                    ("contact_phone_ciphertext", "contact_phone_ciphertext TEXT NOT NULL DEFAULT ''"),
                    ("contact_phone_hash", "contact_phone_hash TEXT NOT NULL DEFAULT ''"),
                    ("contact_phone_masked", "contact_phone_masked TEXT NOT NULL DEFAULT ''"),
                ),
            )
            _ensure_columns(
                conn,
                "gov_service_applications",
                (
                    ("applicant_phone_ciphertext", "applicant_phone_ciphertext TEXT NOT NULL DEFAULT ''"),
                    ("applicant_phone_hash", "applicant_phone_hash TEXT NOT NULL DEFAULT ''"),
                    ("applicant_phone_masked", "applicant_phone_masked TEXT NOT NULL DEFAULT ''"),
                    ("sensitive_extra_fields_encrypted", "sensitive_extra_fields_encrypted TEXT NOT NULL DEFAULT ''"),
                    ("applicant_id_card_hash", "applicant_id_card_hash TEXT NOT NULL DEFAULT ''"),
                    ("application_fingerprint_hash", "application_fingerprint_hash TEXT NOT NULL DEFAULT ''"),
                ),
            )
            for signup_table in ("training_signups", "volunteer_activity_signups"):
                _ensure_columns(
                    conn,
                    signup_table,
                    (
                        ("phone_ciphertext", "phone_ciphertext TEXT NOT NULL DEFAULT ''"),
                        ("phone_hash", "phone_hash TEXT NOT NULL DEFAULT ''"),
                        ("phone_masked", "phone_masked TEXT NOT NULL DEFAULT ''"),
                    ),
                )
            _ensure_index(
                conn,
                "villager_requests",
                "idx_villager_requests_identity_created",
                "CREATE INDEX idx_villager_requests_identity_created ON villager_requests(reporter_id_card_hash, reporter_real_name, created_at)",
            )
        conn.commit()
    finally:
        conn.close()
