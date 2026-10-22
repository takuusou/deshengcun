"""本地演示: 往花名册写入测试身份, 供村民端"实名认证"匹配。
运行: cd backend && .venv/bin/python scripts/seed_local_roster.py
会打印一个可用的 姓名 + 身份证号, 在小程序村民端实名时填这个就能通过。
"""
from __future__ import annotations

import sqlite3
from pathlib import Path

from app import services

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "local_dev.db"

# 测试身份（虚构行政区划，仅用于本地测试）。前 17 位固定, 自动补校验位。
PREFIX17 = "00000019900101123"
NAME = "王五"
GROUP = "第一村民小组"


def _check_digit(body17: str) -> str:
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    codes = "10X98765432"
    total = sum(int(body17[i]) * weights[i] for i in range(17))
    return codes[total % 11]


def main() -> None:
    id_card = PREFIX17 + _check_digit(PREFIX17)
    if not services.is_valid_id_card(id_card):
        raise SystemExit(f"生成的身份证号无效: {id_card}")

    id_hash = services._id_hash(id_card)
    id_last4 = ""
    now = services.now_iso()

    conn = sqlite3.connect(str(DB_PATH))
    try:
        # 复用已有测试批次, 没有则建一个
        row = conn.execute(
            "SELECT id FROM roster_import_batches WHERE filename = 'local_demo_roster' LIMIT 1"
        ).fetchone()
        if row is None:
            cur = conn.execute(
                """
                INSERT INTO roster_import_batches(filename, imported_by, imported_count, skipped_count, created_at)
                VALUES('local_demo_roster', 'seed_script', 1, 0, ?)
                """,
                (now,),
            )
            batch_id = cur.lastrowid
        else:
            batch_id = int(row["id"]) if hasattr(row, "keys") else int(row[0])

        exists = conn.execute(
            "SELECT id FROM villager_roster WHERE full_name = ? AND id_hash = ? LIMIT 1",
            (NAME, id_hash),
        ).fetchone()
        if exists is None:
            conn.execute(
                """
                INSERT INTO villager_roster(batch_id, full_name, id_last4, id_hash, group_name, status, created_at)
                VALUES(?, ?, ?, ?, ?, 'active', ?)
                """,
                (batch_id, NAME, id_last4, id_hash, GROUP, now),
            )
        conn.commit()
    finally:
        conn.close()

    print("花名册测试身份已写入:")
    print(f"  姓名     : {NAME}")
    print(f"  身份证号 : {id_card}")
    print(f"  村组     : {GROUP}")
    print("在小程序村民端做'实名认证'时填这两项即可通过。")


if __name__ == "__main__":
    main()
