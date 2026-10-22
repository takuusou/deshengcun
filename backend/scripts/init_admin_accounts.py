from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.admin_auth import bootstrap_admin_user
from app.db import init_db


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or update a web admin account.")
    parser.add_argument("--login-name", required=True, help="Admin login name")
    parser.add_argument("--password", required=True, help="Initial password")
    parser.add_argument("--authorization-id", type=int, default=0, help="cadre_authorizations.id")
    parser.add_argument("--real-name", default="", help="Fallback cadre real name when authorization id is unknown")
    parser.add_argument("--display-name", default="", help="Display name shown in web admin")
    parser.add_argument("--role-key", default="", help="super_admin / cadre / readonly")
    parser.add_argument("--force-reset", action="store_true", help="Require password reset after next login")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    init_db()
    user = bootstrap_admin_user(
        login_name=args.login_name,
        password=args.password,
        authorization_id=args.authorization_id,
        real_name=args.real_name,
        display_name=args.display_name,
        role_key=args.role_key,
        force_reset=args.force_reset,
    )
    print(
        f"admin account ready: id={user['id']} login_name={user['login_name']} "
        f"role_key={user['role_key']} cadre_authorization_id={user['cadre_authorization_id']}"
    )


if __name__ == "__main__":
    main()
