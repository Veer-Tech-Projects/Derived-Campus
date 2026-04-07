from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from redis.exceptions import RedisError

from ingestion.location_pipeline.tasks import redis_client
from app.domains.student_portal.college_filter_tool.tasks import (
    rebuild_college_filter_task,
)

logger = logging.getLogger(__name__)


class CollegeFilterRebuildMode(str, Enum):
    FULL_STACK = "FULL_STACK"
    SERVING_AND_READ_MODEL = "SERVING_AND_READ_MODEL"
    READ_MODEL_ONLY = "READ_MODEL_ONLY"


@dataclass(frozen=True)
class CollegeFilterRebuildRequest:
    reason: str
    rebuild_mode: CollegeFilterRebuildMode
    trigger_exam_code: Optional[str] = None
    created_by: Optional[str] = None


class CollegeFilterRebuildDispatcher:
    """
    Centralized async dispatcher for college-filter rebuild requests.

    Design rules:
    - Redis NX + TTL is used only for burst dedupe
    - this is NOT the batch orchestration mechanism for long-running ingest flows
    - cutoff batch processing must use explicit skip_rebuild controls
    - fail OPEN on Redis failure to preserve freshness
    """

    DEFAULT_TTL_SECONDS = 30

    def dispatch(self, request: CollegeFilterRebuildRequest) -> bool:
        """
        Returns:
            True  -> task was queued
            False -> equivalent request was debounced
        """
        debounce_key = self._build_debounce_key(request)

        try:
            acquired = redis_client.set(
                debounce_key,
                "1",
                ex=self.DEFAULT_TTL_SECONDS,
                nx=True,
            )
        except RedisError:
            logger.exception(
                "College-filter rebuild debounce failed for key=%s. "
                "Failing open and dispatching rebuild.",
                debounce_key,
            )
            acquired = True

        if not acquired:
            logger.info(
                "Debounced duplicate college-filter rebuild request "
                "mode=%s exam=%s reason=%s",
                request.rebuild_mode.value,
                request.trigger_exam_code,
                request.reason,
            )
            return False

        rebuild_college_filter_task.delay(
            rebuild_mode=request.rebuild_mode.value,
            trigger_exam_code=request.trigger_exam_code,
            trigger_reason=request.reason,
            created_by=request.created_by,
        )

        logger.info(
            "Queued college-filter rebuild "
            "mode=%s exam=%s reason=%s",
            request.rebuild_mode.value,
            request.trigger_exam_code,
            request.reason,
        )
        return True

    @staticmethod
    def _build_debounce_key(request: CollegeFilterRebuildRequest) -> str:
        exam_part = (request.trigger_exam_code or "GLOBAL").strip().lower()
        mode_part = request.rebuild_mode.value.strip().upper()
        return f"college_filter_rebuild:{mode_part}:{exam_part}"


college_filter_rebuild_dispatcher = CollegeFilterRebuildDispatcher()