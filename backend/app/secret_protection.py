from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
import secrets
import subprocess

from .runtime_config import get_app_env, load_runtime_env


load_runtime_env()

_PAYLOAD_VERSION = 1
_PAYLOAD_ALGORITHM = "aes-256-cbc+hmac-sha256"
_PURPOSE_PATTERN = re.compile(r"^[a-z0-9_.:-]{1,80}$")


def _root_key() -> bytes:
    key_hex = str(os.getenv("ID_CARD_AES_KEY_HEX", "") or "").strip().lower()
    if not key_hex:
        seed = str(os.getenv("ID_CARD_DEV_KEY_SEED", "") or "").strip()
        if get_app_env() == "production" or not seed:
            raise ValueError("sensitive_data_key_not_configured")
        key_hex = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    if re.fullmatch(r"[0-9a-f]{64}", key_hex) is None:
        raise ValueError("invalid_sensitive_data_key")
    return bytes.fromhex(key_hex)


def _lookup_root_key() -> bytes:
    key_hex = str(os.getenv("SENSITIVE_LOOKUP_HMAC_KEY_HEX", "") or "").strip().lower()
    if not key_hex:
        raise ValueError("sensitive_lookup_hmac_key_not_configured")
    disallowed_keys = {
        "0" * 64,
        "1" * 64,
        str(os.getenv("ID_CARD_AES_KEY_HEX", "") or "").strip().lower(),
        str(os.getenv("PHONE_AES_KEY_HEX", "") or "").strip().lower(),
        str(os.getenv("BACKUP_ENCRYPTION_KEY_HEX", "") or "").strip().lower(),
    }
    if re.fullmatch(r"[0-9a-f]{64}", key_hex) is None or key_hex in disallowed_keys:
        raise ValueError("invalid_sensitive_lookup_hmac_key")
    return bytes.fromhex(key_hex)


def _normalize_purpose(purpose: str) -> str:
    text = str(purpose or "").strip().lower()
    if _PURPOSE_PATTERN.fullmatch(text) is None:
        raise ValueError("invalid_sensitive_data_purpose")
    return text


def _derive_key(purpose: str, usage: str) -> bytes:
    label = f"deshengcun:v1:{usage}:{_normalize_purpose(purpose)}".encode("utf-8")
    root_key = _lookup_root_key() if usage == "lookup" else _root_key()
    return hmac.new(root_key, label, hashlib.sha256).digest()


def _run_aes256_cbc(*, decrypt: bool, key: bytes, iv: bytes, payload: bytes) -> bytes:
    command = [
        "openssl",
        "enc",
        "-aes-256-cbc",
        "-d" if decrypt else "-e",
        "-K",
        key.hex(),
        "-iv",
        iv.hex(),
        "-nosalt",
    ]
    try:
        process = subprocess.run(
            command,
            input=payload,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    except OSError as exc:
        raise ValueError("sensitive_data_decrypt_failed" if decrypt else "sensitive_data_encrypt_failed") from exc
    if process.returncode != 0:
        raise ValueError("sensitive_data_decrypt_failed" if decrypt else "sensitive_data_encrypt_failed")
    return process.stdout


def protect_text(plain_text: str, *, purpose: str) -> str:
    text = str(plain_text or "")
    if not text:
        return ""
    purpose_text = _normalize_purpose(purpose)
    encryption_key = _derive_key(purpose_text, "encryption")
    mac_key = _derive_key(purpose_text, "authentication")
    iv = secrets.token_bytes(16)
    ciphertext = _run_aes256_cbc(
        decrypt=False,
        key=encryption_key,
        iv=iv,
        payload=text.encode("utf-8"),
    )
    authenticated_payload = purpose_text.encode("utf-8") + b"\0" + iv + ciphertext
    mac = hmac.new(mac_key, authenticated_payload, hashlib.sha256).hexdigest()
    return json.dumps(
        {
            "v": _PAYLOAD_VERSION,
            "alg": _PAYLOAD_ALGORITHM,
            "purpose": purpose_text,
            "iv": base64.b64encode(iv).decode("ascii"),
            "ct": base64.b64encode(ciphertext).decode("ascii"),
            "mac": mac,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def unprotect_text(protected_text: str, *, purpose: str) -> str:
    payload_text = str(protected_text or "").strip()
    if not payload_text:
        return ""
    purpose_text = _normalize_purpose(purpose)
    try:
        payload = json.loads(payload_text)
        version = int(payload.get("v") or 0)
        algorithm = str(payload.get("alg") or "")
        stored_purpose = str(payload.get("purpose") or "")
        iv = base64.b64decode(str(payload.get("iv") or ""), validate=True)
        ciphertext = base64.b64decode(str(payload.get("ct") or ""), validate=True)
        mac = str(payload.get("mac") or "").lower()
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("sensitive_data_decrypt_failed") from exc
    if (
        not isinstance(payload, dict)
        or version != _PAYLOAD_VERSION
        or algorithm != _PAYLOAD_ALGORITHM
        or stored_purpose != purpose_text
        or len(iv) != 16
        or not ciphertext
        or re.fullmatch(r"[0-9a-f]{64}", mac) is None
    ):
        raise ValueError("sensitive_data_decrypt_failed")
    mac_key = _derive_key(purpose_text, "authentication")
    authenticated_payload = purpose_text.encode("utf-8") + b"\0" + iv + ciphertext
    expected_mac = hmac.new(mac_key, authenticated_payload, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_mac, mac):
        raise ValueError("sensitive_data_decrypt_failed")
    plain_bytes = _run_aes256_cbc(
        decrypt=True,
        key=_derive_key(purpose_text, "encryption"),
        iv=iv,
        payload=ciphertext,
    )
    try:
        return plain_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("sensitive_data_decrypt_failed") from exc


def keyed_lookup_hash(value: str, *, purpose: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    key = _derive_key(purpose, "lookup")
    return hmac.new(key, text.encode("utf-8"), hashlib.sha256).hexdigest()
