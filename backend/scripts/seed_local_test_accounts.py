"""Prepare stable local test accounts for Deshengcun v1.1.0.

This script is local-development only. It creates or updates:
- one verified villager identity for the mini program mock login
- one active admin account for the web console
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parent.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app import services
from app.admin_auth import bootstrap_admin_user
from app.db import get_connection, init_db

TEST_VILLAGER_NAME = os.getenv("LOCAL_TEST_VILLAGER_NAME", "王五").strip() or "王五"
TEST_VILLAGER_PHONE = os.getenv("LOCAL_TEST_VILLAGER_PHONE", "10000138888").strip() or "10000138888"
TEST_VILLAGER_ID_BODY17 = (
    os.getenv("LOCAL_TEST_VILLAGER_ID_BODY17", "00000019900101123").strip()
    or "00000019900101123"
)
TEST_VILLAGE_GROUP = os.getenv("LOCAL_TEST_VILLAGE_GROUP", "第一村民小组").strip() or "第一村民小组"
TEST_OPENID = (
    os.getenv("MOCK_WECHAT_OPENID", "mock_deshengcun_v110_local_villager").strip()
    or "mock_deshengcun_v110_local_villager"
)

ADMIN_LOGIN = os.getenv("DEFAULT_CADRE_MANAGER_LOGIN_NAME", "admin").strip().lower() or "admin"
ADMIN_NAME = os.getenv("DEFAULT_CADRE_MANAGER_NAME", "示例人员1").strip() or "示例人员1"
ADMIN_PASSWORD = (
    os.getenv("DEFAULT_CADRE_MANAGER_PASSWORD", "").strip()
)


def _check_digit(body17: str) -> str:
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    codes = "10X98765432"
    total = sum(int(body17[index]) * weights[index] for index in range(17))
    return codes[total % 11]


def _test_id_card() -> str:
    id_card = TEST_VILLAGER_ID_BODY17 + _check_digit(TEST_VILLAGER_ID_BODY17)
    if not services.is_valid_id_card(id_card):
        raise SystemExit(f"本地测试身份证号生成失败: {id_card}")
    return id_card


def _ensure_roster(conn, id_card: str) -> None:
    id_hash = services._id_hash(id_card)
    id_last4 = ""
    now = services.now_iso()
    batch_row = conn.execute(
        "SELECT id FROM roster_import_batches WHERE filename = 'local_test_roster' LIMIT 1"
    ).fetchone()
    if batch_row is None:
        cursor = conn.execute(
            """
            INSERT INTO roster_import_batches(filename, imported_by, imported_count, skipped_count, created_at)
            VALUES('local_test_roster', 'run_local.sh', 1, 0, ?)
            """,
            (now,),
        )
        batch_id = int(cursor.lastrowid or 0)
    else:
        batch_id = int(batch_row["id"] or 0)

    roster_row = conn.execute(
        """
        SELECT id FROM villager_roster
        WHERE full_name = ? AND id_hash = ?
        LIMIT 1
        """,
        (TEST_VILLAGER_NAME, id_hash),
    ).fetchone()
    if roster_row is None:
        conn.execute(
            """
            INSERT INTO villager_roster(batch_id, full_name, id_last4, id_hash, group_name, status, created_at)
            VALUES(?, ?, ?, ?, ?, 'active', ?)
            """,
            (batch_id, TEST_VILLAGER_NAME, id_last4, id_hash, TEST_VILLAGE_GROUP, now),
        )
    else:
        conn.execute(
            """
            UPDATE villager_roster
            SET batch_id = ?, id_last4 = ?, group_name = ?, status = 'active'
            WHERE id = ?
            """,
            (batch_id, id_last4, TEST_VILLAGE_GROUP, int(roster_row["id"] or 0)),
        )


def _ensure_privacy_consents(conn, user_id: int) -> None:
    now = services.now_iso()
    for consent_type in ("privacy_policy", "sensitive_identity"):
        conn.execute(
            services._privacy_consent_upsert_sql(),
            (user_id, services.PRIVACY_POLICY_VERSION, consent_type, now, now),
        )


def _ensure_villager(conn, id_card: str) -> int:
    now = services.now_iso()
    phone_fields = services._phone_fields(TEST_VILLAGER_PHONE)
    gender = services._gender_from_id_card(id_card) or ""
    id_hash = services._id_hash(id_card)
    id_last4 = ""
    id_encrypted = services.encrypt_id_card_number(id_card)
    id_masked = services.mask_id_card(id_card)

    row = conn.execute("SELECT id FROM users WHERE openid = ? LIMIT 1", (TEST_OPENID,)).fetchone()
    if row is None:
        cursor = conn.execute(
            """
            INSERT INTO users(
                openid, unionid, nickname, avatar_url,
                phone, phone_ciphertext, phone_hash, phone_masked, phone_last4,
                phone_bound, phone_verified_at,
                real_name, gender, id_card_masked, id_card_last4, id_card_hash, id_card_encrypted,
                role, role_request, realname_status, face_status, auth_status, roster_match_status,
                village_group, created_at, updated_at
            )
            VALUES(
                ?, '', ?, '',
                ?, ?, ?, ?, ?,
                1, ?,
                ?, ?, ?, ?, ?, ?,
                'villager', 'villager', 'verified', 'unsubmitted', 'verified', 'matched',
                ?, ?, ?
            )
            """,
            (
                TEST_OPENID,
                TEST_VILLAGER_NAME,
                phone_fields["phone"],
                phone_fields["phone_ciphertext"],
                phone_fields["phone_hash"],
                phone_fields["phone_masked"],
                phone_fields["phone_last4"],
                now,
                TEST_VILLAGER_NAME,
                gender,
                id_masked,
                id_last4,
                id_hash,
                id_encrypted,
                TEST_VILLAGE_GROUP,
                now,
                now,
            ),
        )
        user_id = int(cursor.lastrowid or 0)
    else:
        user_id = int(row["id"] or 0)
        conn.execute(
            """
            UPDATE users
            SET
                nickname = ?,
                phone = ?,
                phone_ciphertext = ?,
                phone_hash = ?,
                phone_masked = ?,
                phone_last4 = ?,
                phone_bound = 1,
                phone_verified_at = ?,
                real_name = ?,
                gender = ?,
                id_card_masked = ?,
                id_card_last4 = ?,
                id_card_hash = ?,
                id_card_encrypted = ?,
                role = 'villager',
                role_request = 'villager',
                realname_status = 'verified',
                face_status = 'unsubmitted',
                auth_status = 'verified',
                roster_match_status = 'matched',
                village_group = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                TEST_VILLAGER_NAME,
                phone_fields["phone"],
                phone_fields["phone_ciphertext"],
                phone_fields["phone_hash"],
                phone_fields["phone_masked"],
                phone_fields["phone_last4"],
                now,
                TEST_VILLAGER_NAME,
                gender,
                id_masked,
                id_last4,
                id_hash,
                id_encrypted,
                TEST_VILLAGE_GROUP,
                now,
                user_id,
            ),
        )

    _ensure_privacy_consents(conn, user_id)
    services._sync_villager_registry_conn(conn, user_id)
    return user_id


def _ensure_admin() -> None:
    services.ensure_default_cadre_authorizations()
    conn = get_connection()
    try:
        auth_row = conn.execute(
            "SELECT id FROM cadre_authorizations WHERE real_name = ? LIMIT 1",
            (ADMIN_NAME,),
        ).fetchone()
        if auth_row is None:
            raise SystemExit(f"本地后台授权不存在: {ADMIN_NAME}")
        authorization_id = int(auth_row["id"] or 0)
        conflict_row = conn.execute(
            """
            SELECT id, cadre_authorization_id
            FROM admin_users
            WHERE login_name = ?
            LIMIT 1
            """,
            (ADMIN_LOGIN,),
        ).fetchone()
        if conflict_row is not None and int(conflict_row["cadre_authorization_id"] or 0) != authorization_id:
            now = services.now_iso()
            conflict_id = int(conflict_row["id"] or 0)
            conn.execute(
                """
                UPDATE admin_users
                SET login_name = ?, updated_at = ?
                WHERE id = ?
                """,
                (f"{ADMIN_LOGIN}_old_{conflict_id}", now, conflict_id),
            )
            conn.commit()
    finally:
        conn.close()

    bootstrap_admin_user(
        login_name=ADMIN_LOGIN,
        password=ADMIN_PASSWORD,
        real_name=ADMIN_NAME,
        display_name=ADMIN_NAME,
        role_key="super_admin",
        force_reset=False,
    )


def main() -> None:
    init_db()
    id_card = _test_id_card()
    conn = get_connection()
    try:
        _ensure_roster(conn, id_card)
        user_id = _ensure_villager(conn, id_card)
        conn.commit()
    finally:
        conn.close()
    _ensure_admin()

    print("本地测试账号已准备好:")
    print(f"  村民姓名   : {TEST_VILLAGER_NAME}")
    print(f"  村民身份证 : {id_card}")
    print(f"  村民手机号 : {TEST_VILLAGER_PHONE}")
    print(f"  Mock OpenID: {TEST_OPENID}")
    print(f"  村民 user_id: {user_id}")
    print(f"  后台账号   : {ADMIN_LOGIN}")
    print(f"  后台密码   : {ADMIN_PASSWORD}")


if __name__ == "__main__":
    main()
