from __future__ import annotations

import argparse
from datetime import datetime, timezone
import gzip
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from typing import BinaryIO
from urllib.parse import parse_qs, unquote, urlparse


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.runtime_config import (
    get_backend_db_path,
    get_database_backend,
    get_database_url,
    load_runtime_env,
)


MAGIC = b"DSCBK1\n"
TAG_BYTES = 32
REQUIRED_TABLES = {
    "users",
    "villager_roster",
    "admin_users",
    "admin_sessions",
    "audit_logs",
}


def _root_key() -> bytes:
    load_runtime_env()
    key_hex = str(os.getenv("BACKUP_ENCRYPTION_KEY_HEX", "") or "").strip().lower()
    if re.fullmatch(r"[0-9a-f]{64}", key_hex) is None or key_hex in {"0" * 64, "1" * 64}:
        raise ValueError("BACKUP_ENCRYPTION_KEY_HEX 必须是独立的 64 位十六进制强密钥。")
    return bytes.fromhex(key_hex)


def _derived_key(label: bytes) -> bytes:
    return hmac.new(_root_key(), b"deshengcun-backup-v1:" + label, hashlib.sha256).digest()


def _run_openssl(*, decrypt: bool, source: Path, target: Path, iv: bytes) -> None:
    command = [
        "openssl",
        "enc",
        "-aes-256-cbc",
        "-d" if decrypt else "-e",
        "-K",
        _derived_key(b"encryption").hex(),
        "-iv",
        iv.hex(),
        "-nosalt",
        "-in",
        str(source),
        "-out",
        str(target),
    ]
    result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=False)
    if result.returncode != 0:
        raise RuntimeError("备份解密失败。" if decrypt else "备份加密失败。")


def _stream_hmac(parts: list[bytes], file_obj: BinaryIO, *, limit: int | None = None) -> bytes:
    digest = hmac.new(_derived_key(b"authentication"), digestmod=hashlib.sha256)
    for part in parts:
        digest.update(part)
    remaining = limit
    while remaining is None or remaining > 0:
        size = 1024 * 1024 if remaining is None else min(1024 * 1024, remaining)
        chunk = file_obj.read(size)
        if not chunk:
            break
        digest.update(chunk)
        if remaining is not None:
            remaining -= len(chunk)
    if remaining not in {None, 0}:
        raise ValueError("备份文件已截断。")
    return digest.digest()


def _mysql_settings(database_url: str) -> dict[str, object]:
    parsed = urlparse(database_url)
    if parsed.scheme not in {"mysql", "mysql+pymysql"}:
        raise ValueError("数据库连接不是 MySQL。")
    database_name = str(parsed.path or "").lstrip("/")
    if not database_name:
        raise ValueError("MySQL 连接缺少数据库名。")
    query = parse_qs(parsed.query or "")
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": int(parsed.port or 3306),
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": database_name,
        "charset": str((query.get("charset") or ["utf8mb4"])[0] or "utf8mb4"),
    }


def _create_plain_backup(target: Path) -> str:
    backend = get_database_backend()
    if backend == "sqlite":
        source = get_backend_db_path()
        if not source.is_file():
            raise FileNotFoundError("SQLite 数据库文件不存在。")
        source_conn = sqlite3.connect(f"file:{source}?mode=ro", uri=True)
        target_conn = sqlite3.connect(target)
        try:
            source_conn.backup(target_conn)
        finally:
            target_conn.close()
            source_conn.close()
        return "sqlite"

    settings = _mysql_settings(get_database_url())
    command = [
        "mysqldump",
        "--single-transaction",
        "--quick",
        "--routines",
        "--triggers",
        "--hex-blob",
        "--set-gtid-purged=OFF",
        "--no-tablespaces",
        "--default-character-set",
        str(settings["charset"]),
        "--host",
        str(settings["host"]),
        "--port",
        str(settings["port"]),
        "--user",
        str(settings["user"]),
        str(settings["database"]),
    ]
    environment = os.environ.copy()
    environment["MYSQL_PWD"] = str(settings["password"])
    with target.open("wb") as output:
        result = subprocess.run(command, stdout=output, stderr=subprocess.PIPE, env=environment, check=False)
    if result.returncode != 0:
        raise RuntimeError("MySQL 备份失败，请检查 mysqldump、账号权限和网络。")
    return "mysql_sql"


def create_backup(output_dir: Path) -> Path:
    output_dir = output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = output_dir / f"deshengcun-{timestamp}.dscbk"
    if destination.exists():
        raise FileExistsError("目标备份已存在。")

    with tempfile.TemporaryDirectory(prefix="deshengcun-backup-") as temp_name:
        temp_dir = Path(temp_name)
        plain_path = temp_dir / "database.raw"
        compressed_path = temp_dir / "database.raw.gz"
        ciphertext_path = temp_dir / "database.enc"
        content_type = _create_plain_backup(plain_path)
        with plain_path.open("rb") as source, gzip.open(compressed_path, "wb", compresslevel=6) as compressed:
            shutil.copyfileobj(source, compressed)
        iv = secrets.token_bytes(16)
        _run_openssl(decrypt=False, source=compressed_path, target=ciphertext_path, iv=iv)
        header = json.dumps(
            {
                "version": 1,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "content_type": content_type,
                "iv": iv.hex(),
            },
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"
        with ciphertext_path.open("rb") as ciphertext:
            tag = _stream_hmac([MAGIC, header], ciphertext)
        with destination.open("xb") as output, ciphertext_path.open("rb") as ciphertext:
            output.write(MAGIC)
            output.write(header)
            shutil.copyfileobj(ciphertext, output)
            output.write(tag)
        destination.chmod(0o600)
    return destination


def _decrypt_backup(backup_path: Path, target: Path) -> dict[str, object]:
    backup_path = backup_path.expanduser().resolve()
    total_size = backup_path.stat().st_size
    with backup_path.open("rb") as source:
        if source.readline() != MAGIC:
            raise ValueError("不是得胜服务通安全备份文件。")
        header_line = source.readline()
        try:
            header = json.loads(header_line.decode("utf-8"))
            iv = bytes.fromhex(str(header["iv"]))
        except (KeyError, ValueError, TypeError, json.JSONDecodeError) as exc:
            raise ValueError("备份头信息无效。") from exc
        if int(header.get("version") or 0) != 1 or len(iv) != 16:
            raise ValueError("不支持的备份格式。")
        ciphertext_offset = source.tell()
        ciphertext_size = total_size - ciphertext_offset - TAG_BYTES
        if ciphertext_size <= 0:
            raise ValueError("备份文件已截断。")
        expected_tag = _stream_hmac([MAGIC, header_line], source, limit=ciphertext_size)
        stored_tag = source.read(TAG_BYTES)
        if len(stored_tag) != TAG_BYTES or not hmac.compare_digest(expected_tag, stored_tag):
            raise ValueError("备份完整性校验失败，文件可能损坏或密钥不正确。")

    with tempfile.TemporaryDirectory(prefix="deshengcun-decrypt-") as temp_name:
        ciphertext_path = Path(temp_name) / "database.enc"
        compressed_path = Path(temp_name) / "database.raw.gz"
        with backup_path.open("rb") as source, ciphertext_path.open("wb") as ciphertext:
            source.seek(ciphertext_offset)
            remaining = ciphertext_size
            while remaining > 0:
                chunk = source.read(min(1024 * 1024, remaining))
                if not chunk:
                    raise ValueError("备份文件已截断。")
                ciphertext.write(chunk)
                remaining -= len(chunk)
        _run_openssl(decrypt=True, source=ciphertext_path, target=compressed_path, iv=iv)
        with gzip.open(compressed_path, "rb") as compressed, target.open("wb") as output:
            shutil.copyfileobj(compressed, output)
    return header


def _verify_sqlite(path: Path) -> None:
    conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        integrity = str(conn.execute("PRAGMA integrity_check").fetchone()[0] or "")
        tables = {str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()
    if integrity.lower() != "ok":
        raise ValueError("SQLite 完整性检查失败。")
    missing = REQUIRED_TABLES - tables
    if missing:
        raise ValueError("备份缺少必要数据表：" + ", ".join(sorted(missing)))


def _verify_mysql_sql(path: Path) -> None:
    found: set[str] = set()
    patterns = {
        table_name: re.compile(rf"CREATE TABLE(?: IF NOT EXISTS)? [`']?{re.escape(table_name)}[`']?", re.I)
        for table_name in REQUIRED_TABLES
    }
    with path.open("r", encoding="utf-8", errors="replace") as source:
        for line in source:
            for table_name, pattern in patterns.items():
                if table_name not in found and pattern.search(line):
                    found.add(table_name)
    missing = REQUIRED_TABLES - found
    if missing:
        raise ValueError("MySQL 备份缺少必要数据表：" + ", ".join(sorted(missing)))


def verify_backup(backup_path: Path) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="deshengcun-verify-") as temp_name:
        plain_path = Path(temp_name) / "database.raw"
        header = _decrypt_backup(backup_path, plain_path)
        content_type = str(header.get("content_type") or "")
        if content_type == "sqlite":
            _verify_sqlite(plain_path)
        elif content_type == "mysql_sql":
            _verify_mysql_sql(plain_path)
        else:
            raise ValueError("备份内容类型无效。")
        return header


def restore_sqlite_backup(backup_path: Path, target: Path) -> None:
    target = target.expanduser().resolve()
    if target.exists():
        raise FileExistsError("恢复目标已存在；为防止覆盖，请使用一个新的空路径。")
    target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with tempfile.TemporaryDirectory(prefix="deshengcun-restore-") as temp_name:
        source_path = Path(temp_name) / "database.sqlite"
        header = _decrypt_backup(backup_path, source_path)
        if str(header.get("content_type") or "") != "sqlite":
            raise ValueError("该备份不是 SQLite 备份，不能恢复为 SQLite 文件。")
        _verify_sqlite(source_path)
        source_conn = sqlite3.connect(f"file:{source_path}?mode=ro", uri=True)
        target_conn = sqlite3.connect(target)
        try:
            source_conn.backup(target_conn)
        finally:
            target_conn.close()
            source_conn.close()
    target.chmod(0o600)
    _verify_sqlite(target)


def main() -> None:
    parser = argparse.ArgumentParser(description="创建、验证或恢复加密数据库备份；不会输出密钥或个人信息。")
    subparsers = parser.add_subparsers(dest="command", required=True)
    backup_parser = subparsers.add_parser("backup")
    backup_parser.add_argument("--output-dir", type=Path, required=True)
    verify_parser = subparsers.add_parser("verify")
    verify_parser.add_argument("backup_file", type=Path)
    restore_parser = subparsers.add_parser("restore-sqlite")
    restore_parser.add_argument("backup_file", type=Path)
    restore_parser.add_argument("--target", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "backup":
        path = create_backup(args.output_dir)
        print(f"encrypted_backup_created={path}")
        verify_backup(path)
        print("backup_verification=ok")
    elif args.command == "verify":
        header = verify_backup(args.backup_file)
        print(f"backup_verification=ok content_type={header['content_type']}")
    else:
        restore_sqlite_backup(args.backup_file, args.target)
        print(f"sqlite_restore_verification=ok target={args.target.resolve()}")


if __name__ == "__main__":
    main()
