from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import os
from pathlib import Path
import re
import sys
from typing import TextIO


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services import _id_hash, _normalize_id_card, is_valid_id_card


EXPECTED_HEADERS = ("姓名", "身份证号", "组别")
EXPECTED_UNIQUE_RECORDS = 1743
HASH_PATTERN = re.compile(r"[0-9a-f]{64}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="从原始 CSV 生成户籍白名单 HMAC 重建 SQL，不连接数据库。"
    )
    parser.add_argument("--input-csv", required=True, help="原始户籍名册 CSV 路径。")
    parser.add_argument("--output-sql", help="SQL 输出路径；必须位于项目目录之外。")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只统计和校验，不生成 SQL 文件。",
    )
    return parser.parse_args()


def _normalize_real_name(value: str) -> str:
    # Keep this identical to submit_realname: trim surrounding whitespace only.
    return str(value or "").strip()


def _require_input_file(raw_path: str) -> Path:
    path = Path(raw_path).expanduser().resolve()
    if not path.is_file() or path.suffix.lower() != ".csv":
        raise SystemExit("输入必须是存在的 CSV 文件。")
    return path


def _require_output_file(raw_path: str | None, *, dry_run: bool) -> Path | None:
    if dry_run:
        return None
    if not raw_path:
        raise SystemExit("非 dry-run 模式必须指定 --output-sql。")
    path = Path(raw_path).expanduser().resolve()
    try:
        path.relative_to(PROJECT_DIR)
    except ValueError:
        pass
    else:
        raise SystemExit("SQL 输出路径不得位于项目目录内。")
    if not path.parent.is_dir():
        raise SystemExit("SQL 输出目录不存在。")
    if path.exists():
        raise SystemExit("SQL 输出文件已存在，拒绝覆盖。")
    return path


def _validate_headers(fieldnames: list[str] | None) -> None:
    headers = [str(name or "").strip() for name in (fieldnames or [])]
    if len(headers) != len(set(headers)) or any(name not in headers for name in EXPECTED_HEADERS):
        raise SystemExit("原始 CSV 表头必须包含：姓名、身份证号、组别。")


def _build_entries(
    stream: TextIO,
) -> tuple[list[tuple[str, str, str]], int, int, int]:
    reader = csv.DictReader(stream)
    _validate_headers(reader.fieldnames)
    entries: list[tuple[str, str, str]] = []
    seen_hashes: set[str] = set()
    total_count = 0
    skipped_count = 0
    duplicate_count = 0

    for raw_row in reader:
        total_count += 1
        full_name = _normalize_real_name(raw_row.get("姓名") or "")
        id_card_number = _normalize_id_card(raw_row.get("身份证号") or "")
        group_name = str(raw_row.get("组别") or "").strip()
        if (
            not full_name
            or len(full_name) > 60
            or len(group_name) > 80
            or not is_valid_id_card(id_card_number)
        ):
            skipped_count += 1
            continue

        try:
            id_hash = _id_hash(id_card_number)
        except ValueError as exc:
            raise SystemExit("HMAC 密钥未配置或不符合要求。") from exc
        if HASH_PATTERN.fullmatch(id_hash) is None:
            raise SystemExit("HMAC 指纹格式异常。")
        if id_hash in seen_hashes:
            duplicate_count += 1
            continue
        seen_hashes.add(id_hash)
        entries.append((full_name, id_hash, group_name))

    return entries, total_count, skipped_count, duplicate_count


def _mysql_utf8_expression(value: str) -> str:
    if not value:
        return "''"
    return f"CONVERT(0x{value.encode('utf-8').hex()} USING utf8mb4)"


def _build_sql(
    entries: list[tuple[str, str, str]],
    *,
    skipped_count: int,
    duplicate_count: int,
) -> str:
    created_at = datetime.now(timezone.utc).isoformat()
    batch_label = "hmac_rebuild_20260902"
    roster_values = []
    for full_name, id_hash, group_name in entries:
        roster_values.append(
            "(" + ", ".join(
                (
                    _mysql_utf8_expression(full_name),
                    f"'{id_hash}'",
                    _mysql_utf8_expression(group_name),
                    "'active'",
                    "@new_roster_batch_id",
                    "''",
                    f"'{created_at}'",
                )
            ) + ")"
        )

    return "\n".join(
        (
            "-- Generated locally. Contains no plaintext ID card numbers.",
            "START TRANSACTION;",
            "",
            "DELETE FROM villager_roster;",
            "DELETE FROM roster_import_batches;",
            "",
            "INSERT INTO roster_import_batches(",
            "    filename, imported_by, imported_count, skipped_count, created_at",
            ") VALUES (",
            f"    '{batch_label}', 'offline_hmac_rebuild', {len(entries)}, "
            f"{skipped_count + duplicate_count}, '{created_at}'",
            ");",
            "SET @new_roster_batch_id := LAST_INSERT_ID();",
            "",
            "INSERT INTO villager_roster(",
            "    full_name, id_hash, group_name, status, batch_id, id_last4, created_at",
            ") VALUES",
            ",\n".join(roster_values) + ";",
            "",
            "COMMIT;",
            "",
        )
    )


def _write_private_file(path: Path, content: str) -> None:
    file_descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8", newline="\n") as stream:
            file_descriptor = -1
            stream.write(content)
    finally:
        if file_descriptor >= 0:
            os.close(file_descriptor)


def _print_stats(
    *,
    total_count: int,
    generated_count: int,
    skipped_count: int,
    duplicate_count: int,
) -> None:
    print(f"total_rows={total_count}")
    print(f"generated_rows={generated_count}")
    print(f"skipped_rows={skipped_count}")
    print(f"duplicate_rows={duplicate_count}")


def main() -> int:
    args = parse_args()
    input_path = _require_input_file(args.input_csv)
    output_path = _require_output_file(args.output_sql, dry_run=bool(args.dry_run))

    with input_path.open("r", encoding="utf-8-sig", newline="") as stream:
        entries, total_count, skipped_count, duplicate_count = _build_entries(stream)

    _print_stats(
        total_count=total_count,
        generated_count=len(entries),
        skipped_count=skipped_count,
        duplicate_count=duplicate_count,
    )
    if len(entries) != EXPECTED_UNIQUE_RECORDS:
        raise SystemExit(f"有效去重记录数不是预期的 {EXPECTED_UNIQUE_RECORDS} 条，已拒绝生成 SQL。")
    if args.dry_run:
        return 0

    assert output_path is not None
    sql_text = _build_sql(
        entries,
        skipped_count=skipped_count,
        duplicate_count=duplicate_count,
    )
    _write_private_file(output_path, sql_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
