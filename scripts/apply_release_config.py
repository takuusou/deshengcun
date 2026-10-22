from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = PROJECT_DIR / "backend"
MINIPROGRAM_DIR = PROJECT_DIR / "miniprogram"
PROJECT_CONFIG_PATH = MINIPROGRAM_DIR / "project.config.json"
MINIPROGRAM_ENV_PATH = MINIPROGRAM_DIR / "config" / "env.js"
WEB_ADMIN_DIR = PROJECT_DIR / "web-admin"
WEB_ADMIN_ENV_PATH = WEB_ADMIN_DIR / ".env.production"
DEFAULT_BACKEND_ENV_PATH = BACKEND_DIR / ".env"
ENV_LINE_PATTERN = re.compile(r"^(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="写入得胜村小程序和 Web 后台的发布配置。")
    parser.add_argument(
        "--backend-env-file",
        help="从该 .env 文件读取缺省发布参数；未传时会自动尝试读取 backend/.env。",
    )
    parser.add_argument("--appid", help="要写入 project.config.json 的真实 AppID。")
    parser.add_argument("--api-base", help="要写入小程序 production 环境的 API 地址。")
    parser.add_argument("--web-admin-api-base", help="要写入 web-admin/.env.production 的 API 地址。")
    parser.add_argument("--cloudbase-env", help="要写入小程序 production 环境的 CloudBase Env ID。")
    parser.add_argument("--cloudbase-service", help="要写入小程序 production 环境的服务名。")
    parser.add_argument("--public-base-url", help="要写入小程序 production 环境的公网根地址。")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印解析后的发布配置，不实际写入文件。",
    )
    return parser.parse_args()


def _strip_wrapping_quotes(value: str) -> str:
    text = str(value or "").strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in {"'", '"'}:
        return text[1:-1]
    return text


def _looks_like_placeholder(value: str) -> bool:
    text = str(value or "").strip()
    if not text:
        return True
    if text == "touristappid":
        return True
    return text.startswith("<") and text.endswith(">")


def _normalize_text(value: str) -> str:
    text = _strip_wrapping_quotes(value)
    return "" if _looks_like_placeholder(text) else text


def _normalize_public_base_url(value: str) -> str:
    return _normalize_text(value).rstrip("/")


def _normalize_api_base(value: str) -> str:
    text = _normalize_public_base_url(value)
    if not text:
        return ""
    if text.endswith("/api/v1"):
        return text
    if text.endswith("/api"):
        return f"{text}/v1"
    return f"{text}/api/v1"


def _resolve_backend_env_path(candidate: str | None) -> Path | None:
    if candidate:
        resolved = Path(candidate).expanduser()
        if not resolved.is_file():
            raise SystemExit(f"未找到 backend env 文件：{resolved}")
        return resolved
    if DEFAULT_BACKEND_ENV_PATH.is_file():
        return DEFAULT_BACKEND_ENV_PATH
    return None


def _load_env_values(path: Path | None) -> dict[str, str]:
    if path is None or not path.is_file():
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
        values[key] = _normalize_text(raw_value)
    return values


def _resolve_release_values(args: argparse.Namespace) -> tuple[Path | None, dict[str, str]]:
    env_path = _resolve_backend_env_path(args.backend_env_file)
    env_values = _load_env_values(env_path)

    public_base_url = _normalize_public_base_url(args.public_base_url or env_values.get("PUBLIC_API_BASE_URL"))
    api_base = _normalize_api_base(args.api_base or public_base_url)
    web_admin_api_base = _normalize_api_base(args.web_admin_api_base or api_base)

    values = {
        "appid": _normalize_text(args.appid or env_values.get("WECHAT_MINI_APP_ID")),
        "api_base": api_base,
        "web_admin_api_base": web_admin_api_base,
        "cloudbase_env": _normalize_text(args.cloudbase_env or env_values.get("CLOUDBASE_ENV_ID")),
        "cloudbase_service": _normalize_text(
            args.cloudbase_service or env_values.get("CLOUDBASE_SERVICE_NAME")
        ),
        "public_base_url": public_base_url,
    }
    return env_path, values


def update_miniprogram_production_env(
    *,
    api_base: str,
    env_id: str,
    service: str,
    public_base_url: str,
) -> None:
    if not MINIPROGRAM_ENV_PATH.is_file():
        raise SystemExit(f"未找到小程序环境配置：{MINIPROGRAM_ENV_PATH}")
    text = MINIPROGRAM_ENV_PATH.read_text(encoding="utf-8")
    replacements = (
        (r'const TARGET = "[^"]+";', 'const TARGET = "production";'),
        (
            r'(production:\s*\{\s*apiBase:\s*")[^"]+(")',
            rf"\g<1>{api_base}\g<2>",
        ),
        (
            r'(production:\s*\{.*?enabled:\s*)(?:true|false)',
            rf"\g<1>{'true' if env_id and service else 'false'}",
        ),
        (
            r'(production:\s*\{.*?envId:\s*")[^"]*(")',
            rf"\g<1>{env_id}\g<2>",
        ),
        (
            r'(production:\s*\{.*?service:\s*")[^"]*(")',
            rf"\g<1>{service}\g<2>",
        ),
        (
            r'(production:\s*\{.*?publicBaseUrl:\s*")[^"]*(")',
            rf"\g<1>{public_base_url}\g<2>",
        ),
    )
    for pattern, replacement in replacements:
        text, count = re.subn(pattern, replacement, text, count=1, flags=re.DOTALL)
        if count != 1:
            raise SystemExit(f"小程序 production 配置结构不完整，未匹配：{pattern}")
    MINIPROGRAM_ENV_PATH.write_text(text, encoding="utf-8")


def render_web_admin_env(api_base: str) -> str:
    return f"VITE_API_BASE_URL={json.dumps(str(api_base or '').strip(), ensure_ascii=False)}\n"


def main() -> int:
    args = parse_args()
    env_path, values = _resolve_release_values(args)
    appid = values["appid"]
    api_base = values["api_base"]
    web_admin_api_base = values["web_admin_api_base"]
    cloudbase_env = values["cloudbase_env"]
    cloudbase_service = values["cloudbase_service"]
    public_base_url = values["public_base_url"]

    if (
        not appid
        and not api_base
        and not web_admin_api_base
        and not cloudbase_env
        and not cloudbase_service
        and not public_base_url
    ):
        raise SystemExit("未解析到任何发布参数；请先填写 backend/.env，或显式传入命令行参数。")

    if env_path is not None:
        print(f"loaded backend env: {env_path}")

    if args.dry_run:
        print(
            json.dumps(
                {
                    "appid": appid,
                    "apiBase": api_base,
                    "webAdminApiBase": web_admin_api_base,
                    "cloudbaseEnvId": cloudbase_env,
                    "cloudbaseService": cloudbase_service,
                    "publicBaseUrl": public_base_url,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if appid:
        project_config = json.loads(PROJECT_CONFIG_PATH.read_text(encoding="utf-8"))
        project_config["appid"] = appid
        PROJECT_CONFIG_PATH.write_text(
            json.dumps(project_config, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"updated appid: {appid}")

    if api_base or cloudbase_env or cloudbase_service or public_base_url:
        update_miniprogram_production_env(
            api_base=api_base,
            env_id=cloudbase_env,
            service=cloudbase_service,
            public_base_url=public_base_url,
        )
        print(f"updated miniprogram production apiBase: {api_base}")

    resolved_web_admin_api_base = web_admin_api_base or api_base
    if resolved_web_admin_api_base:
        WEB_ADMIN_ENV_PATH.write_text(
            render_web_admin_env(resolved_web_admin_api_base),
            encoding="utf-8",
        )
        print(f"updated web admin api base: {resolved_web_admin_api_base}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
