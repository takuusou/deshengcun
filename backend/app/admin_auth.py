from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import ipaddress
import json
import logging
import os
import re
import secrets
import struct
import time
from typing import Any
from urllib.parse import quote

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from .db import DBIntegrityError, get_connection
from .secret_protection import protect_text, unprotect_text


ADMIN_SESSION_HOURS = max(int(os.getenv("ADMIN_SESSION_HOURS", "12") or "12"), 1)
ADMIN_MAX_FAILURES = max(int(os.getenv("ADMIN_MAX_FAILURES", "5") or "5"), 1)
ADMIN_LOCK_MINUTES = max(int(os.getenv("ADMIN_LOCK_MINUTES", "30") or "30"), 1)
ADMIN_IP_MAX_FAILURES = max(int(os.getenv("ADMIN_IP_MAX_FAILURES", "12") or "12"), 1)
ADMIN_IP_FAILURE_WINDOW_MINUTES = max(
    int(os.getenv("ADMIN_IP_FAILURE_WINDOW_MINUTES", "30") or "30"),
    1,
)
ADMIN_ROLE_KEYS = {"super_admin", "cadre", "readonly"}
ADMIN_MFA_REQUIRED = str(os.getenv("ADMIN_MFA_REQUIRED", "1" if os.getenv("APP_ENV") == "production" else "0") or "0").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
ADMIN_MFA_ISSUER = str(os.getenv("ADMIN_MFA_ISSUER", "得胜服务通后台") or "得胜服务通后台").strip()[:60]
ADMIN_PASSWORD_HASHER = PasswordHasher()
ADMIN_LOGIN_IP_RATE_LIMIT_SCOPE = "admin_login_ip"
DEFAULT_BOOTSTRAP_ADMIN_LOGIN_NAME = str(
    os.getenv("DEFAULT_CADRE_MANAGER_LOGIN_NAME", "admin") or "admin"
).strip().lower() or "admin"
security_logger = logging.getLogger("deshengcun.security")


def _admin_trusted_proxy_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    configured = str(
        os.getenv(
            "ADMIN_TRUSTED_PROXY_CIDRS",
            "127.0.0.0/8,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16",
        )
        or ""
    )
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for raw_network in configured.split(","):
        try:
            networks.append(ipaddress.ip_network(raw_network.strip(), strict=False))
        except ValueError:
            continue
    return networks


def resolve_client_ip(*, peer_ip: str, forwarded_for: str = "", real_ip: str = "") -> str:
    peer_text = str(peer_ip or "").strip()
    try:
        peer_address = ipaddress.ip_address(peer_text)
    except ValueError:
        return "unknown"
    if not any(peer_address in network for network in _admin_trusted_proxy_networks()):
        return str(peer_address)

    forwarded_addresses: list[ipaddress.IPv4Address | ipaddress.IPv6Address] = []
    for raw_address in str(forwarded_for or "").split(",")[-20:]:
        try:
            forwarded_addresses.append(ipaddress.ip_address(raw_address.strip()))
        except ValueError:
            continue
    if not forwarded_addresses and str(real_ip or "").strip():
        try:
            forwarded_addresses.append(ipaddress.ip_address(str(real_ip).strip()))
        except ValueError:
            pass
    trusted_networks = _admin_trusted_proxy_networks()
    for address in reversed(forwarded_addresses):
        if not any(address in network for network in trusted_networks):
            return str(address)
    return str(forwarded_addresses[0] if forwarded_addresses else peer_address)


def is_admin_ip_allowed(ip: str) -> bool:
    configured = str(os.getenv("ADMIN_ALLOWED_IP_CIDRS", "") or "").strip()
    if not configured:
        return True
    try:
        address = ipaddress.ip_address(str(ip or "").strip())
    except ValueError:
        return False
    for raw_network in configured.split(","):
        network_text = raw_network.strip()
        if not network_text:
            continue
        try:
            network = ipaddress.ip_network(network_text, strict=False)
        except ValueError:
            continue
        if address in network:
            return True
    return False


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _json_text(value: dict[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _hash_token(token: str) -> str:
    return hashlib.sha256(str(token or "").encode("utf-8")).hexdigest()


def _normalize_admin_login_ip(ip: str) -> str:
    text = str(ip or "").strip().lower()
    return text[:64] or "unknown"


def _parse_iso_datetime(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _normalize_role_key(role_key: str, fallback_role_level: str = "cadre") -> str:
    text = str(role_key or "").strip().lower()
    if text in ADMIN_ROLE_KEYS:
        return text
    fallback = str(fallback_role_level or "").strip().lower()
    if fallback == "super_admin":
        return "super_admin"
    return "cadre"


def _admin_user_to_dict(row: Any) -> dict[str, Any]:
    item = dict(row)
    return {
        "id": int(item.get("id") or 0),
        "login_name": str(item.get("login_name") or ""),
        "display_name": str(item.get("display_name") or ""),
        "real_name": str(item.get("real_name") or ""),
        "office_title": str(item.get("office_title") or ""),
        "role_key": _normalize_role_key(item.get("role_key") or "", item.get("cadre_role_level") or ""),
        "status": str(item.get("status") or "inactive"),
        "password_reset_required": bool(item.get("password_reset_required") or 0),
        "mfa_enabled": bool(item.get("mfa_enabled") or 0),
        "mfa_setup_required": bool(ADMIN_MFA_REQUIRED and not item.get("mfa_enabled")),
        "cadre_authorization_id": int(item.get("cadre_authorization_id") or 0),
        "cadre_role_level": str(item.get("cadre_role_level") or "none"),
        "can_export_full_id": False,
        "last_login_at": str(item.get("last_login_at") or ""),
    }


def _audit_admin_log_conn(
    conn: Any,
    *,
    actor_admin_user_id: int | None,
    action: str,
    target_type: str,
    target_id: str,
    detail: dict[str, Any],
    ip: str = "",
    user_agent: str = "",
) -> None:
    conn.execute(
        """
        INSERT INTO audit_logs(
            actor_user_id, actor_admin_user_id, actor_type,
            action, target_type, target_id, detail_json, ip, user_agent, created_at
        )
        VALUES(?, ?, 'admin', ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            None,
            actor_admin_user_id,
            action,
            target_type,
            target_id,
            _json_text(detail),
            str(ip or "")[:64],
            str(user_agent or "")[:255],
            now_iso(),
        ),
    )


def _load_admin_user_by_login_conn(conn: Any, login_name: str) -> Any | None:
    return conn.execute(
        """
        SELECT
            a.id,
            a.login_name,
            a.display_name,
            a.real_name,
            a.cadre_authorization_id,
            a.role_key,
            a.password_hash,
            a.password_algorithm,
            a.status,
            a.password_reset_required,
            a.mfa_secret_encrypted,
            a.mfa_enabled,
            a.mfa_enrolled_at,
            a.mfa_recovery_codes_hashes,
            a.mfa_last_counter,
            a.failed_login_count,
            a.locked_until,
            a.last_login_at,
            a.last_login_ip,
            a.last_login_user_agent,
            a.password_changed_at,
            c.office_title,
            c.role_level AS cadre_role_level,
            c.can_export_full_id,
            c.status AS cadre_authorization_status
        FROM admin_users a
        JOIN cadre_authorizations c ON c.id = a.cadre_authorization_id
        WHERE a.login_name = ?
        LIMIT 1
        """,
        (str(login_name or "").strip(),),
    ).fetchone()


def _load_admin_user_by_id_conn(conn: Any, admin_user_id: int) -> Any | None:
    return conn.execute(
        """
        SELECT
            a.id,
            a.login_name,
            a.display_name,
            a.real_name,
            a.cadre_authorization_id,
            a.role_key,
            a.password_hash,
            a.password_algorithm,
            a.status,
            a.password_reset_required,
            a.mfa_secret_encrypted,
            a.mfa_enabled,
            a.mfa_enrolled_at,
            a.mfa_recovery_codes_hashes,
            a.mfa_last_counter,
            a.failed_login_count,
            a.locked_until,
            a.last_login_at,
            a.last_login_ip,
            a.last_login_user_agent,
            a.password_changed_at,
            c.office_title,
            c.role_level AS cadre_role_level,
            c.can_export_full_id,
            c.status AS cadre_authorization_status
        FROM admin_users a
        JOIN cadre_authorizations c ON c.id = a.cadre_authorization_id
        WHERE a.id = ?
        LIMIT 1
        """,
        (admin_user_id,),
    ).fetchone()


def _load_admin_user_by_token_conn(conn: Any, token: str) -> tuple[Any, Any]:
    token_text = str(token or "").strip()
    if not token_text:
        raise ValueError("login_required")
    token_hash = _hash_token(token_text)
    session_row = conn.execute(
        """
        SELECT id, admin_user_id, token_hash, expires_at, revoked_at
        FROM admin_sessions
        WHERE token_hash IN (?, ?) AND revoked_at = ''
        ORDER BY CASE WHEN token_hash = ? THEN 0 ELSE 1 END ASC
        LIMIT 1
        """,
        (token_hash, token_text, token_hash),
    ).fetchone()
    if session_row is None:
        raise ValueError("invalid_admin_token")
    expires_at = _parse_iso_datetime(str(session_row["expires_at"] or ""))
    if expires_at is None or expires_at <= datetime.now(timezone.utc):
        conn.execute(
            "UPDATE admin_sessions SET revoked_at = ? WHERE id = ?",
            (now_iso(), session_row["id"]),
        )
        raise ValueError("admin_token_expired")
    if str(session_row["token_hash"] or "") != token_hash:
        conn.execute(
            "UPDATE admin_sessions SET token_hash = ?, last_seen_at = ? WHERE id = ?",
            (token_hash, now_iso(), session_row["id"]),
        )
    else:
        conn.execute(
            "UPDATE admin_sessions SET last_seen_at = ? WHERE id = ?",
            (now_iso(), session_row["id"]),
        )
    user_row = _load_admin_user_by_id_conn(conn, int(session_row["admin_user_id"] or 0))
    if user_row is None:
        raise ValueError("invalid_admin_token")
    if str(user_row["status"] or "").strip() != "active":
        raise ValueError("admin_account_disabled")
    if str(user_row["cadre_authorization_status"] or "").strip() != "active":
        raise ValueError("admin_authorization_disabled")
    return user_row, session_row


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bool(ADMIN_PASSWORD_HASHER.verify(password_hash, password))
    except (VerifyMismatchError, InvalidHashError):
        return False


def _hash_password(password: str) -> str:
    return ADMIN_PASSWORD_HASHER.hash(password)


def _validate_new_password(password: str) -> None:
    text = str(password or "").strip()
    character_classes = sum(
        bool(pattern.search(text))
        for pattern in (
            re.compile(r"[a-z]"),
            re.compile(r"[A-Z]"),
            re.compile(r"\d"),
            re.compile(r"[^A-Za-z0-9]"),
        )
    )
    if len(text) < 12 or character_classes < 2 or text.lower() in {"password123!", "admin123456!"}:
        raise ValueError("weak_admin_password")


def _admin_login_ip_window_start(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc)
    return current.replace(second=0, microsecond=0).isoformat()


def _purge_expired_admin_login_ip_failures_conn(conn: Any, *, now: datetime | None = None) -> None:
    current = now or datetime.now(timezone.utc)
    cutoff = (current - timedelta(minutes=ADMIN_IP_FAILURE_WINDOW_MINUTES * 2)).isoformat()
    conn.execute(
        """
        DELETE FROM request_rate_limits
        WHERE scope = ? AND updated_at < ?
        """,
        (ADMIN_LOGIN_IP_RATE_LIMIT_SCOPE, cutoff),
    )


def _recent_admin_login_ip_failures_conn(conn: Any, ip: str, *, now: datetime | None = None) -> int:
    current = now or datetime.now(timezone.utc)
    cutoff = (current - timedelta(minutes=ADMIN_IP_FAILURE_WINDOW_MINUTES)).isoformat()
    row = conn.execute(
        """
        SELECT COALESCE(SUM(request_count), 0) AS total
        FROM request_rate_limits
        WHERE scope = ? AND bucket_key = ? AND updated_at >= ?
        """,
        (ADMIN_LOGIN_IP_RATE_LIMIT_SCOPE, _normalize_admin_login_ip(ip), cutoff),
    ).fetchone()
    return int((dict(row) if row is not None else {}).get("total") or 0)


def _record_admin_login_ip_failure_conn(conn: Any, ip: str, *, now: datetime | None = None) -> int:
    current = now or datetime.now(timezone.utc)
    bucket_key = _normalize_admin_login_ip(ip)
    window_start = _admin_login_ip_window_start(current)
    now_text = current.isoformat()
    existing = conn.execute(
        """
        SELECT id, request_count
        FROM request_rate_limits
        WHERE scope = ? AND bucket_key = ? AND window_start = ?
        LIMIT 1
        """,
        (ADMIN_LOGIN_IP_RATE_LIMIT_SCOPE, bucket_key, window_start),
    ).fetchone()
    if existing is None:
        conn.execute(
            """
            INSERT INTO request_rate_limits(
                scope, bucket_key, window_start, request_count, created_at, updated_at
            )
            VALUES(?, ?, ?, 1, ?, ?)
            """,
            (ADMIN_LOGIN_IP_RATE_LIMIT_SCOPE, bucket_key, window_start, now_text, now_text),
        )
    else:
        conn.execute(
            """
            UPDATE request_rate_limits
            SET request_count = ?, updated_at = ?
            WHERE id = ?
            """,
            (int(existing["request_count"] or 0) + 1, now_text, existing["id"]),
        )
    _purge_expired_admin_login_ip_failures_conn(conn, now=current)
    return _recent_admin_login_ip_failures_conn(conn, bucket_key, now=current)


def _clear_admin_login_ip_failures_conn(conn: Any, ip: str) -> None:
    conn.execute(
        """
        DELETE FROM request_rate_limits
        WHERE scope = ? AND bucket_key = ?
        """,
        (ADMIN_LOGIN_IP_RATE_LIMIT_SCOPE, _normalize_admin_login_ip(ip)),
    )


def _normalize_mfa_code(code: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", str(code or "")).upper()


def _totp_value(secret_base32: str, counter: int) -> str:
    try:
        key = base64.b32decode(str(secret_base32 or "").upper(), casefold=True)
    except (ValueError, TypeError) as exc:
        raise ValueError("admin_mfa_invalid_secret") from exc
    digest = hmac.new(key, struct.pack(">Q", int(counter)), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(binary % 1_000_000).zfill(6)


def _totp_counter(at_time: float | None = None) -> int:
    return int((time.time() if at_time is None else at_time) // 30)


def _parse_recovery_code_hashes(raw: Any) -> list[str]:
    try:
        values = json.loads(str(raw or "[]"))
    except json.JSONDecodeError:
        return []
    if not isinstance(values, list):
        return []
    return [str(value or "").lower() for value in values if re.fullmatch(r"[0-9a-f]{64}", str(value or "").lower())]


def _verify_admin_mfa_conn(conn: Any, row: Any, code: str) -> str:
    normalized = _normalize_mfa_code(code)
    if not normalized:
        raise ValueError("admin_mfa_code_required")
    admin_user_id = int(row["id"] or 0)
    if normalized.isdigit() and len(normalized) == 6:
        protected_secret = str(row["mfa_secret_encrypted"] or "").strip()
        if not protected_secret:
            raise ValueError("admin_mfa_not_configured")
        secret = unprotect_text(protected_secret, purpose=f"admin_mfa:{admin_user_id}")
        current_counter = _totp_counter()
        last_counter = int(row["mfa_last_counter"] or 0)
        for counter in range(current_counter - 1, current_counter + 2):
            if counter <= last_counter:
                continue
            if hmac.compare_digest(_totp_value(secret, counter), normalized):
                conn.execute(
                    "UPDATE admin_users SET mfa_last_counter = ?, updated_at = ? WHERE id = ?",
                    (counter, now_iso(), admin_user_id),
                )
                return "totp"

    recovery_hash = _hash_token(normalized)
    recovery_hashes = _parse_recovery_code_hashes(row["mfa_recovery_codes_hashes"])
    if recovery_hash in recovery_hashes:
        recovery_hashes.remove(recovery_hash)
        conn.execute(
            "UPDATE admin_users SET mfa_recovery_codes_hashes = ?, updated_at = ? WHERE id = ?",
            (_json_text(recovery_hashes), now_iso(), admin_user_id),
        )
        return "recovery_code"
    raise ValueError("invalid_admin_mfa_code")


def _create_admin_session_conn(
    conn: Any,
    admin_user_id: int,
    *,
    ip: str = "",
    user_agent: str = "",
    session_type: str = "password+mfa",
) -> tuple[str, str]:
    token = secrets.token_urlsafe(32)
    token_hash = _hash_token(token)
    now = now_iso()
    expires_at = (datetime.now(timezone.utc) + timedelta(hours=ADMIN_SESSION_HOURS)).isoformat()
    conn.execute(
        """
        INSERT INTO admin_sessions(
            admin_user_id, token_hash, session_type, login_ip, login_user_agent,
            created_at, expires_at, last_seen_at, revoked_at
        )
        VALUES(?, ?, ?, ?, ?, ?, ?, ?, '')
        """,
        (
            admin_user_id,
            token_hash,
            str(session_type or "password")[:20],
            str(ip or "")[:64],
            str(user_agent or "")[:255],
            now,
            expires_at,
            now,
        ),
    )
    return token, expires_at


def login_admin(
    *,
    login_name: str,
    password: str,
    mfa_code: str = "",
    ip: str = "",
    user_agent: str = "",
) -> dict[str, Any]:
    conn = get_connection()
    try:
        normalized_ip = _normalize_admin_login_ip(ip)
        recent_ip_failures = _recent_admin_login_ip_failures_conn(conn, normalized_ip)
        if recent_ip_failures >= ADMIN_IP_MAX_FAILURES:
            security_logger.warning(
                "security_alert event=admin_login_ip_rate_limited ip=%s failures=%s",
                normalized_ip,
                recent_ip_failures,
            )
            _audit_admin_log_conn(
                conn,
                actor_admin_user_id=None,
                action="admin_login_ip_rate_limited",
                target_type="ip",
                target_id=normalized_ip,
                detail={
                    "login_name": str(login_name or "").strip(),
                    "ip_failures": recent_ip_failures,
                    "window_minutes": ADMIN_IP_FAILURE_WINDOW_MINUTES,
                    "max_failures": ADMIN_IP_MAX_FAILURES,
                },
                ip=normalized_ip,
                user_agent=user_agent,
            )
            conn.commit()
            raise ValueError("admin_ip_rate_limited")

        row = _load_admin_user_by_login_conn(conn, login_name)
        if row is None:
            ip_failures = _record_admin_login_ip_failure_conn(conn, normalized_ip)
            _audit_admin_log_conn(
                conn,
                actor_admin_user_id=None,
                action="admin_login_failed",
                target_type="admin_login",
                target_id=str(login_name or "").strip()[:80] or normalized_ip,
                detail={
                    "login_name": str(login_name or "").strip(),
                    "ip_failures": ip_failures,
                    "reason": "unknown_login_name",
                },
                ip=normalized_ip,
                user_agent=user_agent,
            )
            conn.commit()
            raise ValueError("invalid_admin_credentials")
        if str(row["status"] or "").strip() != "active":
            raise ValueError("admin_account_disabled")
        if str(row["cadre_authorization_status"] or "").strip() != "active":
            raise ValueError("admin_authorization_disabled")

        locked_until = _parse_iso_datetime(str(row["locked_until"] or ""))
        if locked_until is not None and locked_until > datetime.now(timezone.utc):
            _audit_admin_log_conn(
                conn,
                actor_admin_user_id=int(row["id"] or 0),
                action="admin_login_locked",
                target_type="admin_user",
                target_id=str(row["id"]),
                detail={"login_name": str(row["login_name"] or "")},
                ip=normalized_ip,
                user_agent=user_agent,
            )
            conn.commit()
            raise ValueError("admin_account_locked")

        if not _verify_password(password, str(row["password_hash"] or "")):
            ip_failures = _record_admin_login_ip_failure_conn(conn, normalized_ip)
            failed_count = int(row["failed_login_count"] or 0) + 1
            now = now_iso()
            locked_until_text = ""
            if failed_count >= ADMIN_MAX_FAILURES:
                locked_until_text = (
                    datetime.now(timezone.utc) + timedelta(minutes=ADMIN_LOCK_MINUTES)
                ).isoformat()
            conn.execute(
                """
                UPDATE admin_users
                SET failed_login_count = ?, locked_until = ?, updated_at = ?
                WHERE id = ?
                """,
                (failed_count, locked_until_text, now, row["id"]),
            )
            _audit_admin_log_conn(
                conn,
                actor_admin_user_id=int(row["id"] or 0),
                action="admin_login_failed",
                target_type="admin_user",
                target_id=str(row["id"]),
                detail={
                    "login_name": str(row["login_name"] or ""),
                    "failed_login_count": failed_count,
                    "ip_failures": ip_failures,
                },
                ip=normalized_ip,
                user_agent=user_agent,
            )
            conn.commit()
            if locked_until_text:
                security_logger.warning(
                    "security_alert event=admin_account_locked admin_user_id=%s ip=%s",
                    int(row["id"] or 0),
                    normalized_ip,
                )
                raise ValueError("admin_account_locked")
            raise ValueError("invalid_admin_credentials")

        mfa_enabled = bool(row["mfa_enabled"] or 0)
        mfa_method = ""
        if mfa_enabled:
            if not _normalize_mfa_code(mfa_code):
                _audit_admin_log_conn(
                    conn,
                    actor_admin_user_id=int(row["id"] or 0),
                    action="admin_mfa_challenge",
                    target_type="admin_user",
                    target_id=str(row["id"]),
                    detail={"login_name": str(row["login_name"] or "")},
                    ip=normalized_ip,
                    user_agent=user_agent,
                )
                conn.commit()
                raise ValueError("admin_mfa_code_required")
            try:
                mfa_method = _verify_admin_mfa_conn(conn, row, mfa_code)
            except ValueError as exc:
                if str(exc) != "admin_mfa_code_required":
                    failed_count = int(row["failed_login_count"] or 0) + 1
                    locked_until_text = ""
                    if failed_count >= ADMIN_MAX_FAILURES:
                        locked_until_text = (
                            datetime.now(timezone.utc) + timedelta(minutes=ADMIN_LOCK_MINUTES)
                        ).isoformat()
                    conn.execute(
                        """
                        UPDATE admin_users
                        SET failed_login_count = ?, locked_until = ?, updated_at = ?
                        WHERE id = ?
                        """,
                        (failed_count, locked_until_text, now_iso(), row["id"]),
                    )
                    _record_admin_login_ip_failure_conn(conn, normalized_ip)
                    security_logger.warning(
                        "security_alert event=admin_mfa_failed admin_user_id=%s ip=%s failures=%s",
                        int(row["id"] or 0),
                        normalized_ip,
                        failed_count,
                    )
                    _audit_admin_log_conn(
                        conn,
                        actor_admin_user_id=int(row["id"] or 0),
                        action="admin_mfa_failed",
                        target_type="admin_user",
                        target_id=str(row["id"]),
                        detail={"failed_login_count": failed_count},
                        ip=normalized_ip,
                        user_agent=user_agent,
                    )
                    conn.commit()
                    if locked_until_text:
                        raise ValueError("admin_account_locked") from exc
                raise

        now = now_iso()
        _clear_admin_login_ip_failures_conn(conn, normalized_ip)
        conn.execute(
            """
            UPDATE admin_users
            SET
                failed_login_count = 0,
                locked_until = '',
                last_login_at = ?,
                last_login_ip = ?,
                last_login_user_agent = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (now, normalized_ip, str(user_agent or "")[:255], now, row["id"]),
        )
        if bool(row["password_reset_required"] or 0):
            session_type = "password_change"
        elif ADMIN_MFA_REQUIRED and not mfa_enabled:
            session_type = "mfa_enrollment"
        elif mfa_enabled:
            session_type = "password+mfa"
        else:
            session_type = "password"
        token, expires_at = _create_admin_session_conn(
            conn,
            int(row["id"] or 0),
            ip=normalized_ip,
            user_agent=user_agent,
            session_type=session_type,
        )
        fresh = _load_admin_user_by_id_conn(conn, int(row["id"] or 0))
        _audit_admin_log_conn(
            conn,
            actor_admin_user_id=int(row["id"] or 0),
            action="admin_login",
            target_type="admin_user",
            target_id=str(row["id"]),
            detail={
                "login_name": str(row["login_name"] or ""),
                "session_type": session_type,
                "mfa_method": mfa_method,
            },
            ip=normalized_ip,
            user_agent=user_agent,
        )
        conn.commit()
        if mfa_method == "recovery_code":
            security_logger.warning(
                "security_alert event=admin_mfa_recovery_code_used admin_user_id=%s ip=%s",
                int(row["id"] or 0),
                normalized_ip,
            )
        return {
            "token": token,
            "expires_at": expires_at,
            "user": _admin_user_to_dict(fresh),
        }
    finally:
        conn.close()


def get_current_admin(token: str, *, allow_incomplete: bool = False) -> dict[str, Any]:
    conn = get_connection()
    try:
        user_row, _ = _load_admin_user_by_token_conn(conn, token)
        if not allow_incomplete:
            if bool(user_row["password_reset_required"] or 0):
                raise ValueError("admin_password_change_required")
            if ADMIN_MFA_REQUIRED and not bool(user_row["mfa_enabled"] or 0):
                raise ValueError("admin_mfa_setup_required")
        conn.commit()
        return _admin_user_to_dict(user_row)
    finally:
        conn.close()


def logout_admin(token: str, *, ip: str = "", user_agent: str = "") -> dict[str, str]:
    conn = get_connection()
    try:
        user_row, session_row = _load_admin_user_by_token_conn(conn, token)
        conn.execute(
            "UPDATE admin_sessions SET revoked_at = ? WHERE id = ?",
            (now_iso(), session_row["id"]),
        )
        _audit_admin_log_conn(
            conn,
            actor_admin_user_id=int(user_row["id"] or 0),
            action="admin_logout",
            target_type="admin_session",
            target_id=str(session_row["id"]),
            detail={},
            ip=ip,
            user_agent=user_agent,
        )
        conn.commit()
        return {"status": "ok", "message": "已退出后台登录"}
    finally:
        conn.close()


def change_admin_password(
    token: str,
    *,
    current_password: str,
    new_password: str,
    ip: str = "",
    user_agent: str = "",
) -> dict[str, str]:
    _validate_new_password(new_password)
    conn = get_connection()
    try:
        user_row, session_row = _load_admin_user_by_token_conn(conn, token)
        if not _verify_password(current_password, str(user_row["password_hash"] or "")):
            raise ValueError("invalid_admin_credentials")
        now = now_iso()
        conn.execute(
            """
            UPDATE admin_users
            SET
                password_hash = ?,
                password_algorithm = 'argon2id',
                password_reset_required = 0,
                failed_login_count = 0,
                locked_until = '',
                password_changed_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (_hash_password(new_password), now, now, user_row["id"]),
        )
        conn.execute(
            """
            UPDATE admin_sessions
            SET revoked_at = ?
            WHERE admin_user_id = ? AND id <> ? AND revoked_at = ''
            """,
            (now, user_row["id"], session_row["id"]),
        )
        next_session_type = (
            "password+mfa"
            if bool(user_row["mfa_enabled"] or 0)
            else ("mfa_enrollment" if ADMIN_MFA_REQUIRED else "password")
        )
        conn.execute(
            "UPDATE admin_sessions SET session_type = ? WHERE id = ?",
            (next_session_type, session_row["id"]),
        )
        _audit_admin_log_conn(
            conn,
            actor_admin_user_id=int(user_row["id"] or 0),
            action="admin_change_password",
            target_type="admin_user",
            target_id=str(user_row["id"]),
            detail={},
            ip=ip,
            user_agent=user_agent,
        )
        conn.commit()
        return {"status": "ok", "message": "后台密码已更新"}
    finally:
        conn.close()


def begin_admin_mfa_setup(
    token: str,
    *,
    ip: str = "",
    user_agent: str = "",
) -> dict[str, str]:
    conn = get_connection()
    try:
        user_row, _ = _load_admin_user_by_token_conn(conn, token)
        if bool(user_row["password_reset_required"] or 0):
            raise ValueError("admin_password_change_required")
        if bool(user_row["mfa_enabled"] or 0):
            raise ValueError("admin_mfa_already_configured")
        admin_user_id = int(user_row["id"] or 0)
        secret = base64.b32encode(secrets.token_bytes(20)).decode("ascii").rstrip("=")
        protected_secret = protect_text(secret, purpose=f"admin_mfa:{admin_user_id}")
        now = now_iso()
        conn.execute(
            """
            UPDATE admin_users
            SET mfa_secret_encrypted = ?, mfa_enabled = 0, mfa_enrolled_at = '',
                mfa_recovery_codes_hashes = '[]', mfa_last_counter = 0, updated_at = ?
            WHERE id = ?
            """,
            (protected_secret, now, admin_user_id),
        )
        _audit_admin_log_conn(
            conn,
            actor_admin_user_id=admin_user_id,
            action="admin_mfa_setup_begin",
            target_type="admin_user",
            target_id=str(admin_user_id),
            detail={},
            ip=ip,
            user_agent=user_agent,
        )
        conn.commit()
        account_label = str(user_row["login_name"] or admin_user_id)
        issuer = ADMIN_MFA_ISSUER or "得胜服务通后台"
        otpauth_uri = (
            f"otpauth://totp/{quote(issuer)}:{quote(account_label)}"
            f"?secret={secret}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"
        )
        return {
            "secret": secret,
            "otpauth_uri": otpauth_uri,
            "account_label": account_label,
            "issuer": issuer,
        }
    finally:
        conn.close()


def confirm_admin_mfa_setup(
    token: str,
    *,
    code: str,
    ip: str = "",
    user_agent: str = "",
) -> dict[str, Any]:
    normalized_code = _normalize_mfa_code(code)
    if not normalized_code.isdigit() or len(normalized_code) != 6:
        raise ValueError("invalid_admin_mfa_code")
    conn = get_connection()
    try:
        user_row, session_row = _load_admin_user_by_token_conn(conn, token)
        if bool(user_row["password_reset_required"] or 0):
            raise ValueError("admin_password_change_required")
        admin_user_id = int(user_row["id"] or 0)
        protected_secret = str(user_row["mfa_secret_encrypted"] or "").strip()
        if not protected_secret:
            raise ValueError("admin_mfa_setup_not_started")
        secret = unprotect_text(protected_secret, purpose=f"admin_mfa:{admin_user_id}")
        matched_counter = 0
        current_counter = _totp_counter()
        for counter in range(current_counter - 1, current_counter + 2):
            if hmac.compare_digest(_totp_value(secret, counter), normalized_code):
                matched_counter = counter
                break
        if not matched_counter:
            raise ValueError("invalid_admin_mfa_code")

        recovery_codes: list[str] = []
        recovery_hashes: list[str] = []
        for _ in range(8):
            raw_code = base64.b32encode(secrets.token_bytes(10)).decode("ascii").rstrip("=")
            display_code = f"{raw_code[:4]}-{raw_code[4:8]}-{raw_code[8:12]}-{raw_code[12:16]}"
            recovery_codes.append(display_code)
            recovery_hashes.append(_hash_token(_normalize_mfa_code(display_code)))
        now = now_iso()
        conn.execute(
            """
            UPDATE admin_users
            SET mfa_enabled = 1, mfa_enrolled_at = ?, mfa_recovery_codes_hashes = ?,
                mfa_last_counter = ?, updated_at = ?
            WHERE id = ?
            """,
            (now, json.dumps(recovery_hashes, separators=(",", ":")), matched_counter, now, admin_user_id),
        )
        conn.execute(
            "UPDATE admin_sessions SET session_type = 'password+mfa' WHERE id = ?",
            (session_row["id"],),
        )
        conn.execute(
            """
            UPDATE admin_sessions SET revoked_at = ?
            WHERE admin_user_id = ? AND id <> ? AND revoked_at = ''
            """,
            (now, admin_user_id, session_row["id"]),
        )
        _audit_admin_log_conn(
            conn,
            actor_admin_user_id=admin_user_id,
            action="admin_mfa_enabled",
            target_type="admin_user",
            target_id=str(admin_user_id),
            detail={"recovery_code_count": len(recovery_codes)},
            ip=ip,
            user_agent=user_agent,
        )
        fresh = _load_admin_user_by_id_conn(conn, admin_user_id)
        conn.commit()
        return {
            "status": "ok",
            "message": "双因素认证已启用",
            "recovery_codes": recovery_codes,
            "user": _admin_user_to_dict(fresh),
        }
    finally:
        conn.close()


def bootstrap_admin_user(
    *,
    login_name: str,
    password: str,
    authorization_id: int = 0,
    real_name: str = "",
    display_name: str = "",
    role_key: str = "",
    force_reset: bool = False,
) -> dict[str, Any]:
    _validate_new_password(password)
    login_name = str(login_name or "").strip().lower()
    if not login_name:
        raise ValueError("invalid_admin_login_name")

    conn = get_connection()
    try:
        auth_row = None
        if int(authorization_id or 0) > 0:
            auth_row = conn.execute(
                "SELECT * FROM cadre_authorizations WHERE id = ? LIMIT 1",
                (int(authorization_id),),
            ).fetchone()
        elif str(real_name or "").strip():
            auth_row = conn.execute(
                "SELECT * FROM cadre_authorizations WHERE real_name = ? LIMIT 1",
                (str(real_name or "").strip(),),
            ).fetchone()
        if auth_row is None:
            raise ValueError("cadre_authorization_not_found")

        resolved_role_key = _normalize_role_key(role_key, str(auth_row["role_level"] or "cadre"))
        now = now_iso()
        existing_by_auth = conn.execute(
            "SELECT id FROM admin_users WHERE cadre_authorization_id = ? LIMIT 1",
            (int(auth_row["id"] or 0),),
        ).fetchone()
        existing_by_login = conn.execute(
            "SELECT id, cadre_authorization_id FROM admin_users WHERE login_name = ? LIMIT 1",
            (login_name,),
        ).fetchone()
        if existing_by_login is not None and (
            existing_by_auth is None or int(existing_by_login["id"] or 0) != int(existing_by_auth["id"] or 0)
        ):
            raise ValueError("admin_login_name_conflict")

        resolved_display_name = str(display_name or "").strip() or str(auth_row["real_name"] or "").strip()
        resolved_real_name = str(auth_row["real_name"] or "").strip()
        password_hash = _hash_password(password)

        if existing_by_auth is None:
            cursor = conn.execute(
                """
                INSERT INTO admin_users(
                    login_name, display_name, real_name, cadre_authorization_id, role_key,
                    password_hash, password_algorithm, status, password_reset_required,
                    security_policy_version, password_changed_at, created_at, updated_at
                )
                VALUES(?, ?, ?, ?, ?, ?, 'argon2id', 'active', ?, 1, ?, ?, ?)
                """,
                (
                    login_name,
                    resolved_display_name,
                    resolved_real_name,
                    int(auth_row["id"] or 0),
                    resolved_role_key,
                    password_hash,
                    1 if force_reset else 0,
                    now,
                    now,
                    now,
                ),
            )
            admin_user_id = int(cursor.lastrowid or 0)
        else:
            admin_user_id = int(existing_by_auth["id"] or 0)
            conn.execute(
                """
                UPDATE admin_users
                SET
                    login_name = ?,
                    display_name = ?,
                    real_name = ?,
                    role_key = ?,
                    password_hash = ?,
                    password_algorithm = 'argon2id',
                    status = 'active',
                    password_reset_required = ?,
                    security_policy_version = 1,
                    mfa_secret_encrypted = '',
                    mfa_enabled = 0,
                    mfa_enrolled_at = '',
                    mfa_recovery_codes_hashes = '[]',
                    mfa_last_counter = 0,
                    failed_login_count = 0,
                    locked_until = '',
                    password_changed_at = ?,
                    updated_at = ?
                WHERE id = ?
                """,
                (
                    login_name,
                    resolved_display_name,
                    resolved_real_name,
                    resolved_role_key,
                    password_hash,
                    1 if force_reset else 0,
                    now,
                    now,
                    admin_user_id,
                ),
            )
        row = _load_admin_user_by_id_conn(conn, admin_user_id)
        conn.commit()
        if row is None:
            raise ValueError("admin_account_init_failed")
        return _admin_user_to_dict(row)
    except DBIntegrityError as exc:
        raise ValueError("admin_account_init_failed") from exc
    finally:
        conn.close()


def ensure_default_bootstrap_admin_user() -> dict[str, Any]:
    login_name = DEFAULT_BOOTSTRAP_ADMIN_LOGIN_NAME
    password = str(os.getenv("DEFAULT_CADRE_MANAGER_PASSWORD", "") or "").strip()
    real_name = str(os.getenv("DEFAULT_CADRE_MANAGER_NAME", "") or "").strip()
    if not login_name or not password or not real_name:
        return {"status": "skipped_missing_config", "login_name": login_name, "real_name": real_name}

    conn = get_connection()
    try:
        auth_row = conn.execute(
            """
            SELECT id
            FROM cadre_authorizations
            WHERE real_name = ?
            LIMIT 1
            """,
            (real_name,),
        ).fetchone()
        if auth_row is None:
            return {"status": "skipped_authorization_missing", "login_name": login_name, "real_name": real_name}

        authorization_id = int(auth_row["id"] or 0)
        existing_by_auth = conn.execute(
            "SELECT id, login_name FROM admin_users WHERE cadre_authorization_id = ? LIMIT 1",
            (authorization_id,),
        ).fetchone()
        if existing_by_auth is not None:
            return {
                "status": "exists",
                "authorization_id": authorization_id,
                "login_name": str(existing_by_auth["login_name"] or ""),
            }

        existing_by_login = conn.execute(
            "SELECT id, cadre_authorization_id FROM admin_users WHERE login_name = ? LIMIT 1",
            (login_name,),
        ).fetchone()
        if existing_by_login is not None:
            return {
                "status": "login_name_conflict",
                "login_name": login_name,
                "authorization_id": int(existing_by_login["cadre_authorization_id"] or 0),
            }
    finally:
        conn.close()

    user = bootstrap_admin_user(
        login_name=login_name,
        password=password,
        real_name=real_name,
        display_name=real_name,
        role_key="super_admin",
        force_reset=False,
    )
    return {"status": "created", **user}


def reset_admin_account_password(
    *,
    authorization_id: int,
    new_password: str,
    force_reset: bool = True,
) -> dict[str, Any]:
    _validate_new_password(new_password)
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT id FROM admin_users WHERE cadre_authorization_id = ? LIMIT 1",
            (int(authorization_id or 0),),
        ).fetchone()
        if row is None:
            raise ValueError("admin_account_not_found")
        admin_user_id = int(row["id"] or 0)
        now = now_iso()
        conn.execute(
            """
            UPDATE admin_users
            SET
                password_hash = ?,
                password_algorithm = 'argon2id',
                password_reset_required = ?,
                mfa_secret_encrypted = '',
                mfa_enabled = 0,
                mfa_enrolled_at = '',
                mfa_recovery_codes_hashes = '[]',
                mfa_last_counter = 0,
                failed_login_count = 0,
                locked_until = '',
                password_changed_at = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                _hash_password(new_password),
                1 if force_reset else 0,
                now,
                now,
                admin_user_id,
            ),
        )
        conn.execute(
            """
            UPDATE admin_sessions
            SET revoked_at = ?
            WHERE admin_user_id = ? AND revoked_at = ''
            """,
            (now, admin_user_id),
        )
        fresh = _load_admin_user_by_id_conn(conn, admin_user_id)
        conn.commit()
        if fresh is None:
            raise ValueError("admin_account_not_found")
        return _admin_user_to_dict(fresh)
    finally:
        conn.close()
