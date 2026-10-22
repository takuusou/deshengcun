from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

try:
    import boto3
except ImportError:  # pragma: no cover - optional outside object-storage mode
    boto3 = None

try:
    from qcloud_cos import CosConfig, CosS3Client
except ImportError:  # pragma: no cover - optional outside cos mode
    CosConfig = None
    CosS3Client = None

from .runtime_config import (
    get_backend_upload_dir,
    get_object_storage_access_key,
    get_object_storage_bucket,
    get_object_storage_endpoint,
    get_object_storage_prefix,
    get_object_storage_provider,
    get_object_storage_region,
    get_object_storage_secret_key,
)

logger = logging.getLogger(__name__)


def _build_object_key(scene: str, filename: str) -> str:
    prefix = get_object_storage_prefix().strip("/")
    return f"{prefix}/{scene}/{filename}" if prefix else f"{scene}/{filename}"


def _parse_object_storage_endpoint() -> tuple[str, str]:
    endpoint = str(get_object_storage_endpoint() or "").strip()
    if not endpoint:
        return "", "https"
    parsed = urlsplit(endpoint if "://" in endpoint else f"https://{endpoint}")
    host = str(parsed.netloc or parsed.path or "").strip().strip("/")
    scheme = str(parsed.scheme or "https").strip().lower() or "https"
    return host, scheme


def _is_tencent_cos_endpoint() -> bool:
    host, _ = _parse_object_storage_endpoint()
    return host.endswith((".myqcloud.com", ".tencentcos.cn"))


def _build_cos_client() -> Any:
    if CosConfig is None or CosS3Client is None:
        raise RuntimeError("腾讯 COS 模式缺少 cos-python-sdk-v5 依赖，请先安装 requirements.txt。")
    endpoint_host, scheme = _parse_object_storage_endpoint()
    config_kwargs: dict[str, Any] = {
        "Region": get_object_storage_region() or None,
        "SecretId": get_object_storage_access_key(),
        "SecretKey": get_object_storage_secret_key(),
        "Scheme": scheme or "https",
    }
    if endpoint_host:
        config_kwargs["Endpoint"] = endpoint_host
    return CosS3Client(CosConfig(**config_kwargs))


def _store_local_upload(
    *,
    scene: str,
    filename: str,
    file_bytes: bytes,
) -> dict[str, Any]:
    upload_dir = get_backend_upload_dir()
    scene_dir = upload_dir / scene
    scene_dir.mkdir(parents=True, exist_ok=True)
    file_path = scene_dir / filename
    file_path.write_bytes(file_bytes)
    return {
        "storage_provider": "local",
        "bucket_name": "",
        "object_key": "",
        "source_path": str(file_path),
    }


def store_upload_bytes(
    *,
    scene: str,
    filename: str,
    content_type: str,
    file_bytes: bytes,
) -> dict[str, Any]:
    provider = get_object_storage_provider()
    if provider == "s3":
        bucket_name = get_object_storage_bucket()
        if not bucket_name:
            raise RuntimeError("OBJECT_STORAGE_BUCKET 未配置。")
        object_key = _build_object_key(scene, filename)
        try:
            if _is_tencent_cos_endpoint():
                client = _build_cos_client()
                client.put_object(
                    Bucket=bucket_name,
                    Key=object_key,
                    Body=file_bytes,
                    ContentType=content_type or "application/octet-stream",
                )
            else:
                if boto3 is None:
                    raise RuntimeError("对象存储模式缺少 boto3 依赖，请先安装 requirements.txt。")
                client = boto3.client(
                    "s3",
                    region_name=get_object_storage_region() or None,
                    endpoint_url=get_object_storage_endpoint() or None,
                    aws_access_key_id=get_object_storage_access_key(),
                    aws_secret_access_key=get_object_storage_secret_key(),
                )
                client.put_object(
                    Bucket=bucket_name,
                    Key=object_key,
                    Body=file_bytes,
                    ContentType=content_type or "application/octet-stream",
                )
            return {
                "storage_provider": "s3",
                "bucket_name": bucket_name,
                "object_key": object_key,
                "source_path": "",
            }
        except Exception:
            logger.exception(
                "object storage upload failed",
                extra={"upload_scene": scene, "upload_filename": filename},
            )
            raise ValueError("upload_store_failed")

    return _store_local_upload(
        scene=scene,
        filename=filename,
        file_bytes=file_bytes,
    )


def build_download_url(*, record: dict[str, Any], expires_in_seconds: int) -> str:
    provider = str(record.get("storage_provider") or "local").strip().lower()
    if provider != "s3":
        return ""
    bucket_name = str(record.get("bucket_name") or "").strip()
    object_key = str(record.get("object_key") or "").strip()
    if not bucket_name or not object_key:
        raise FileNotFoundError("missing_object_storage_reference")
    expires = max(60, min(int(expires_in_seconds), 7 * 24 * 60 * 60))
    if _is_tencent_cos_endpoint():
        client = _build_cos_client()
        return str(
            client.get_presigned_download_url(
                Bucket=bucket_name,
                Key=object_key,
                Expired=expires,
            )
        )
    if boto3 is None:
        raise RuntimeError("对象存储模式缺少 boto3 依赖，请先安装 requirements.txt。")
    client = boto3.client(
        "s3",
        region_name=get_object_storage_region() or None,
        endpoint_url=get_object_storage_endpoint() or None,
        aws_access_key_id=get_object_storage_access_key(),
        aws_secret_access_key=get_object_storage_secret_key(),
    )
    return str(
        client.generate_presigned_url(
            ClientMethod="get_object",
            Params={"Bucket": bucket_name, "Key": object_key},
            ExpiresIn=expires,
        )
    )


def resolve_local_file_path(record: dict[str, Any]) -> Path:
    source_path = str(record.get("source_path") or "").strip()
    if source_path:
        return Path(source_path)
    scene = str(record.get("scene") or "").strip().lower()
    filename = str(record.get("filename") or "").strip()
    return get_backend_upload_dir() / scene / filename


def build_file_sha256(file_bytes: bytes) -> str:
    return hashlib.sha256(file_bytes).hexdigest()
