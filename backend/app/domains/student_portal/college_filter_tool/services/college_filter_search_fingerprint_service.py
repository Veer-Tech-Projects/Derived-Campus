from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from typing import Any


class CollegeFilterSearchFingerprintService:
    """
    Canonical fingerprint builder for College Filter search identity.

    Design rules:
    - backend is source of truth for billable search identity
    - page/pagination state must NOT affect fingerprint
    - canonicalization must be stable across retries/reopens
    - correctness must not depend on Redis
    """

    def build_fingerprint(
        self,
        *,
        path_id: str,
        score: Decimal,
        filters: dict[str, Any],
        sort_mode: str,
    ) -> str:
        snapshot = self.build_request_snapshot(
            path_id=path_id,
            score=score,
            filters=filters,
            sort_mode=sort_mode,
        )
        canonical_json = json.dumps(
            snapshot,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    def build_request_snapshot(
        self,
        *,
        path_id: str,
        score: Decimal,
        filters: dict[str, Any],
        sort_mode: str,
    ) -> dict[str, Any]:
        return {
            "path_id": str(path_id).strip(),
            "score": self._normalize_decimal(score),
            "filters": self._normalize_filters(filters),
            "sort_mode": str(sort_mode).strip().lower(),
        }

    def _normalize_filters(self, filters: dict[str, Any]) -> dict[str, str]:
        normalized: dict[str, str] = {}

        for raw_key in sorted(filters.keys()):
            key = str(raw_key).strip()
            if not key:
                continue

            raw_value = filters[raw_key]
            value = self._normalize_scalar(raw_value)
            if value == "":
                continue

            normalized[key] = value

        return normalized

    @staticmethod
    def _normalize_decimal(value: Decimal) -> str:
        return format(Decimal(value).normalize(), "f")

    @staticmethod
    def _normalize_scalar(value: Any) -> str:
        if value is None:
            return ""

        if isinstance(value, Decimal):
            return format(value.normalize(), "f")

        return str(value).strip()


college_filter_search_fingerprint_service = CollegeFilterSearchFingerprintService()