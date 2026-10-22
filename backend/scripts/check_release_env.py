from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlparse


SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPT_DIR.parent
PROJECT_DIR = BACKEND_DIR.parent
MINIPROGRAM_DIR = PROJECT_DIR / "miniprogram"
PROJECT_CONFIG_PATH = MINIPROGRAM_DIR / "project.config.json"
PRIVATE_PROJECT_CONFIG_PATH = MINIPROGRAM_DIR / "project.private.config.json"
MINIPROGRAM_ENV_PATH = MINIPROGRAM_DIR / "config" / "env.js"
WEB_ADMIN_ENV_PATH = PROJECT_DIR / "web-admin" / ".env.production"
ENV_LINE_PATTERN = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查得胜村后端发布配置是否就绪。")
    parser.add_argument(
        "--target-env",
        default="production",
        help="按哪个环境标准执行校验，默认 production。",
    )
    return parser.parse_args()


def _strip_wrapping_quotes(value: str) -> str:
    text = str(value or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1]
    return text


def _normalize_public_base_url(value: str) -> str:
    return _strip_wrapping_quotes(value).rstrip("/")


def _normalize_api_base(value: str) -> str:
    text = _normalize_public_base_url(value)
    if not text:
        return ""
    if text.endswith("/api/v1"):
        return text
    if text.endswith("/api"):
        return f"{text}/v1"
    return f"{text}/api/v1"


def _load_env_values(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = ENV_LINE_PATTERN.match(line)
        if not match:
            continue
        key, raw_value = match.groups()
        values[key] = _strip_wrapping_quotes(raw_value)
    return values


def _extract_js_object_block(path: Path, key: str) -> str:
    if not path.is_file():
        return ""
    text = path.read_text(encoding="utf-8")
    match = re.search(rf"\b{re.escape(key)}\s*:\s*\{{", text)
    if not match:
        return ""
    start = text.find("{", match.start())
    depth = 0
    quote = ""
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in {'"', "'"}:
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return ""


def _read_active_miniprogram_config() -> dict[str, str | bool | None]:
    if not MINIPROGRAM_ENV_PATH.is_file():
        return {
            "target": "",
            "api_base": "",
            "cloudbase_enabled": None,
            "cloudbase_env_id": "",
            "cloudbase_service": "",
            "public_base_url": "",
        }
    text = MINIPROGRAM_ENV_PATH.read_text(encoding="utf-8")
    target_match = re.search(r"""const\s+DEFAULT_TARGET\s*=\s*(["'])(.*?)\1""", text)
    if target_match is None:
        target_match = re.search(r"""const\s+TARGET\s*=\s*(["'])(.*?)\1""", text)
    target = str(target_match.group(2) if target_match else "").strip()
    block = _extract_js_object_block(MINIPROGRAM_ENV_PATH, target) if target else ""

    def read_string(key: str) -> str:
        match = re.search(rf"""\b{re.escape(key)}\s*:\s*(["'])(.*?)\1""", block, re.DOTALL)
        return _strip_wrapping_quotes(match.group(2)) if match else ""

    enabled_match = re.search(r"\benabled\s*:\s*(true|false)\b", block)
    return {
        "target": target,
        "api_base": read_string("apiBase"),
        "cloudbase_enabled": enabled_match.group(1) == "true" if enabled_match else None,
        "cloudbase_env_id": read_string("envId"),
        "cloudbase_service": read_string("service"),
        "public_base_url": read_string("publicBaseUrl"),
    }


def _is_local_hostname(hostname: str) -> bool:
    host = str(hostname or "").strip().lower()
    if not host:
        return False
    return host in {"localhost", "127.0.0.1", "0.0.0.0", "::1"} or host.endswith(".local")


def _is_https_origin(value: str) -> bool:
    parsed = urlparse(str(value or "").strip())
    return parsed.scheme == "https" and bool(parsed.netloc) and parsed.path in {"", "/"}


def _is_https_api_base(value: str) -> bool:
    parsed = urlparse(str(value or "").strip())
    return parsed.scheme == "https" and bool(parsed.netloc) and parsed.path.endswith("/api/v1")


def _read_miniprogram_appid() -> str:
    if not PROJECT_CONFIG_PATH.is_file():
        return ""
    try:
        payload = json.loads(PROJECT_CONFIG_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    return str(payload.get("appid") or "").strip()


def _read_project_config(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def collect_client_release_configuration_errors(*, target_env: str | None = None) -> list[str]:
    env_name = str(target_env or os.getenv("APP_ENV") or "production").strip().lower()
    if env_name != "production":
        return []

    errors: list[str] = []
    for config_path in (PROJECT_CONFIG_PATH, PRIVATE_PROJECT_CONFIG_PATH):
        config = _read_project_config(config_path)
        setting = config.get("setting") if isinstance(config.get("setting"), dict) else {}
        label = str(config_path.relative_to(PROJECT_DIR))
        if setting.get("urlCheck") is not True:
            errors.append(f"{label} 的 setting.urlCheck 必须为 true。")
        if setting.get("minified") is not True:
            errors.append(f"{label} 的 setting.minified 必须为 true。")
        if setting.get("uploadWithSourceMap") is not False:
            errors.append(f"{label} 的 setting.uploadWithSourceMap 必须为 false。")

    project_config = _read_project_config(PROJECT_CONFIG_PATH)
    ignores = project_config.get("packOptions", {}).get("ignore", []) if isinstance(project_config.get("packOptions"), dict) else []
    if not any(
        isinstance(item, dict)
        and item.get("type") == "file"
        and item.get("value") == "config/env.local.js"
        for item in ignores
    ):
        errors.append("miniprogram/project.config.json 必须将 config/env.local.js 排除在正式上传包外。")

    mini_config = _read_active_miniprogram_config()
    expected_appid = str(os.getenv("WECHAT_MINI_APP_ID") or "").strip()
    expected_public_base_url = _normalize_public_base_url(os.getenv("PUBLIC_API_BASE_URL") or "")
    expected_api_base = _normalize_api_base(expected_public_base_url)

    miniprogram_appid = _read_miniprogram_appid()
    if not miniprogram_appid or miniprogram_appid == "touristappid":
        errors.append("miniprogram/project.config.json 仍未写入真实小程序 AppID。")
    elif expected_appid and miniprogram_appid != expected_appid:
        errors.append("miniprogram/project.config.json 的 appid 与 WECHAT_MINI_APP_ID 不一致。")

    if mini_config["target"] != "production":
        errors.append("miniprogram/config/env.js 当前 TARGET 不是 production。")

    miniprogram_api_base = _normalize_api_base(str(mini_config["api_base"] or ""))
    if not miniprogram_api_base:
        errors.append("miniprogram/config/env.js 的 production apiBase 未配置。")
    elif not _is_https_api_base(miniprogram_api_base):
        errors.append("小程序当前 apiBase 必须是 HTTPS 且以 /api/v1 结尾。")
    elif _is_local_hostname(urlparse(miniprogram_api_base).hostname or ""):
        errors.append("小程序当前 apiBase 仍指向 localhost 或本机地址。")
    elif expected_api_base and miniprogram_api_base != expected_api_base:
        errors.append("小程序当前 apiBase 与 PUBLIC_API_BASE_URL 推导结果不一致。")

    cloudbase_enabled = mini_config["cloudbase_enabled"]
    cloudbase_env_id = str(mini_config["cloudbase_env_id"] or "")
    cloudbase_service = str(mini_config["cloudbase_service"] or "")
    cloudbase_public_base_url = _normalize_public_base_url(str(mini_config["public_base_url"] or ""))

    if cloudbase_enabled is not True:
        errors.append("小程序当前 CloudBase enabled 不是 true。")
    if not cloudbase_env_id:
        errors.append("小程序当前 CloudBase envId 未配置。")
    elif str(os.getenv("CLOUDBASE_ENV_ID") or "").strip() and cloudbase_env_id != str(
        os.getenv("CLOUDBASE_ENV_ID") or ""
    ).strip():
        errors.append("小程序当前 CloudBase envId 与 CLOUDBASE_ENV_ID 不一致。")
    if not cloudbase_service:
        errors.append("小程序当前 CloudBase service 未配置。")
    elif str(os.getenv("CLOUDBASE_SERVICE_NAME") or "").strip() and cloudbase_service != str(
        os.getenv("CLOUDBASE_SERVICE_NAME") or ""
    ).strip():
        errors.append("小程序当前 CloudBase service 与 CLOUDBASE_SERVICE_NAME 不一致。")
    if not cloudbase_public_base_url:
        errors.append("小程序当前 publicBaseUrl 未配置。")
    elif not _is_https_origin(cloudbase_public_base_url):
        errors.append("小程序当前 publicBaseUrl 必须是 HTTPS 根地址。")
    elif _is_local_hostname(urlparse(cloudbase_public_base_url).hostname or ""):
        errors.append("小程序当前 publicBaseUrl 仍指向 localhost 或本机地址。")
    elif expected_public_base_url and cloudbase_public_base_url != expected_public_base_url:
        errors.append("小程序当前 publicBaseUrl 与 PUBLIC_API_BASE_URL 不一致。")

    web_admin_env = _load_env_values(WEB_ADMIN_ENV_PATH)
    web_admin_api_base = _normalize_api_base(web_admin_env.get("VITE_API_BASE_URL", ""))
    if not WEB_ADMIN_ENV_PATH.is_file():
        errors.append("web-admin/.env.production 不存在，请先写入正式 VITE_API_BASE_URL。")
    elif not web_admin_api_base:
        errors.append("web-admin/.env.production 尚未写入 VITE_API_BASE_URL。")
    elif not _is_https_api_base(web_admin_api_base):
        errors.append("web-admin/.env.production 的 VITE_API_BASE_URL 必须是 HTTPS 且以 /api/v1 结尾。")
    elif _is_local_hostname(urlparse(web_admin_api_base).hostname or ""):
        errors.append("web-admin/.env.production 的 VITE_API_BASE_URL 仍指向 localhost 或本机地址。")
    elif expected_api_base and web_admin_api_base != expected_api_base:
        errors.append("web-admin/.env.production 的 VITE_API_BASE_URL 与 PUBLIC_API_BASE_URL 推导结果不一致。")

    return errors


def collect_client_release_configuration_warnings(*, target_env: str | None = None) -> list[str]:
    env_name = str(target_env or os.getenv("APP_ENV") or "production").strip().lower()
    if env_name != "production":
        return []

    warnings: list[str] = []
    web_admin_api_base = _normalize_api_base(_load_env_values(WEB_ADMIN_ENV_PATH).get("VITE_API_BASE_URL", ""))
    if WEB_ADMIN_ENV_PATH.is_file() and web_admin_api_base and not _is_https_api_base(web_admin_api_base):
        warnings.append("web-admin/.env.production 的 VITE_API_BASE_URL 不是标准 HTTPS /api/v1 地址。")
    return warnings


def main() -> int:
    args = parse_args()
    target_env = str(args.target_env or "production").strip().lower()
    os.environ["APP_ENV"] = target_env

    from app.runtime_config import (
        collect_release_configuration_errors,
        collect_release_configuration_warnings,
        get_backend_db_path,
        get_backend_upload_dir,
        get_database_backend,
        get_object_storage_provider,
    )

    errors = collect_release_configuration_errors(target_env=target_env)
    warnings = collect_release_configuration_warnings(target_env=target_env)
    errors.extend(collect_client_release_configuration_errors(target_env=target_env))
    warnings.extend(collect_client_release_configuration_warnings(target_env=target_env))

    print(f"target_env: {target_env}")
    print(f"database_backend: {get_database_backend()}")
    print(f"db_path: {get_backend_db_path()}")
    print(f"object_storage_provider: {get_object_storage_provider()}")
    print(f"upload_dir: {get_backend_upload_dir()}")
    print(f"miniprogram_appid: {_read_miniprogram_appid() or '<missing>'}")
    mini_config = _read_active_miniprogram_config()
    print(f"miniprogram_target: {mini_config['target'] or '<missing>'}")
    print(f"miniprogram_cloudbase_enabled: {mini_config['cloudbase_enabled']}")
    print(f"miniprogram_public_base_url: {_normalize_public_base_url(str(mini_config['public_base_url'] or '')) or '<missing>'}")
    print(
        "web_admin_api_base: "
        f"{_normalize_api_base(_load_env_values(WEB_ADMIN_ENV_PATH).get('VITE_API_BASE_URL', '')) or '<missing>'}"
    )

    if warnings:
        print("\nWarnings:")
        for item in warnings:
            print(f"- {item}")

    if errors:
        print("\nErrors:")
        for item in errors:
            print(f"- {item}")
        return 1

    print("\nRelease configuration check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
