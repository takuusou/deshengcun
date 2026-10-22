from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_BACKEND_ENV_PATH = PROJECT_DIR / "backend" / ".env"
APPLY_RELEASE_CONFIG_PATH = PROJECT_DIR / "scripts" / "apply_release_config.py"
PUBLIC_BASE_PATTERN = re.compile(r"^(\s*(?:export\s+)?)PUBLIC_API_BASE_URL=(.*)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="切换得胜村正式自定义域名。")
    parser.add_argument("root_domain", help="主域名，例如 example.invalid")
    parser.add_argument(
        "--api-subdomain",
        default="api",
        help="API 子域名前缀，默认 api",
    )
    parser.add_argument(
        "--admin-subdomain",
        default="admin",
        help="Web 后台子域名前缀，默认 admin",
    )
    parser.add_argument(
        "--backend-env-file",
        default=str(DEFAULT_BACKEND_ENV_PATH),
        help="要更新的 backend/.env 文件路径",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅打印即将切换到的域名，不实际写文件",
    )
    return parser.parse_args()


def _normalize_label(value: str) -> str:
    text = str(value or "").strip().strip(".")
    text = re.sub(r"^https?://", "", text, flags=re.IGNORECASE)
    return text.strip("/")


def _build_origin(root_domain: str, subdomain: str) -> str:
    root = _normalize_label(root_domain)
    sub = _normalize_label(subdomain)
    host = f"{sub}.{root}" if sub else root
    return f"https://{host}"


def _replace_public_base_url(env_path: Path, public_base_url: str) -> None:
    original = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    lines = original.splitlines()
    updated_lines: list[str] = []
    replaced = False

    for line in lines:
        match = PUBLIC_BASE_PATTERN.match(line)
        if match:
            prefix = match.group(1) or ""
            updated_lines.append(f"{prefix}PUBLIC_API_BASE_URL={public_base_url}")
            replaced = True
        else:
            updated_lines.append(line)

    if not replaced:
        if updated_lines and updated_lines[-1].strip():
            updated_lines.append("")
        updated_lines.append(f"PUBLIC_API_BASE_URL={public_base_url}")

    env_path.write_text("\n".join(updated_lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    backend_env_path = Path(args.backend_env_file).expanduser()

    if not backend_env_path.exists():
        raise SystemExit(f"未找到 backend env 文件：{backend_env_path}")

    api_origin = _build_origin(args.root_domain, args.api_subdomain)
    admin_origin = _build_origin(args.root_domain, args.admin_subdomain)

    print(f"planned api origin: {api_origin}")
    print(f"planned admin origin: {admin_origin}")
    print(f"target backend env: {backend_env_path}")

    if args.dry_run:
        print("dry-run 模式：未写入 backend/.env，也未重写小程序/Web 配置。")
        return 0

    _replace_public_base_url(backend_env_path, api_origin)

    subprocess.run(
        [
            sys.executable,
            str(APPLY_RELEASE_CONFIG_PATH),
            "--backend-env-file",
            str(backend_env_path),
        ],
        check=True,
        cwd=str(PROJECT_DIR),
    )

    print("已更新 backend/.env 中的 PUBLIC_API_BASE_URL。")
    print("已同步更新小程序 production 环境和 web-admin/.env.production。")
    print("下一步仍需去云托管/静态站点/微信后台完成域名绑定、解析、合法域名配置后再重新部署。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
