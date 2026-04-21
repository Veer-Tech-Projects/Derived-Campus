from __future__ import annotations

import hashlib
import json
import logging
from decimal import Decimal
from typing import Any

from redis.exceptions import RedisError

from ingestion.location_pipeline.tasks import redis_client

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
        canonical_payload = {
            "path_id": str(path_id).strip(),
            "score": self._normalize_decimal(score),
            "filters": self._normalize_filters(filters),
            "sort_mode": str(sort_mode).strip().lower(),
        }

        canonical_json = json.dumps(
            canonical_payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

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

    @staticmethod
    def _normalize_filters(filters: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}

        for raw_key in sorted(filters.keys()):
            key = str(raw_key).strip()
            if not key:
                continue

            value = filters[raw_key]

            if value is None:
                continue

            if isinstance(value, str):
                stripped = value.strip()
                if not stripped:
                    continue
                normalized[key] = stripped
                continue

            if isinstance(value, Decimal):
                normalized[key] = CollegeFilterSearchSnapshotCacheService._normalize_decimal(
                    value
                )
                continue

            normalized[key] = value

        return normalized

    @staticmethod
    def _normalize_decimal(value: Decimal) -> str:
        text = format(value, "f")
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text or "0"


college_filter_search_snapshot_cache_service = CollegeFilterSearchSnapshotCacheService()