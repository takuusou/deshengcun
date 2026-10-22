"""本地演示数据脚本 —— 仅本地 SQLite 测试库用。
造一个已实名村民, 走真实接口提交一条低保 + 一条特困申请(带照片),
让干部端后台能立刻看到效果, 同时真实验证后端改动。
运行: cd backend && .venv/bin/python scripts/seed_local_demo.py
"""
from __future__ import annotations

import json
import sqlite3
import struct
import urllib.error
import urllib.request
import zlib
from pathlib import Path

BASE = "http://127.0.0.1:8000/api/v1"
DB_PATH = Path(__file__).resolve().parent.parent / "data" / "local_dev.db"


def _api(path: str, payload: dict, token: str | None = None) -> dict:
    data = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json", "X-Role": "villager"}
    if token:
        headers["X-Token"] = token
    req = urllib.request.Request(BASE + path, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"[请求失败] POST {path} -> {exc.code}: {body}")


def _png(color: tuple[int, int, int], size: int = 240) -> bytes:
    """无依赖生成一张纯色 PNG。"""
    r, g, b = color
    row = b"\x00" + bytes([r, g, b]) * size
    raw = row * size

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )


def _upload(token: str, color: tuple[int, int, int]) -> str:
    import base64

    data_b64 = base64.b64encode(_png(color)).decode("ascii")
    res = _api(
        "/uploads/images-inline",
        {"scene": "request", "content_type": "image/png", "data_base64": data_b64},
        token=token,
    )
    return res["url"]


def _make_verified_villager(code: str, real_name: str, id_hash: str, group: str) -> str:
    res = _api("/auth/wechat-login", {"code": code, "nickname": real_name})
    token = res["token"]
    user_id = int(res["user"]["id"])
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute(
            """
            UPDATE users SET
                phone_bound = 1,
                phone_verified_at = '2026-06-27T10:00:00+00:00',
                phone_masked = '100****8888',
                phone_last4 = '8888',
                real_name = ?,
                gender = '男',
                realname_status = 'verified',
                auth_status = 'verified',
                roster_match_status = 'matched',
                id_card_hash = ?,
                id_card_masked = '000001************',
                id_card_last4 = '',
                village_group = ?
            WHERE id = ?
            """,
            (real_name, id_hash, group, user_id),
        )
        conn.commit()
    finally:
        conn.close()
    return token


def main() -> None:
    # 村民一: 提交低保申请
    token1 = _make_verified_villager("seed-zhangsan-001", "张三", "seedhash_zhangsan_001", "第一村民小组")
    dibao_materials = [
        ("application", "申请书", [(190, 60, 50)]),
        ("diagnosis", "病历诊断书", [(70, 110, 70), (90, 130, 80)]),
        ("hospitalization", "出入院记录", [(120, 90, 60)]),
        ("expense", "费用清单", [(60, 90, 130)]),
        ("hukou", "户口簿", [(150, 120, 70)]),
        # 银行卡 故意不传, 演示"未传"
    ]
    flat1, manifest1 = [], []
    for key, name, colors in dibao_materials:
        urls = [_upload(token1, c) for c in colors]
        flat1 += urls
        manifest1.append({"key": key, "name": name, "count": len(urls)})
    r1 = _api(
        "/requests",
        {
            "request_type": "dibao",
            "title": "低保申请",
            "content": json.dumps({"flow": "material", "kind": "dibao", "materials": manifest1}, ensure_ascii=False),
            "contact_phone": "10000138001",
            "photo_urls": flat1,
        },
        token=token1,
    )
    print(f"低保申请已创建: id={r1['id']} 照片{len(flat1)}张 状态={r1['status']}")

    # 村民二: 提交特困认证
    token2 = _make_verified_villager("seed-lisi-002", "李四", "seedhash_lisi_002", "第二村民小组")
    tekun_materials = [
        ("application", "申请书", [(190, 60, 50)]),
        ("hukou", "户口簿", [(150, 120, 70)]),
        ("id_card", "身份证", [(60, 90, 130), (80, 110, 150)]),
    ]
    flat2, manifest2 = [], []
    for key, name, colors in tekun_materials:
        urls = [_upload(token2, c) for c in colors]
        flat2 += urls
        manifest2.append({"key": key, "name": name, "count": len(urls)})
    r2 = _api(
        "/requests",
        {
            "request_type": "tekun",
            "title": "特困认证",
            "content": json.dumps({"flow": "material", "kind": "tekun", "materials": manifest2}, ensure_ascii=False),
            "contact_phone": "10000138002",
            "photo_urls": flat2,
        },
        token=token2,
    )
    print(f"特困认证已创建: id={r2['id']} 照片{len(flat2)}张 状态={r2['status']}")
    print("OK")


if __name__ == "__main__":
    main()
