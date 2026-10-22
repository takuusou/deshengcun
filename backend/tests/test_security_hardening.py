from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app import admin_auth, db, secret_protection, services
from scripts import migrate_sensitive_business_data
from scripts import secure_database_backup


TEST_KEY_HEX = "42" * 32
TEST_PHONE_KEY_HEX = "43" * 32
TEST_BACKUP_KEY_HEX = "73" * 32
TEST_LOOKUP_HMAC_KEY_HEX = "84" * 32


class SecurityHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.original_db_path = db.DB_PATH
        self.original_data_dir = db.DATA_DIR
        self.original_db_backend = db.DB_BACKEND
        db.DB_PATH = Path(self.temp_dir.name) / "security.db"
        db.DATA_DIR = db.DB_PATH.parent
        db.DB_BACKEND = "sqlite"
        self.environment = patch.dict(
            os.environ,
            {
                "APP_ENV": "development",
                "ID_CARD_AES_KEY_HEX": TEST_KEY_HEX,
                "PHONE_AES_KEY_HEX": TEST_PHONE_KEY_HEX,
                "BACKUP_ENCRYPTION_KEY_HEX": TEST_BACKUP_KEY_HEX,
                "SENSITIVE_LOOKUP_HMAC_KEY_HEX": TEST_LOOKUP_HMAC_KEY_HEX,
                "DESHENGCUN_DATABASE_URL": "",
                "DATABASE_URL": "",
                "DESHENGCUN_DB_PATH": str(db.DB_PATH),
            },
            clear=False,
        )
        self.environment.start()
        db.init_db()

    def tearDown(self) -> None:
        self.environment.stop()
        db.DB_PATH = self.original_db_path
        db.DATA_DIR = self.original_data_dir
        db.DB_BACKEND = self.original_db_backend
        self.temp_dir.cleanup()

    def test_purpose_bound_encryption_detects_tampering(self) -> None:
        protected = secret_protection.protect_text("敏感字段", purpose="test_field")
        self.assertNotIn("敏感字段", protected)
        self.assertEqual(
            secret_protection.unprotect_text(protected, purpose="test_field"),
            "敏感字段",
        )
        payload = json.loads(protected)
        payload["mac"] = "0" * 64
        tampered = json.dumps(payload, separators=(",", ":"))
        with self.assertRaisesRegex(ValueError, "sensitive_data_decrypt_failed"):
            secret_protection.unprotect_text(tampered, purpose="test_field")
        with self.assertRaisesRegex(ValueError, "sensitive_data_decrypt_failed"):
            secret_protection.unprotect_text(protected, purpose="other_field")

    def test_identity_and_phone_hashes_use_independent_lookup_hmac_domains(self) -> None:
        normalized_id = "00000019900101123X"
        normalized_phone = "10000138888"
        id_hash = services._id_hash(f" {normalized_id.lower()} ")
        phone_hash = services._phone_hash(
            f"{normalized_phone[:3]}-{normalized_phone[3:7]}-{normalized_phone[7:]}"
        )

        self.assertEqual(
            id_hash,
            secret_protection.keyed_lookup_hash(
                normalized_id,
                purpose="identity.id_card",
            ),
        )
        self.assertEqual(
            phone_hash,
            secret_protection.keyed_lookup_hash(
                normalized_phone,
                purpose="identity.phone",
            ),
        )
        self.assertNotEqual(
            id_hash,
            hashlib.sha256(normalized_id.encode("utf-8")).hexdigest(),
        )
        self.assertNotEqual(
            phone_hash,
            hashlib.sha256(normalized_phone.encode("utf-8")).hexdigest(),
        )
        self.assertNotEqual(
            secret_protection.keyed_lookup_hash("same-value", purpose="identity.id_card"),
            secret_protection.keyed_lookup_hash("same-value", purpose="identity.phone"),
        )

    def test_lookup_hmac_key_has_no_missing_key_fallback(self) -> None:
        with patch.dict(os.environ, {"SENSITIVE_LOOKUP_HMAC_KEY_HEX": ""}, clear=False):
            with self.assertRaisesRegex(ValueError, "sensitive_lookup_hmac_key_not_configured"):
                secret_protection.keyed_lookup_hash("value", purpose="identity.id_card")

    def test_production_rejects_weak_or_reused_lookup_hmac_key(self) -> None:
        from app import runtime_config

        for invalid_key in (
            "",
            "0" * 64,
            "1" * 64,
            TEST_KEY_HEX,
            TEST_PHONE_KEY_HEX,
            TEST_BACKUP_KEY_HEX,
        ):
            with self.subTest(invalid_key=invalid_key[:4]):
                with patch.dict(
                    os.environ,
                    {
                        "SENSITIVE_LOOKUP_HMAC_KEY_HEX": invalid_key,
                        "ID_CARD_AES_KEY_HEX": TEST_KEY_HEX,
                        "PHONE_AES_KEY_HEX": TEST_PHONE_KEY_HEX,
                        "BACKUP_ENCRYPTION_KEY_HEX": TEST_BACKUP_KEY_HEX,
                    },
                    clear=False,
                ):
                    errors = runtime_config.collect_release_configuration_errors(target_env="production")
                self.assertTrue(any("SENSITIVE_LOOKUP_HMAC_KEY_HEX" in error for error in errors))

        with patch.dict(
            os.environ,
            {
                "SENSITIVE_LOOKUP_HMAC_KEY_HEX": TEST_LOOKUP_HMAC_KEY_HEX,
                "ID_CARD_AES_KEY_HEX": TEST_KEY_HEX,
                "PHONE_AES_KEY_HEX": TEST_PHONE_KEY_HEX,
                "BACKUP_ENCRYPTION_KEY_HEX": TEST_BACKUP_KEY_HEX,
            },
            clear=False,
        ):
            valid_errors = runtime_config.collect_release_configuration_errors(target_env="production")
        self.assertFalse(any("SENSITIVE_LOOKUP_HMAC_KEY_HEX" in error for error in valid_errors))

    def test_business_records_store_phone_and_id_only_as_ciphertext_or_mask(self) -> None:
        now = services.now_iso()
        conn = db.get_connection()
        try:
            user_id = conn.execute(
                """
                INSERT INTO users(
                    openid, nickname, real_name, gender, phone_masked, phone_ciphertext,
                    phone_bound, phone_verified_at, id_card_masked, id_card_hash,
                    id_card_encrypted, role, realname_status, auth_status,
                    roster_match_status, village_group, created_at, updated_at
                )
                VALUES('security-openid', '测试村民', '王五', '男', ?, ?, 1, ?, ?, ?, ?,
                       'villager', 'verified', 'verified', 'matched', '第一村民小组', ?, ?)
                """,
                (
                    services.mask_phone("10000138888"),
                    services.encrypt_phone_number("10000138888"),
                    now,
                    services.mask_id_card("00000019900101123X"),
                    services._id_hash("00000019900101123X"),
                    services.encrypt_id_card_number("00000019900101123X"),
                    now,
                    now,
                ),
            ).lastrowid
            conn.execute(
                "INSERT INTO auth_sessions(user_id, token, created_at, expires_at) VALUES(?, ?, ?, ?)",
                (
                    user_id,
                    services._hash_session_token("security-token"),
                    now,
                    "2999-01-01T00:00:00+00:00",
                ),
            )
            service_id = conn.execute(
                """
                INSERT INTO gov_services(service_key, title, is_enabled, created_at, updated_at)
                VALUES('security-test', '安全测试', 1, ?, ?)
                """,
                (now, now),
            ).lastrowid
            conn.commit()
        finally:
            conn.close()

        request_row = services.create_villager_request(
            "security-token",
            {
                "request_type": "service",
                "title": "安全测试诉求",
                "content": "仅用于自动测试",
                "contact_phone": "10000138888",
            },
        )
        application_row = services.create_gov_application(
            "security-token",
            {
                "service_id": service_id,
                "applicant_name": "王五",
                "applicant_phone": "10000138888",
                "extra_fields": {"id_card": "00000019900101123X"},
            },
        )
        self.assertEqual(request_row["contact_phone"], "100****8888")
        self.assertEqual(application_row["applicant_phone"], "100****8888")
        self.assertEqual(application_row["extra_fields"]["id_card"], "000000************")

        conn = db.get_connection()
        try:
            stored_request = dict(conn.execute("SELECT * FROM villager_requests LIMIT 1").fetchone())
            stored_application = dict(
                conn.execute("SELECT * FROM gov_service_applications LIMIT 1").fetchone()
            )
        finally:
            conn.close()
        self.assertNotIn("10000138888", json.dumps(stored_request, ensure_ascii=False))
        self.assertNotIn("10000138888", stored_application["applicant_phone"])
        self.assertNotIn("00000019900101123X", stored_application["extra_fields"])
        sensitive_json = secret_protection.unprotect_text(
            stored_application["sensitive_extra_fields_encrypted"],
            purpose="gov_application_extra",
        )
        self.assertEqual(json.loads(sensitive_json)["id_card"], "00000019900101123X")

    def test_admin_mfa_enrollment_is_required_before_business_access(self) -> None:
        now = admin_auth.now_iso()
        conn = db.get_connection()
        try:
            authorization_id = conn.execute(
                """
                INSERT INTO cadre_authorizations(
                    real_name, office_title, role_level, status, created_at, updated_at
                ) VALUES('测试管理员', '测试', 'super_admin', 'active', ?, ?)
                """,
                (now, now),
            ).lastrowid
            conn.commit()
        finally:
            conn.close()
        with patch.object(admin_auth, "ADMIN_MFA_REQUIRED", True):
            admin_auth.bootstrap_admin_user(
                login_name="security-admin",
                password="StrongPassword-2026",
                authorization_id=authorization_id,
                force_reset=False,
            )
            login = admin_auth.login_admin(
                login_name="security-admin",
                password="StrongPassword-2026",
                ip="127.0.0.1",
            )
            self.assertTrue(login["user"]["mfa_setup_required"])
            with self.assertRaisesRegex(ValueError, "admin_mfa_setup_required"):
                admin_auth.get_current_admin(login["token"])
            setup = admin_auth.begin_admin_mfa_setup(login["token"])
            code = admin_auth._totp_value(setup["secret"], admin_auth._totp_counter())
            confirmed = admin_auth.confirm_admin_mfa_setup(login["token"], code=code)
            self.assertTrue(confirmed["user"]["mfa_enabled"])
            self.assertEqual(len(confirmed["recovery_codes"]), 8)
            self.assertEqual(admin_auth.get_current_admin(login["token"])["login_name"], "security-admin")
            with self.assertRaisesRegex(ValueError, "admin_mfa_code_required"):
                admin_auth.login_admin(
                    login_name="security-admin",
                    password="StrongPassword-2026",
                    ip="127.0.0.1",
                )

    def test_legacy_sensitive_business_migration_is_idempotent(self) -> None:
        now = services.now_iso()
        conn = db.get_connection()
        try:
            conn.execute(
                """
                INSERT INTO villager_requests(
                    user_id, request_type, title, content, contact_phone, created_at, updated_at
                ) VALUES(1, 'service', '旧诉求', '测试', '10000138888', ?, ?)
                """,
                (now, now),
            )
            conn.execute(
                "INSERT INTO training_signups(program_id, name, phone, created_at) VALUES(1, '王五', '10000138888', ?)",
                (now,),
            )
            conn.execute(
                "INSERT INTO volunteer_activity_signups(activity_id, name, phone, created_at) VALUES(1, '王五', '10000138888', ?)",
                (now,),
            )
            conn.execute(
                """
                INSERT INTO gov_service_applications(
                    service_id, user_id, service_key, service_title, applicant_name,
                    applicant_phone, extra_fields, created_at, updated_at
                ) VALUES(1, 1, 'certificate', '证明', '王五', '10000138888', ?, ?, ?)
                """,
                ('{"id_card":"00000019900101123X"}', now, now),
            )
            legacy_user_id = conn.execute(
                """
                INSERT INTO users(
                    openid, real_name, id_card_masked, id_card_last4, id_card_hash,
                    id_card_encrypted, role, realname_status, created_at, updated_at
                ) VALUES('legacy-mask-user', '王五', '510***********123X', '123X', ?, ?,
                         'villager', 'verified', ?, ?)
                """,
                (
                    services._id_hash("00000019900101123X"),
                    services.encrypt_id_card_number("00000019900101123X"),
                    now,
                    now,
                ),
            ).lastrowid
            conn.execute(
                """
                INSERT INTO villager_registry(
                    user_id, real_name, id_card_masked, id_card_last4, id_card_hash,
                    created_at, updated_at
                ) VALUES(?, '王五', '510***********123X', '123X', ?, ?, ?)
                """,
                (legacy_user_id, services._id_hash("00000019900101123X"), now, now),
            )
            roster_batch_id = conn.execute(
                """
                INSERT INTO roster_import_batches(
                    filename, imported_by, imported_count, skipped_count, created_at
                ) VALUES('legacy.csv', 'test', 1, 0, ?)
                """,
                (now,),
            ).lastrowid
            conn.execute(
                """
                INSERT INTO villager_roster(
                    batch_id, full_name, id_last4, id_hash, group_name, status, created_at
                ) VALUES(?, '王五', '123X', ?, '第一村民小组', 'active', ?)
                """,
                (roster_batch_id, services._id_hash("00000019900101123X"), now),
            )
            conn.execute(
                """
                INSERT INTO audit_logs(
                    actor_user_id, actor_type, action, target_type, target_id, detail_json, created_at
                ) VALUES(?, 'villager', 'submit_realname', 'user', ?, ?, ?)
                """,
                (
                    legacy_user_id,
                    str(legacy_user_id),
                    '{"real_name":"王五","id_last4":"123X"}',
                    now,
                ),
            )
            authorization_id = conn.execute(
                """
                INSERT INTO cadre_authorizations(real_name, role_level, status, created_at, updated_at)
                VALUES('旧管理员', 'cadre', 'active', ?, ?)
                """,
                (now, now),
            ).lastrowid
            admin_user_id = conn.execute(
                """
                INSERT INTO admin_users(
                    login_name, display_name, real_name, cadre_authorization_id, password_hash,
                    security_policy_version, created_at, updated_at
                ) VALUES('legacy-admin', '旧管理员', '旧管理员', ?, 'unused', 0, ?, ?)
                """,
                (authorization_id, now, now),
            ).lastrowid
            conn.execute(
                """
                INSERT INTO admin_sessions(
                    admin_user_id, token_hash, created_at, expires_at, last_seen_at
                ) VALUES(?, 'legacy-session', ?, '2999-01-01T00:00:00+00:00', ?)
                """,
                (admin_user_id, now, now),
            )
            conn.commit()
        finally:
            conn.close()

        first = migrate_sensitive_business_data.migrate_sensitive_business_data()
        second = migrate_sensitive_business_data.migrate_sensitive_business_data()
        self.assertEqual(first["villager_request_phones_migrated"], 1)
        self.assertEqual(first["training_signup_phones_migrated"], 1)
        self.assertEqual(first["volunteer_signup_phones_migrated"], 1)
        self.assertEqual(first["gov_application_sensitive_json_migrated"], 1)
        self.assertEqual(first["admin_accounts_forced_password_reset"], 1)
        self.assertEqual(first["villager_identity_masks_updated"], 1)
        self.assertEqual(first["villager_registry_masks_updated"], 1)
        self.assertEqual(first["roster_id_last4_cleared"], 1)
        self.assertEqual(first["audit_identity_suffixes_removed"], 1)
        self.assertEqual(second["villager_request_phones_migrated"], 0)
        self.assertEqual(second["training_signup_phones_migrated"], 0)
        self.assertEqual(second["volunteer_signup_phones_migrated"], 0)
        self.assertEqual(second["gov_application_sensitive_json_migrated"], 0)
        self.assertEqual(second["admin_accounts_forced_password_reset"], 0)
        self.assertEqual(second["villager_identity_masks_updated"], 0)
        self.assertEqual(second["villager_registry_masks_updated"], 0)
        self.assertEqual(second["roster_id_last4_cleared"], 0)
        self.assertEqual(second["audit_identity_suffixes_removed"], 0)

        conn = db.get_connection()
        try:
            request_row = dict(conn.execute("SELECT * FROM villager_requests LIMIT 1").fetchone())
            training_row = dict(conn.execute("SELECT * FROM training_signups LIMIT 1").fetchone())
            volunteer_row = dict(
                conn.execute("SELECT * FROM volunteer_activity_signups LIMIT 1").fetchone()
            )
            application_row = dict(
                conn.execute("SELECT * FROM gov_service_applications LIMIT 1").fetchone()
            )
            admin_row = dict(conn.execute("SELECT * FROM admin_users LIMIT 1").fetchone())
            admin_session = dict(conn.execute("SELECT * FROM admin_sessions LIMIT 1").fetchone())
            user_row = dict(conn.execute("SELECT * FROM users WHERE id = ?", (legacy_user_id,)).fetchone())
            registry_row = dict(
                conn.execute("SELECT * FROM villager_registry WHERE user_id = ?", (legacy_user_id,)).fetchone()
            )
            roster_row = dict(conn.execute("SELECT * FROM villager_roster LIMIT 1").fetchone())
            audit_row = dict(
                conn.execute("SELECT * FROM audit_logs WHERE action = 'submit_realname' LIMIT 1").fetchone()
            )
        finally:
            conn.close()
        for row in (request_row, training_row, volunteer_row, application_row):
            self.assertNotIn("10000138888", json.dumps(row, ensure_ascii=False))
        self.assertNotIn("00000019900101123X", application_row["extra_fields"])
        self.assertTrue(application_row["sensitive_extra_fields_encrypted"])
        self.assertTrue(application_row["applicant_id_card_hash"])
        self.assertEqual(admin_row["password_reset_required"], 1)
        self.assertEqual(admin_row["security_policy_version"], 1)
        self.assertTrue(admin_session["revoked_at"])
        self.assertEqual(user_row["id_card_masked"], "000000************")
        self.assertEqual(user_row["id_card_last4"], "")
        self.assertEqual(registry_row["id_card_masked"], "000000************")
        self.assertEqual(registry_row["id_card_last4"], "")
        self.assertEqual(roster_row["id_last4"], "")
        self.assertNotIn("id_last4", json.loads(audit_row["detail_json"]))

    def test_forwarded_ip_is_ignored_for_untrusted_direct_peer(self) -> None:
        with patch.dict(
            os.environ,
            {"ADMIN_TRUSTED_PROXY_CIDRS": "10.0.0.0/8"},
            clear=False,
        ):
            self.assertEqual(
                admin_auth.resolve_client_ip(
                    peer_ip="203.0.113.10",
                    forwarded_for="198.51.100.20",
                ),
                "203.0.113.10",
            )
            self.assertEqual(
                admin_auth.resolve_client_ip(
                    peer_ip="10.0.0.4",
                    forwarded_for="198.51.100.20, 10.0.0.3",
                ),
                "198.51.100.20",
            )

    def test_encrypted_backup_can_be_verified_and_restored(self) -> None:
        backup_dir = Path(self.temp_dir.name) / "backups"
        backup_path = secure_database_backup.create_backup(backup_dir)
        self.assertEqual(backup_path.stat().st_mode & 0o777, 0o600)
        header = secure_database_backup.verify_backup(backup_path)
        self.assertEqual(header["content_type"], "sqlite")
        restored_path = Path(self.temp_dir.name) / "restore" / "restored.db"
        secure_database_backup.restore_sqlite_backup(backup_path, restored_path)
        self.assertTrue(restored_path.is_file())
        self.assertEqual(restored_path.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
