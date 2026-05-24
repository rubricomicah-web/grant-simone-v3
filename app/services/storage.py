"""Storage abstraction.

Default is Railway/local disk for current deployment. Cloudflare R2/S3 can be enabled later
without changing API routes by setting STORAGE_BACKEND=s3 and S3_* env vars.
"""
from __future__ import annotations
import os, shutil, uuid
from pathlib import Path
from typing import BinaryIO
from app.core.config import settings

LOCAL_UPLOAD_DIR = Path(os.getenv("LOCAL_UPLOAD_DIR", "storage/uploads"))
LOCAL_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def storage_backend() -> str:
    return (getattr(settings, "storage_backend", None) or os.getenv("STORAGE_BACKEND", "local")).lower()


def save_upload(fileobj: BinaryIO, original_filename: str, tenant_id: int, user_id: int) -> dict:
    safe_name = original_filename.replace("/", "_").replace("\\", "_")
    key = f"tenant-{tenant_id}/user-{user_id}/{uuid.uuid4().hex}-{safe_name}"
    if storage_backend() == "s3":
        # Optional production path. Kept dependency-free until boss provides R2/S3 details.
        # Install boto3 and set S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY, S3_BUCKET.
        try:
            import boto3  # type: ignore
        except Exception as exc:
            raise RuntimeError("S3/R2 storage selected but boto3 is not installed") from exc
        client = boto3.client(
            "s3",
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
        )
        bucket = os.getenv("S3_BUCKET")
        if not bucket:
            raise RuntimeError("S3_BUCKET is required when STORAGE_BACKEND=s3")
        client.upload_fileobj(fileobj, bucket, key)
        return {"backend": "s3", "key": key, "path": f"s3://{bucket}/{key}"}

    path = LOCAL_UPLOAD_DIR / key
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as out:
        shutil.copyfileobj(fileobj, out)
    return {"backend": "local", "key": key, "path": str(path)}


def signed_url(path: str, expires_seconds: int = 900) -> str:
    if path.startswith("s3://"):
        try:
            import boto3  # type: ignore
        except Exception:
            return path
        bucket_key = path[len("s3://"):]
        bucket, key = bucket_key.split("/", 1)
        client = boto3.client(
            "s3",
            endpoint_url=os.getenv("S3_ENDPOINT_URL"),
            aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
        )
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )
    return path
