"""MinIO 스토리지 서비스"""

import io
import os

from loguru import logger
from minio import Minio
from minio.deleteobjects import DeleteObject
from minio.error import S3Error

from src.core.exceptions import AppException

_client: Minio | None = None


def _get_client() -> Minio:
    """MinIO 클라이언트 싱글톤 (lazy init)"""
    global _client
    if _client is None:
        endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
        access_key = os.getenv("MINIO_ACCESS_KEY", "aise")
        secret_key = os.getenv("MINIO_SECRET_KEY", "aise1234")
        _client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=False,  # 로컬 개발: TLS 비활성화
        )
        logger.info(f"MinIO 클라이언트 초기화: endpoint={endpoint}")
    return _client


def get_default_bucket() -> str:
    return os.getenv("MINIO_BUCKET", "aise-knowledge")


async def ensure_bucket(bucket: str) -> None:
    """버킷이 존재하지 않으면 생성"""
    client = _get_client()
    try:
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            logger.info(f"MinIO 버킷 생성: {bucket}")
    except S3Error as e:
        logger.error(f"MinIO 버킷 확인/생성 실패: {e}")
        raise AppException(500, f"스토리지 버킷 확인 실패: {e}")


async def upload_file(bucket: str, key: str, data: bytes, content_type: str) -> str:
    """파일 업로드 후 key 반환"""
    client = _get_client()
    try:
        await ensure_bucket(bucket)
        client.put_object(
            bucket,
            key,
            io.BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        logger.info(f"MinIO 업로드 완료: bucket={bucket}, key={key}, size={len(data)}")
        return key
    except S3Error as e:
        logger.error(f"MinIO 업로드 실패: {e}")
        raise AppException(500, f"파일 업로드 실패: {e}")


async def download_file(bucket: str, key: str) -> bytes:
    """파일 다운로드"""
    client = _get_client()
    try:
        response = client.get_object(bucket, key)
        data = response.read()
        response.close()
        response.release_conn()
        logger.debug(f"MinIO 다운로드 완료: bucket={bucket}, key={key}, size={len(data)}")
        return data
    except S3Error as e:
        logger.error(f"MinIO 다운로드 실패: {e}")
        raise AppException(500, f"파일 다운로드 실패: {e}")


async def delete_file(bucket: str, key: str) -> None:
    """파일 삭제"""
    client = _get_client()
    try:
        client.remove_object(bucket, key)
        logger.info(f"MinIO 삭제 완료: bucket={bucket}, key={key}")
    except S3Error as e:
        logger.error(f"MinIO 삭제 실패: {e}")
        raise AppException(500, f"파일 삭제 실패: {e}")


async def delete_prefix(bucket: str, prefix: str) -> int:
    """주어진 prefix 로 시작하는 모든 객체 일괄 삭제. 삭제된 개수 반환.

    프로젝트 hard delete 시 `{project_id}/` prefix 로 등록된 모든 파일을 정리하기
    위한 헬퍼. MinIO/S3 의 `remove_objects` 는 batch 삭제를 지원해 페이지네이션 +
    list/delete 한 번씩으로 큰 prefix 도 처리 가능.
    """
    client = _get_client()
    try:
        objects = client.list_objects(bucket, prefix=prefix, recursive=True)
        keys = [obj.object_name for obj in objects if obj.object_name]
        if not keys:
            logger.info(
                f"MinIO prefix 삭제 — 대상 없음: bucket={bucket}, prefix={prefix}"
            )
            return 0
        delete_targets = [DeleteObject(k) for k in keys]
        errors = list(client.remove_objects(bucket, delete_targets))
        if errors:
            for err in errors:
                logger.error(f"MinIO prefix 삭제 일부 실패: {err}")
            raise AppException(
                500,
                f"파일 일괄 삭제 부분 실패: {len(errors)}건 / 총 {len(keys)}건",
            )
        logger.info(
            f"MinIO prefix 삭제 완료: bucket={bucket}, prefix={prefix}, count={len(keys)}"
        )
        return len(keys)
    except S3Error as e:
        logger.error(f"MinIO prefix 삭제 실패: {e}")
        raise AppException(500, f"파일 일괄 삭제 실패: {e}")
