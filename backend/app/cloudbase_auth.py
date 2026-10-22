from __future__ import annotations

import base64
import contextvars
import json
from dataclasses import dataclass
from typing import Mapping

from .runtime_config import is_cloudbase_auth_enabled


@dataclass(frozen=True)
class CloudBaseIdentity:
    openid: str
    unionid: str = ""
    source: str = "cloudbase"


_current_identity: contextvars.ContextVar[CloudBaseIdentity | None] = contextvars.ContextVar(
    "deshengcun_cloudbase_identity",
    default=None,
)


def parse_cloudbase_identity(headers: Mapping[str, str]) -> CloudBaseIdentity | None:
    if not is_cloudbase_auth_enabled():
        return None
    openid = str(headers.get("x-wx-openid") or headers.get("X-WX-OPENID") or "").strip()
    unionid = str(headers.get("x-wx-unionid") or headers.get("X-WX-UNIONID") or "").strip()
    if not openid:
        return None
    return CloudBaseIdentity(openid=openid, unionid=unionid)


def set_request_identity(identity: CloudBaseIdentity | None) -> contextvars.Token[CloudBaseIdentity | None]:
    return _current_identity.set(identity)


def reset_request_identity(token: contextvars.Token[CloudBaseIdentity | None]) -> None:
    _current_identity.reset(token)


def get_request_identity() -> CloudBaseIdentity | None:
    return _current_identity.get()


def build_identity_token(identity: CloudBaseIdentity | None) -> str:
    if identity is None:
        return ""
    payload = {
        "openid": identity.openid,
        "unionid": identity.unionid,
        "source": identity.source,
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return f"cloudbase:{encoded}"


def build_current_identity_token() -> str:
    return build_identity_token(get_request_identity())


def parse_identity_token(token: str) -> CloudBaseIdentity | None:
    text = str(token or "").strip()
    if not text.startswith("cloudbase:"):
        return None
    payload_text = text.split(":", 1)[1].strip()
    if not payload_text:
        return None
    try:
        decoded = base64.urlsafe_b64decode(payload_text.encode("ascii"))
        payload = json.loads(decoded.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    openid = str(payload.get("openid") or "").strip()
    if not openid:
        return None
    return CloudBaseIdentity(
        openid=openid,
        unionid=str(payload.get("unionid") or "").strip(),
        source=str(payload.get("source") or "cloudbase").strip() or "cloudbase",
    )
