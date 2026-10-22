from __future__ import annotations

import argparse
from pathlib import Path

from app.db import init_db
from app.services import (
    _map_roster_row,
    _parse_csv_rows,
    _parse_xlsx_rows,
    get_connection,
    now_iso,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="直接导入正式村民户籍白名单到数据库。")
    parser.add_argument(
        "--file",
        required=True,
        help="白名单文件路径，支持 csv / xlsx",
    )
    parser.add_argument(
        "--imported-by",
        default="系统导入",
        help="导入批次记录显示的操作人，默认 系统导入",
    )
    return parser.parse_args()


def _load_raw_rows(file_path: Path) -> list[dict[str, str]]:
    ext = file_path.suffix.lower().lstrip(".")
    file_bytes = file_path.read_bytes()
    if ext == "csv":
        return _parse_csv_rows(file_bytes)
    if ext == "xlsx":
        return _parse_xlsx_rows(file_bytes)
    raise SystemExit("仅支持 csv 或 xlsx 文件。")


def _build_entries(raw_rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], int]:
    entries: list[dict[str, str]] = []
    skipped_count = 0
    dedup: set[tuple[str, str, str, str]] = set()
    for raw_row in raw_rows:
        row = _map_roster_row(raw_row)
        if row is None:
            skipped_count += 1
            continue
        key = (
            row["full_name"],
            row["id_last4"],
            row["id_hash"],
            row["group_name"],
        )
        if key in dedup:
            skipped_count += 1
            continue
        dedup.add(key)
        entries.append(row)
    return entries, skipped_count


def main() -> int:
    args = parse_args()
    file_path = Path(args.file).expanduser().resolve()
    if not file_path.is_file():
        raise SystemExit(f"未找到白名单文件：{file_path}")

    raw_rows = _load_raw_rows(file_path)
    entries, skipped_count = _build_entries(raw_rows)
    if not entries:
        raise SystemExit("白名单文件无有效数据，导入已取消。")

    init_db()
    conn = get_connection()
    try:
        now = now_iso()
        cursor = conn.execute(
            """
            INSERT INTO roster_import_batches(filename, imported_by, imported_count, skipped_count, created_at)
            VALUES(?, ?, 0, 0, ?)
            """,
            (file_path.name, str(args.imported_by or "").strip() or "系统导入", now),
        )
        batch_id = cursor.lastrowid

        conn.execute("UPDATE villager_roster SET status = 'inactive' WHERE status = 'active'")
        conn.executemany(
            """
            INSERT INTO villager_roster(
                batch_id, full_name, id_last4, id_hash, group_name, status, created_at
            )
            VALUES(?, ?, ?, ?, ?, 'active', ?)
            """,
            [
                (
                    batch_id,
                    row["full_name"],
                    row["id_last4"],
                    row["id_hash"],
                    row["group_name"],
                    now,
                )
                for row in entries
            ],
        )
        conn.execute(
            """
            UPDATE roster_import_batches
            SET imported_count = ?, skipped_count = ?
            WHERE id = ?
            """,
            (len(entries), skipped_count, batch_id),
        )
        conn.commit()
    finally:
        conn.close()

    print(f"file: {file_path}")
    print(f"imported_count: {len(entries)}")
    print(f"skipped_count: {skipped_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
