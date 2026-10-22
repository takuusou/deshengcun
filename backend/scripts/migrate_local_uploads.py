from __future__ import annotations

import argparse
import mimetypes
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.runtime_config import get_backend_upload_dir  # noqa: E402
from app.services import store_uploaded_file_record  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate local uploaded files into configured object storage.")
    parser.add_argument(
        "--source-dir",
        default=str(get_backend_upload_dir()),
        help="Legacy local upload directory, defaults to backend/uploads",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source_dir = Path(args.source_dir).expanduser().resolve()
    if not source_dir.is_dir():
        raise SystemExit(f"Upload directory not found: {source_dir}")

    migrated = 0
    for scene_dir in sorted(path for path in source_dir.iterdir() if path.is_dir()):
        scene = scene_dir.name.strip().lower()
        for file_path in sorted(path for path in scene_dir.iterdir() if path.is_file()):
            content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
            store_uploaded_file_record(
                scene=scene,
                filename=file_path.name,
                content_type=content_type,
                file_bytes=file_path.read_bytes(),
                uploaded_by_token=None,
            )
            migrated += 1
            print(f"[ok] migrated {scene}/{file_path.name}")
    print(f"done: {migrated} files")


if __name__ == "__main__":
    main()
