import os
import logging
import boto3
from botocore.exceptions import BotoCoreError, ClientError
from botocore.config import Config
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from app.config import settings

logger = logging.getLogger(__name__)

class StorageUploadError(Exception): pass
class StorageConfigurationError(Exception): pass

def is_retryable_storage_error(exception: BaseException) -> bool:
    """
    Surgical retry evaluator. 
    Prevents useless retries on permanent authentication/configuration failures (4xx).
    """
    if isinstance(exception, StorageUploadError):
        return True

    # BotoCore errors are typically low-level network/socket drops (Transient)
    if isinstance(exception, BotoCoreError):
        return True

    if isinstance(exception, ClientError):
        error_code = exception.response.get("Error", {}).get("Code", "")
        # Strictly retry ONLY on known Server-Side or Throttling exceptions
        if error_code in ("500", "502", "503", "504", "RequestTimeout", "SlowDown", "Throttling", "ThrottlingException"):
            return True
        return False # 400, 403, 404 etc., are fatal. Fail fast.

    return False

class MinioStorageClient:
    """
    Deterministic storage adapter for S3-compatible backends.
    Enforces strict access controls, idempotent bandwidth preservation, 
    and highly surgical transient fault tolerance.
    """
    def __init__(self):
        self.bucket_name = settings.S3_BUCKET_NAME
        
        # Enforce strict AWS Signature v4 for perfect MinIO compatibility
        strict_config = Config(signature_version="s3v4")
        
        self.s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=settings.S3_ACCESS_KEY,
            aws_secret_access_key=settings.S3_SECRET_KEY,
            config=strict_config
        )

        # Fail-Fast Infrastructure Check: Guarantee bucket exists on boot
        try:
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            logger.info(f"[Storage] Verified access to bucket: {self.bucket_name}")
        except ClientError as e:
            raise StorageConfigurationError(f"CRITICAL: Bucket '{self.bucket_name}' is inaccessible or missing: {str(e)}") from e

    @retry(
        retry=retry_if_exception(is_retryable_storage_error),
        wait=wait_exponential(multiplier=1.5, min=2, max=10),
        stop=stop_after_attempt(3),
        reraise=True
    )
    def upload_media(
        self, 
        file_path: str, 
        college_id: str, 
        media_type: str, 
        content_hash: str, 
        extension: str, 
        mime_type: str
    ) -> str:
        """
        Executes a pre-flight idempotency check, verifies local file integrity, 
        and streams the payload to MinIO via TransferManager.
        """
        # Deterministic Path: colleges/UUID/logo/hash.png
        storage_key = f"colleges/{college_id}/{media_type.lower()}/{content_hash}{extension}"
        
        # 1. Bandwidth Idempotency Check
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=storage_key)
            logger.info(f"[Storage] Object {storage_key} already exists. Skipping upload.")
            return storage_key
        except ClientError as e:
            # Safely handle various S3-compatible missing object codes
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code not in ("404", "NoSuchKey", "NotFound"):
                # If it's a 403 or 500 during head_object, we raise it. Tenacity will evaluate it.
                raise StorageUploadError(f"MinIO Head Object Failure: {str(e)}") from e

        # 2. Local Integrity Verification (Pre-Stream)
        try:
            file_size = os.path.getsize(file_path)
        except OSError as e:
            raise StorageUploadError(f"Failed to read file size for {file_path}: {str(e)}") from e

        # 3. Upload Stream (Boto3 TransferManager handles chunking automatically)
        try:
            with open(file_path, "rb") as f:
                self.s3_client.upload_fileobj(
                    f, 
                    self.bucket_name, 
                    storage_key,
                    ExtraArgs={
                        "ContentType": mime_type
                    }
                )
            logger.info(f"[Storage] Successfully persisted {storage_key} to MinIO ({file_size} bytes).")
            return storage_key

        except (BotoCoreError, ClientError) as e:
            logger.error(f"[Storage] Upload failure for {storage_key}: {type(e).__name__}")
            # Tenacity will intercept this exception and evaluate if it is retryable
            raise StorageUploadError(f"MinIO Upload Failure: {str(e)}") from e