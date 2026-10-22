from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app import db, services


class VillagerSessionPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        self.original_db_path = db.DB_PATH
        self.original_data_dir = db.DATA_DIR
        self.original_db_backend = db.DB_BACKEND
        db.DB_PATH = Path(self.temp_dir.name) / "session-persistence.db"
        db.DATA_DIR = db.DB_PATH.parent
        db.DB_BACKEND = "sqlite"
        db.init_db()

    def tearDown(self) -> None:
        db.DB_PATH = self.original_db_path
        db.DATA_DIR = self.original_data_dir
        db.DB_BACKEND = self.original_db_backend
        self.temp_dir.cleanup()

    def test_wechat_relogin_preserves_identity_and_notice_subscription(self) -> None:
        now = services.now_iso()
        conn = db.get_connection()
        try:
            user_id = conn.execute(
                """
                INSERT INTO users(
                    openid, real_name, phone_bound, phone_verified_at,
                    role, realname_status, auth_status,
                    created_at, updated_at
                )
                VALUES('openid-session-test', '已实名村民', 1, ?, 'villager',
                       'verified', 'verified', ?, ?)
                """,
                (now, now, now),
            ).lastrowid
            conn.execute(
                """
                INSERT INTO notice_subscriptions(
                    user_id, openid, template_id, subscription_status, is_enabled,
                    created_at, updated_at
                )
                VALUES(?, 'openid-session-test', 'notice-template-test', 'accept', 1, ?, ?)
                """,
                (user_id, now, now),
            )
            conn.commit()
        finally:
            conn.close()

        notice_config = {
            "available": True,
            "template_id": "notice-template-test",
            "template_title": "资讯更新提醒",
            "prompt_title": "开启村务通知提醒",
            "prompt_content": "开启后接收村务通知。",
        }
        with (
            patch.object(
                services,
                "_exchange_wechat_code_for_identity",
                return_value={"openid": "openid-session-test", "unionid": ""},
            ),
            patch.object(services, "DATABASE_BACKEND", "sqlite"),
            patch.object(services, "_notice_subscription_config", return_value=notice_config),
        ):
            login_result = services.wechat_login({"code": "fresh-code"})
            status = services.get_notice_subscription_status(login_result["token"])

        self.assertEqual(login_result["user"]["id"], user_id)
        self.assertEqual(login_result["user"]["realname_status"], "verified")
        self.assertEqual(login_result["user"]["auth_status"], "verified")
        self.assertTrue(status["is_enabled"])
        self.assertEqual(status["current_status"], "accept")


if __name__ == "__main__":
    unittest.main()
