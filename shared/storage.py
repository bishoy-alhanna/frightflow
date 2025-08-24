"""
MinIO object storage helper for document management with pre-signed URLs.
"""
import logging
import hashlib
import mimetypes
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, BinaryIO
from urllib.parse import urlparse
import io

try:
    from minio import Minio
    from minio.error import S3Error
except ImportError:
    Minio = None
    S3Error = Exception

from flask import current_app

logger = logging.getLogger(__name__)


class ObjectStorageManager:
    """MinIO object storage manager for document handling."""
    
    def __init__(self, endpoint: Optional[str] = None, access_key: Optional[str] = None, 
                 secret_key: Optional[str] = None, secure: bool = False, bucket: Optional[str] = None):
        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.secure = secure
        self.bucket = bucket
        self._client = None
    
    @property
    def client(self) -> Optional[Minio]:
        """Get MinIO client instance."""
        if Minio is None:
            logger.error("MinIO client not available. Install with: pip install minio")
            return None
        
        if self._client is None:
            endpoint = self.endpoint or current_app.config.get('OBJECT_STORE_ENDPOINT', 'localhost:9000')
            access_key = self.access_key or current_app.config.get('OBJECT_STORE_ACCESS_KEY', 'minioadmin')
            secret_key = self.secret_key or current_app.config.get('OBJECT_STORE_SECRET_KEY', 'minioadmin')
            secure = self.secure or current_app.config.get('OBJECT_STORE_SECURE', False)
            
            try:
                self._client = Minio(
                    endpoint=endpoint,
                    access_key=access_key,
                    secret_key=secret_key,
                    secure=secure
                )
            except Exception as e:
                logger.error(f"Failed to initialize MinIO client: {e}")
                return None
        
        return self._client
    
    def ensure_bucket_exists(self, bucket_name: Optional[str] = None) -> bool:
        """Ensure bucket exists, create if it doesn't."""
        if not self.client:
            return False
        
        bucket_name = bucket_name or self.bucket or current_app.config.get('OBJECT_STORE_BUCKET', 'freight-docs')
        
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
                logger.info(f"Created bucket: {bucket_name}")
            return True
        except S3Error as e:
            logger.error(f"Failed to ensure bucket exists: {e}")
            return False
    
    def upload_file(self, file_data: BinaryIO, object_name: str, 
                   content_type: Optional[str] = None, bucket_name: Optional[str] = None,
                   metadata: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Upload file to object storage."""
        if not self.client:
            return None
        
        bucket_name = bucket_name or self.bucket or current_app.config.get('OBJECT_STORE_BUCKET', 'freight-docs')
        
        if not self.ensure_bucket_exists(bucket_name):
            return None
        
        # Determine content type
        if not content_type:
            content_type, _ = mimetypes.guess_type(object_name)
            content_type = content_type or 'application/octet-stream'
        
        # Calculate file size and checksum
        file_data.seek(0, io.SEEK_END)
        file_size = file_data.tell()
        file_data.seek(0)
        
        # Calculate MD5 checksum
        file_content = file_data.read()
        file_data.seek(0)
        md5_hash = hashlib.md5(file_content).hexdigest()
        
        # Prepare metadata
        upload_metadata = metadata or {}
        upload_metadata.update({
            'uploaded_at': datetime.utcnow().isoformat(),
            'md5_checksum': md5_hash,
            'content_type': content_type
        })
        
        try:
            result = self.client.put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=content_type,
                metadata=upload_metadata
            )
            
            logger.info(f"Uploaded file: {object_name} to bucket: {bucket_name}")
            return f"{bucket_name}/{object_name}"
        
        except S3Error as e:
            logger.error(f"Failed to upload file {object_name}: {e}")
            return None
    
    def upload_from_bytes(self, data: bytes, object_name: str, 
                         content_type: Optional[str] = None, bucket_name: Optional[str] = None,
                         metadata: Optional[Dict[str, str]] = None) -> Optional[str]:
        """Upload data from bytes to object storage."""
        file_data = io.BytesIO(data)
        return self.upload_file(file_data, object_name, content_type, bucket_name, metadata)
    
    def download_file(self, object_name: str, bucket_name: Optional[str] = None) -> Optional[bytes]:
        """Download file from object storage."""
        if not self.client:
            return None
        
        bucket_name = bucket_name or self.bucket or current_app.config.get('OBJECT_STORE_BUCKET', 'freight-docs')
        
        try:
            response = self.client.get_object(bucket_name, object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        
        except S3Error as e:
            logger.error(f"Failed to download file {object_name}: {e}")
            return None
    
    def get_presigned_upload_url(self, object_name: str, expires: timedelta = timedelta(hours=1),
                                bucket_name: Optional[str] = None) -> Optional[str]:
        """Generate pre-signed URL for file upload."""
        if not self.client:
            return None
        
        bucket_name = bucket_name or self.bucket or current_app.config.get('OBJECT_STORE_BUCKET', 'freight-docs')
        
        if not self.ensure_bucket_exists(bucket_name):
            return None
        
        try:
            url = self.client.presigned_put_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=expires
            )
            logger.info(f"Generated pre-signed upload URL for: {object_name}")
            return url
        
        except S3Error as e:
            logger.error(f"Failed to generate pre-signed upload URL for {object_name}: {e}")
            return None
    
    def get_presigned_download_url(self, object_name: str, expires: timedelta = timedelta(hours=24),
                                  bucket_name: Optional[str] = None) -> Optional[str]:
        """Generate pre-signed URL for file download."""
        if not self.client:
            return None
        
        bucket_name = bucket_name or self.bucket or current_app.config.get('OBJECT_STORE_BUCKET', 'freight-docs')
        
        try:
            url = self.client.presigned_get_object(
                bucket_name=bucket_name,
                object_name=object_name,
                expires=expires
            )
            logger.info(f"Generated pre-signed download URL for: {object_name}")
            return url
        
        except S3Error as e:
            logger.error(f"Failed to generate pre-signed download URL for {object_name}: {e}")
            return None
    
    def delete_file(self, object_name: str, bucket_name: Optional[str] = None) -> bool:
        """Delete file from object storage."""
        if not self.client:
            return False
        
        bucket_name = bucket_name or self.bucket or current_app.config.get('OBJECT_STORE_BUCKET', 'freight-docs')
        
        try:
            self.client.remove_object(bucket_name, object_name)
            logger.info(f"Deleted file: {object_name} from bucket: {bucket_name}")
            return True
        
        except S3Error as e:
            logger.error(f"Failed to delete file {object_name}: {e}")
            return False
    
    def list_files(self, prefix: str = "", bucket_name: Optional[str] = None) -> list:
        """List files in object storage with optional prefix filter."""
        if not self.client:
            return []
        
        bucket_name = bucket_name or self.bucket or current_app.config.get('OBJECT_STORE_BUCKET', 'freight-docs')
        
        try:
            objects = self.client.list_objects(bucket_name, prefix=prefix, recursive=True)
            return [
                {
                    'name': obj.object_name,
                    'size': obj.size,
                    'last_modified': obj.last_modified.isoformat() if obj.last_modified else None,
                    'etag': obj.etag
                }
                for obj in objects
            ]
        
        except S3Error as e:
            logger.error(f"Failed to list files with prefix {prefix}: {e}")
            return []
    
    def get_file_info(self, object_name: str, bucket_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get file information and metadata."""
        if not self.client:
            return None
        
        bucket_name = bucket_name or self.bucket or current_app.config.get('OBJECT_STORE_BUCKET', 'freight-docs')
        
        try:
            stat = self.client.stat_object(bucket_name, object_name)
            return {
                'name': object_name,
                'size': stat.size,
                'last_modified': stat.last_modified.isoformat() if stat.last_modified else None,
                'etag': stat.etag,
                'content_type': stat.content_type,
                'metadata': stat.metadata
            }
        
        except S3Error as e:
            logger.error(f"Failed to get file info for {object_name}: {e}")
            return None
    
    def verify_checksum(self, object_name: str, expected_checksum: str, 
                       bucket_name: Optional[str] = None) -> bool:
        """Verify file checksum."""
        file_data = self.download_file(object_name, bucket_name)
        if not file_data:
            return False
        
        actual_checksum = hashlib.md5(file_data).hexdigest()
        return actual_checksum == expected_checksum
    
    def health_check(self) -> bool:
        """Check if object storage is accessible."""
        if not self.client:
            return False
        
        try:
            # Try to list buckets as a health check
            list(self.client.list_buckets())
            return True
        except Exception as e:
            logger.error(f"Object storage health check failed: {e}")
            return False


# Global storage instance
storage = ObjectStorageManager()


def init_storage(app):
    """Initialize object storage with Flask app."""
    storage.endpoint = app.config.get('OBJECT_STORE_ENDPOINT')
    storage.access_key = app.config.get('OBJECT_STORE_ACCESS_KEY')
    storage.secret_key = app.config.get('OBJECT_STORE_SECRET_KEY')
    storage.secure = app.config.get('OBJECT_STORE_SECURE', False)
    storage.bucket = app.config.get('OBJECT_STORE_BUCKET')
    
    # Test connection and ensure bucket exists
    if storage.health_check():
        storage.ensure_bucket_exists()
        logger.info("Object storage initialized successfully")
    else:
        logger.warning("Object storage connection failed during initialization")


def generate_object_path(category: str, identifier: str, filename: str) -> str:
    """Generate standardized object path."""
    now = datetime.utcnow()
    return f"{category}/{now.year:04d}/{now.month:02d}/{identifier}/{filename}"

