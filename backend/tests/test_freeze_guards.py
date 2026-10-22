from __future__ import annotations

import unittest
import os
import sqlite3
from unittest.mock import patch

from app import admin_services, schemas, services
from app.image_validation import matches_image_content_type


class IdentityValidationTests(unittest.TestCase):
    def test_accepts_valid_18_digit_id_card(self) -> None:
        self.assertTrue(services.is_valid_id_card("00000019900101123X"))

    def test_rejects_invalid_checksum_and_birth_date(self) -> None:
        self.assertFalse(services.is_valid_id_card("000000199001011231"))
        self.assertFalse(services.is_valid_id_card("00000019901301123X"))

    def test_accepts_valid_15_digit_legacy_id_card(self) -> None:
        self.assertTrue(services.is_valid_id_card("000004670401001"))

    def test_id_card_mask_keeps_only_first_six_characters(self) -> None:
        self.assertEqual(services.mask_id_card("00000019900101123X"), "000000************")
        self.assertEqual(services.mask_id_card("000004670401001"), "000004*********")


class ImageContentValidationTests(unittest.TestCase):
    def test_accepts_supported_image_signatures(self) -> None:
        self.assertTrue(matches_image_content_type("image/jpeg", b"\xff\xd8\xff\xe0payload"))
        self.assertTrue(matches_image_content_type("image/png", b"\x89PNG\r\n\x1a\npayload"))
        self.assertTrue(matches_image_content_type("image/webp", b"RIFF\x04\x00\x00\x00WEBPpayload"))
        self.assertTrue(matches_image_content_type("image/heic", b"\x00\x00\x00\x18ftypheic\x00\x00\x00\x00heic"))

    def test_rejects_declared_image_with_non_image_content(self) -> None:
        self.assertFalse(matches_image_content_type("image/png", b"plain text"))
        self.assertFalse(matches_image_content_type("image/jpeg", b"RIFF\x04\x00\x00\x00WEBP"))


class WorkflowGuardTests(unittest.TestCase):
    def test_terminal_request_status_cannot_regress(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_request_status_transition"):
            admin_services._require_status_transition(
                "resolved",
                "pending",
                admin_services.REQUEST_STATUS_TRANSITIONS,
                "invalid_request_status_transition",
            )

    def test_processing_request_can_complete(self) -> None:
        admin_services._require_status_transition(
            "processing",
            "resolved",
            admin_services.REQUEST_STATUS_TRANSITIONS,
            "invalid_request_status_transition",
        )


class ReleaseSecurityGuardTests(unittest.TestCase):
    def test_villager_signup_outputs_do_not_contain_identity_fields(self) -> None:
        self.assertEqual(
            set(schemas.TrainingSignupOut.model_fields),
            {"id", "program_id", "created_at"},
        )
        self.assertEqual(
            set(schemas.VolunteerActivitySignupOut.model_fields),
            {"id", "activity_id", "created_at"},
        )

    def test_private_upload_signature_is_limited_to_ten_minutes(self) -> None:
        with patch.object(services, "UPLOAD_URL_SIGN_SECRET", "test-only-upload-sign-secret"):
            url = services.build_upload_access_url(
                "https://api.example.invalid/api/v1/uploads/access/request/file.jpg"
            )
            expires_at = int(url.split("exp=", 1)[1].split("&", 1)[0])
            now = int(services.datetime.now(services.timezone.utc).timestamp())
            self.assertGreaterEqual(expires_at - now, 9 * 60)
            self.assertLessEqual(expires_at - now, 10 * 60)

            long_expiry = now + 11 * 60
            signature = services._build_upload_url_signature("request", "file.jpg", long_expiry)
            with self.assertRaisesRegex(ValueError, "invalid_upload_signature"):
                services.verify_upload_access_signature("request", "file.jpg", long_expiry, signature)

    def test_production_configuration_rejects_debug_and_default_password(self) -> None:
        from app import runtime_config

        with patch.dict(
            os.environ,
            {
                "DEBUG": "1",
                "DEFAULT_CADRE_MANAGER_PASSWORD": "999999",
                "MOCK_WECHAT_OPENID": "mock-only-in-development",
            },
            clear=False,
        ):
            errors = runtime_config.collect_release_configuration_errors(target_env="production")
        self.assertTrue(any("DEBUG" in error for error in errors))
        self.assertTrue(any("DEFAULT_CADRE_MANAGER_PASSWORD" in error for error in errors))
        self.assertTrue(any("MOCK_WECHAT_OPENID" in error for error in errors))

    def test_private_upload_ownership_rejects_other_user(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute(
            "CREATE TABLE stored_files (uploaded_by_user_id INTEGER, is_private INTEGER, "
            "scene TEXT, filename TEXT, status TEXT)"
        )
        conn.execute(
            "INSERT INTO stored_files VALUES (?, ?, ?, ?, ?)",
            (7, 1, "request", "private.jpg", "active"),
        )
        url = "https://api.example.invalid/api/v1/uploads/access/request/private.jpg"
        services._validate_private_upload_ownership_conn(conn, [url], 7)
        with self.assertRaisesRegex(ValueError, "upload_access_denied"):
            services._validate_private_upload_ownership_conn(conn, [url], 8)
        conn.close()


class IdentityGenderParsingTests(unittest.TestCase):
    FEMALE_IDS = (
        "000002199001011005",  # 17th digit 0
        "000002199001011224",  # 17th digit 2
        "000002199001011881",  # 17th digit 8
    )
    MALE_IDS = (
        "00000219900101111X",  # 17th digit 1, uppercase check character
        "000002199001011558",  # 17th digit 5
        "000002199001011996",  # 17th digit 9
    )

    def test_18_digit_even_sex_digits_are_female(self) -> None:
        for id_card in self.FEMALE_IDS:
            with self.subTest(id_card=id_card):
                self.assertEqual(services._gender_from_id_card(id_card), "女")

    def test_18_digit_odd_sex_digits_are_male(self) -> None:
        for id_card in self.MALE_IDS:
            with self.subTest(id_card=id_card):
                self.assertEqual(services._gender_from_id_card(id_card), "男")

    def test_lowercase_check_character_is_ignored_for_gender(self) -> None:
        self.assertEqual(services._gender_from_id_card("00000219900101111x"), "男")

    def test_legacy_15_digit_id_uses_last_digit(self) -> None:
        self.assertEqual(services._gender_from_id_card("000002900101122"), "女")
        self.assertEqual(services._gender_from_id_card("000002900101111"), "男")

    def test_invalid_id_does_not_guess_gender(self) -> None:
        for id_card in (
            "",
            "123",
            "00000219900101111",
            "00000219900101A05",
            "000002199001011110",
        ):
            with self.subTest(id_card=id_card):
                self.assertEqual(services._gender_from_id_card(id_card), "")

    def test_valid_stored_gender_is_preserved(self) -> None:
        self.assertEqual(
            services._resolve_gender("女", "00000219900101111X"),
            "女",
        )

    def test_missing_gender_is_filled_and_invalid_data_stays_pending(self) -> None:
        self.assertEqual(
            services._resolve_gender("", "00000219900101111X"),
            "男",
        )
        self.assertEqual(services._resolve_gender("invalid", "123"), "未知")


class GovernmentServiceRoutingTests(unittest.TestCase):
    def test_public_services_keeps_certificate_service_visible(self) -> None:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute(
            """
            CREATE TABLE gov_services (
                id INTEGER,
                service_key TEXT,
                title TEXT,
                subtitle TEXT,
                category TEXT,
                icon_emoji TEXT,
                theme_color TEXT,
                detail_type TEXT,
                action_label TEXT,
                is_enabled INTEGER,
                sort_order INTEGER,
                created_at TEXT,
                updated_at TEXT,
                contact_name TEXT,
                contact_phone TEXT,
                intro TEXT,
                detail_payload TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT INTO gov_services(
                id, service_key, title, subtitle, category, icon_emoji, theme_color,
                detail_type, action_label, is_enabled, sort_order, created_at,
                updated_at, contact_name, contact_phone, intro, detail_payload
            )
            VALUES(1, 'certificate', '我要开证明', '开具村级证明', 'government', '🧾',
                   '#e8f3f1', 'certificate', '开证明', 1, 1, '', '', '', '', '', '{}')
            """
        )
        with patch.object(services, "get_connection", return_value=conn), patch.object(
            services, "_seed_default_gov_services_conn"
        ):
            rows = services.list_gov_services()
        self.assertEqual([row["service_key"] for row in rows], ["certificate"])


class AdminIdentitySerializationTests(unittest.TestCase):
    def test_admin_identity_infers_gender_from_id_card_when_stored_gender_missing(self) -> None:
        row = {
            "id": 1,
            "real_name": "王五",
            "gender": "",
            "phone_masked": "100****8888",
            "phone_ciphertext": "phone-ciphertext",
            "id_card_masked": "000000************",
            "id_card_encrypted": "id-ciphertext",
            "auth_status": "verified",
            "realname_status": "verified",
            "roster_match_status": "matched",
            "village_group": "第一村民小组",
            "updated_at": "2026-07-12T00:00:00+00:00",
            "realname_submitted_at": "2026-07-12T00:00:00+00:00",
        }
        with (
            patch.object(admin_services, "_safe_decrypt_phone", return_value="10000138888"),
            patch.object(admin_services, "_safe_decrypt_id_card", return_value="00000019900101123X"),
        ):
            payload = admin_services._serialize_admin_villager_identity(row)
        self.assertEqual(payload["gender"], "男")

    def test_authenticated_admin_list_payload_only_contains_masked_identity(self) -> None:
        row = {
            "id": 1,
            "real_name": "王五",
            "gender": "男",
            "phone_masked": "100****8888",
            "phone_ciphertext": "phone-ciphertext",
            "id_card_masked": "000000************",
            "id_card_encrypted": "id-ciphertext",
            "auth_status": "verified",
            "realname_status": "verified",
            "roster_match_status": "matched",
            "village_group": "第一村民小组",
            "updated_at": "2026-07-12T00:00:00+00:00",
            "realname_submitted_at": "2026-07-12T00:00:00+00:00",
        }
        with (
            patch.object(admin_services, "_safe_decrypt_phone", return_value="10000138888"),
            patch.object(admin_services, "_safe_decrypt_id_card", return_value="00000019900101123X"),
        ):
            payload = admin_services._serialize_admin_villager_identity(row)
        self.assertNotIn("id_card_number", payload)
        self.assertNotIn("phone_number", payload)
        self.assertEqual(payload["id_card_masked"], "000000************")
        self.assertNotIn("birth_date", payload)

    def test_application_payload_masks_id_card_even_for_legacy_admin_flag(self) -> None:
        payload = services._gov_application_to_dict(
            {
                "applicant_phone": "10000138888",
                "extra_fields": '{"id_card":"00000019900101123X"}',
                "reply_photo_urls": "[]",
            },
            mask_sensitive=False,
        )
        self.assertEqual(payload["extra_fields"]["id_card"], "000000************")
        self.assertEqual(payload["applicant_phone"], "100****8888")

    def test_application_payload_masks_full_id_card_for_villager_record(self) -> None:
        payload = services._gov_application_to_dict(
            {
                "applicant_phone": "10000138888",
                "extra_fields": '{"id_card":"00000019900101123X"}',
                "reply_photo_urls": "[]",
            }
        )
        self.assertEqual(payload["extra_fields"]["id_card"], "000000************")


if __name__ == "__main__":
    unittest.main()
