from __future__ import annotations

import os
import re
from pathlib import Path
from urllib.parse import urlparse


APP_DIR = Path(__file__).resolve().parent
BACKEND_DIR = APP_DIR.parent
DEFAULT_BACKEND_DB_PATH = BACKEND_DIR / "data" / "deshengcun_v1.db"
DEFAULT_BACKEND_UPLOAD_DIR = BACKEND_DIR / "uploads"
DEFAULT_OBJECT_STORAGE_PREFIX = "deshengcun"
_ENV_LINE_PATTERN = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def _strip_wrapping_quotes(value: str) -> str:
    text = str(value or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1]
    return text


def _looks_like_placeholder(value: str) -> bool:
    text = str(value or "").strip()
    return bool(text) and text.startswith("<") and text.endswith(">")


def _load_env_file(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        match = _ENV_LINE_PATTERN.match(line)
        if not match:
            continue
        key, raw_value = match.groups()
        os.environ.setdefault(key, _strip_wrapping_quotes(raw_value))


def load_runtime_env() -> None:
    for filename in (".env.local", ".env"):
        _load_env_file(BACKEND_DIR / filename)


load_runtime_env()


def _get_env_text(name: str, default: str = "") -> str:
    text = str(os.getenv(name, default) or default).strip()
    return "" if _looks_like_placeholder(text) else text


def _get_env_bool(name: str, default: str = "0") -> bool:
    return _get_env_text(name, default).lower() in {"1", "true", "yes", "on"}


def get_app_env() -> str:
    return _get_env_text("APP_ENV", "development").lower()


def get_database_url() -> str:
    return _get_env_text("DESHENGCUN_DATABASE_URL") or _get_env_text("DATABASE_URL")


def get_database_backend() -> str:
    database_url = get_database_url().lower()
    if database_url.startswith(("mysql://", "mysql+pymysql://")):
        return "mysql"
    return "sqlite"


def get_backend_db_path() -> Path:
    raw = _get_env_text("DESHENGCUN_DB_PATH") or _get_env_text("DB_PATH")
    if raw:
        return Path(raw).expanduser()
    database_url = get_database_url()
    if database_url.lower().startswith("sqlite:///"):
        return Path(database_url.replace("sqlite:///", "", 1)).expanduser()
    return DEFAULT_BACKEND_DB_PATH


def get_backend_upload_dir() -> Path:
    raw = _get_env_text("DESHENGCUN_UPLOAD_DIR") or _get_env_text("UPLOAD_DIR")
    return Path(raw).expanduser() if raw else DEFAULT_BACKEND_UPLOAD_DIR


def get_public_api_base_url() -> str:
    return _get_env_text("PUBLIC_API_BASE_URL").rstrip("/")


def is_cloudbase_auth_enabled() -> bool:
    if _get_env_bool("CLOUDBASE_AUTH_ENABLED", "0"):
        return True
    return get_app_env() == "production" and bool(get_cloudbase_env_id())


def get_cloudbase_env_id() -> str:
    return _get_env_text("CLOUDBASE_ENV_ID")


def get_cloudbase_service_name() -> str:
    return _get_env_text("CLOUDBASE_SERVICE_NAME")


def get_cloudbase_region() -> str:
    return _get_env_text("CLOUDBASE_REGION", "ap-shanghai")


def get_object_storage_provider() -> str:
    text = _get_env_text("OBJECT_STORAGE_PROVIDER", "local").lower()
    return text if text in {"local", "s3"} else "local"


def get_object_storage_bucket() -> str:
    return _get_env_text("OBJECT_STORAGE_BUCKET")


def get_object_storage_region() -> str:
    return _get_env_text("OBJECT_STORAGE_REGION")


def get_object_storage_endpoint() -> str:
    return _get_env_text("OBJECT_STORAGE_ENDPOINT")


def get_object_storage_access_key() -> str:
    return _get_env_text("OBJECT_STORAGE_ACCESS_KEY")


def get_object_storage_secret_key() -> str:
    return _get_env_text("OBJECT_STORAGE_SECRET_KEY")


def get_object_storage_prefix() -> str:
    prefix = _get_env_text("OBJECT_STORAGE_PREFIX", DEFAULT_OBJECT_STORAGE_PREFIX).strip("/")
    return prefix or DEFAULT_OBJECT_STORAGE_PREFIX


def get_phone_aes_key_hex() -> str:
    return _get_env_text("PHONE_AES_KEY_HEX").lower()


def _is_local_hostname(hostname: str) -> bool:
    host = str(hostname or "").strip().lower()
    if not host:
        return False
    if host in {"localhost", "0.0.0.0", "127.0.0.1", "::1"}:
        return True
    return host.endswith(".local")


def _validate_public_origin(name: str, value: str) -> str | None:
    text = str(value or "").strip().rstrip("/")
    if not text:
        return f"{name} 未配置。"
    parsed = urlparse(text)
    if parsed.scheme != "https" or not parsed.netloc:
        return f"{name} 必须是 HTTPS 根域名，例如 https://api.example.com 。"
    if parsed.path not in {"", "/"} or parsed.query or parsed.params or parsed.fragment:
        return f"{name} 只能填写源站根地址，不要带 /api/v1 或其它路径。"
    if _is_local_hostname(parsed.hostname or ""):
        return f"{name} 不能指向 localhost 或本机地址。"
    return None


def collect_release_configuration_errors(*, target_env: str | None = None) -> list[str]:
    env_name = str(target_env or get_app_env()).strip().lower()
    if env_name != "production":
        return []

    errors: list[str] = []
    weak_secret_values = {
        "",
        "secret",
        "secretkey",
        "changeme",
        "change_me",
        "password",
        "admin123",
        "admin1234",
        "deshengcun-v1-dev-id-card-key",
    }
    for secret_name in ("SESSION_SECRET", "SESSION_SECRET_KEY", "JWT_SECRET_KEY", "SECRET_KEY"):
        secret_value = _get_env_text(secret_name).lower()
        if secret_value and secret_value in weak_secret_values:
            errors.append(f"{secret_name} 仍是默认或明显弱密钥，请先替换。")

    if _get_env_bool("DEBUG", "0") or _get_env_bool("FASTAPI_DEBUG", "0"):
        errors.append("生产环境 DEBUG 必须保持为 0。")

    dev_key_seed = _get_env_text("ID_CARD_DEV_KEY_SEED").lower()
    if dev_key_seed in {"deshengcun-v1-dev-id-card-key", "development", "dev"}:
        errors.append("ID_CARD_DEV_KEY_SEED 仍是开发兜底值，请移除或替换。")

    app_id = _get_env_text("WECHAT_MINI_APP_ID")
    if not app_id or app_id == "touristappid":
        errors.append("WECHAT_MINI_APP_ID 仍是占位值，请替换为真实小程序 AppID。")
    if not _get_env_text("WECHAT_MINI_APP_SECRET"):
        errors.append("WECHAT_MINI_APP_SECRET 未配置。")
    if _get_env_bool("ALLOW_MOCK_WECHAT_LOGIN", "0"):
        errors.append("ALLOW_MOCK_WECHAT_LOGIN 生产环境必须保持为 0。")
    if _get_env_text("MOCK_WECHAT_OPENID"):
        errors.append("MOCK_WECHAT_OPENID 生产环境必须清空。")

    public_api_base_error = _validate_public_origin(
        "PUBLIC_API_BASE_URL",
        get_public_api_base_url(),
    )
    if public_api_base_error:
        errors.append(public_api_base_error)

    upload_sign_secret = _get_env_text("UPLOAD_URL_SIGN_SECRET")
    if not upload_sign_secret or upload_sign_secret.lower() in weak_secret_values:
        errors.append("UPLOAD_URL_SIGN_SECRET 未配置，图片签名链接不应继续使用开发兜底密钥。")

    id_card_key_hex = _get_env_text("ID_CARD_AES_KEY_HEX").lower()
    if (
        re.fullmatch(r"[0-9a-f]{64}", id_card_key_hex or "") is None
        or id_card_key_hex in {"0" * 64, "1" * 64}
    ):
        errors.append("ID_CARD_AES_KEY_HEX 必须配置为 64 位十六进制 AES 密钥。")

    phone_key_hex = get_phone_aes_key_hex()
    if phone_key_hex and (
        re.fullmatch(r"[0-9a-f]{64}", phone_key_hex) is None
        or phone_key_hex in {"0" * 64, "1" * 64}
    ):
        errors.append("PHONE_AES_KEY_HEX 必须配置为 64 位十六进制 AES 密钥。")

    backup_key_hex = _get_env_text("BACKUP_ENCRYPTION_KEY_HEX").lower()
    if (
        re.fullmatch(r"[0-9a-f]{64}", backup_key_hex or "") is None
        or backup_key_hex in {"0" * 64, "1" * 64, id_card_key_hex, phone_key_hex}
    ):
        errors.append("BACKUP_ENCRYPTION_KEY_HEX 必须配置为独立的 64 位十六进制强密钥。")

    lookup_hmac_key_hex = _get_env_text("SENSITIVE_LOOKUP_HMAC_KEY_HEX").lower()
    if (
        re.fullmatch(r"[0-9a-f]{64}", lookup_hmac_key_hex or "") is None
        or lookup_hmac_key_hex
        in {"0" * 64, "1" * 64, id_card_key_hex, phone_key_hex, backup_key_hex}
    ):
        errors.append(
            "SENSITIVE_LOOKUP_HMAC_KEY_HEX 必须配置为独立的 64 位十六进制强密钥，"
            "不得与身份证、手机号或备份密钥共用。"
        )

    default_password = _get_env_text("DEFAULT_CADRE_MANAGER_PASSWORD", "999999")
    if (
        len(default_password) < 12
        or default_password.lower() in weak_secret_values
        or default_password == "999999"
    ):
        errors.append("DEFAULT_CADRE_MANAGER_PASSWORD 必须至少12位且不能使用默认弱口令。")

    if not _get_env_bool("ADMIN_MFA_REQUIRED", "0"):
        errors.append("ADMIN_MFA_REQUIRED 生产环境必须保持为 1。")

    if get_database_backend() != "mysql":
        errors.append("生产环境必须切换到 MySQL 8.0，不能继续使用 SQLite。")

    if get_object_storage_provider() != "s3":
        errors.append("生产环境必须切换到私有对象存储，不能继续使用本地 uploads。")
    else:
        if not get_object_storage_bucket():
            errors.append("OBJECT_STORAGE_BUCKET 未配置。")
        if not get_object_storage_region():
            errors.append("OBJECT_STORAGE_REGION 未配置。")
        if not get_object_storage_endpoint():
            errors.append("OBJECT_STORAGE_ENDPOINT 未配置。")
        if not get_object_storage_access_key() or not get_object_storage_secret_key():
            errors.append("OBJECT_STORAGE_ACCESS_KEY / OBJECT_STORAGE_SECRET_KEY 未配置。")

    if not get_cloudbase_env_id():
        errors.append("CLOUDBASE_ENV_ID 未配置。")
    if not get_cloudbase_service_name():
        errors.append("CLOUDBASE_SERVICE_NAME 未配置。")

    return errors


def collect_release_configuration_warnings(*, target_env: str | None = None) -> list[str]:
    env_name = str(target_env or get_app_env()).strip().lower()
    if env_name != "production":
        return []

    warnings: list[str] = []
    db_path = get_backend_db_path()
    upload_dir = get_backend_upload_dir()
    if get_database_backend() == "sqlite" and db_path.suffix.lower() == ".db":
        warnings.append(f"当前数据库仍指向 SQLite 文件：{db_path}")
    if get_object_storage_provider() == "local" and upload_dir == DEFAULT_BACKEND_UPLOAD_DIR:
        warnings.append(f"当前上传目录仍指向本地磁盘目录：{upload_dir}")
    if not get_phone_aes_key_hex():
        warnings.append("PHONE_AES_KEY_HEX 未单独配置，当前会回退到身份证 AES 密钥。")
    if not _get_env_text("ADMIN_ALLOWED_IP_CIDRS"):
        warnings.append("ADMIN_ALLOWED_IP_CIDRS 未配置，后台尚未限制固定来源网络。")
    if not _get_env_text("ADMIN_TRUSTED_PROXY_CIDRS"):
        warnings.append("ADMIN_TRUSTED_PROXY_CIDRS 未显式配置，当前使用私网和回环地址作为可信代理网段。")

    return warnings


def ensure_production_configuration() -> None:
    errors = collect_release_configuration_errors()
    if not errors:
        return
    raise RuntimeError("生产环境配置校验失败： " + "；".join(errors))
