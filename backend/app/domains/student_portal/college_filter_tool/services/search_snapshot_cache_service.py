from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from redis.exceptions import RedisError

from ingestion.location_pipeline.tasks import redis_client
from app.domains.student_portal.college_filter_tool.services.college_filter_search_fingerprint_service import (
    college_filter_search_fingerprint_service,
)

logger = logging.getLogger(__name__)


class CollegeFilterSearchSnapshotCacheService:
    """
    Best-effort Redis-backed snapshot cache for identical college-filter searches.

    Design rules:
    - cache is advisory only; correctness must never depend on Redis
    - page-by-band is intentionally excluded from the fingerprint
    - fail open on Redis read/write errors
    - payloads are stored as serialized JSON strings
    """

    KEY_PREFIX = "college_filter:search_snapshot"
    TTL_SECONDS = 180

    def build_fingerprint(
        self,
        *,
        path_id: str,
        score: Decimal,
        filters: dict[str, Any],
        sort_mode: str,
    ) -> str:
        return college_filter_search_fingerprint_service.build_fingerprint(
            path_id=path_id,
            score=score,
            filters=filters,
            sort_mode=sort_mode,
        )

    def load_snapshot_json(self, *, fingerprint: str) -> str | None:
        cache_key = self._build_cache_key(fingerprint)

        try:
            payload = redis_client.get(cache_key)
        except RedisError:
            logger.exception(
                "College-filter snapshot cache read failed for fingerprint=%s",
                fingerprint,
            )
            return None

        if payload is None:
            return None

        if isinstance(payload, bytes):
            return payload.decode("utf-8")

        return str(payload)

    def store_snapshot_json(
        self,
        *,
        fingerprint: str,
        payload_json: str,
    ) -> None:
        cache_key = self._build_cache_key(fingerprint)

        try:
            redis_client.set(
                cache_key,
                payload_json,
                ex=self.TTL_SECONDS,
            )
        except RedisError:
            logger.exception(
                "College-filter snapshot cache write failed for fingerprint=%s",
                fingerprint,
            )

    @classmethod
    def _build_cache_key(cls, fingerprint: str) -> str:
        return f"{cls.KEY_PREFIX}:{fingerprint}"




college_filter_search_snapshot_cache_service = CollegeFilterSearchSnapshotCacheService()