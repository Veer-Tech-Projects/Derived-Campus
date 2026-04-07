from __future__ import annotations

import logging
from enum import Enum
from typing import Any

from celery import shared_task

from app.database import SessionLocal
from app.domains.student_portal.college_filter_tool.bootstrap.seed_college_filter_metadata import (
    seed_college_filter_metadata,
)
from app.domains.student_portal.college_filter_tool.builders.projection_stats_builder import (
    ProjectionStatsBuilder,
)
from app.domains.student_portal.college_filter_tool.builders.search_read_model_builder import (
    SearchReadModelBuilder,
)
from app.domains.student_portal.college_filter_tool.builders.serving_map_builder import (
    ServingMapBuilder,
)

logger = logging.getLogger(__name__)


class CollegeFilterRebuildMode(str, Enum):
    FULL_STACK = "FULL_STACK"
    SERVING_AND_READ_MODEL = "SERVING_AND_READ_MODEL"
    READ_MODEL_ONLY = "READ_MODEL_ONLY"


def execute_college_filter_rebuild(
    *,
    rebuild_mode: str,
    trigger_exam_code: str | None = None,
    trigger_reason: str = "MANUAL",
    created_by: str | None = None,
) -> dict[str, Any]:
    """
    Pure implementation function used by all task entrypoints.

    Keeps logic centralized and avoids brittle task-to-task invocation patterns.
    """
    db = SessionLocal()
    try:
        mode = CollegeFilterRebuildMode(rebuild_mode)

        serving_map_result = None
        projection_result = None
        read_model_result = None

        if mode in (
            CollegeFilterRebuildMode.FULL_STACK,
            CollegeFilterRebuildMode.SERVING_AND_READ_MODEL,
        ):
            serving_map_result = ServingMapBuilder(db).build_for_scope(
                trigger_exam_code=trigger_exam_code
            )

        if mode == CollegeFilterRebuildMode.FULL_STACK:
            projection_result = ProjectionStatsBuilder(db).build_for_scope(
                trigger_exam_code=trigger_exam_code
            )

        read_model_result = SearchReadModelBuilder(db).build_for_scope(
            trigger_reason=trigger_reason,
            trigger_exam_code=trigger_exam_code,
            policy_id=None,
            created_by=created_by,
        )

        db.commit()

        return {
            "rebuild_mode": mode.value,
            "trigger_exam_code": trigger_exam_code,
            "trigger_reason": trigger_reason,
            "serving_map_result": serving_map_result,
            "projection_result": projection_result,
            "read_model_result": read_model_result,
        }

    except Exception:
        db.rollback()
        logger.exception(
            "Failed execute_college_filter_rebuild mode=%s exam=%s reason=%s",
            rebuild_mode,
            trigger_exam_code,
            trigger_reason,
        )
        raise
    finally:
        db.close()


@shared_task(
    name="student_portal.college_filter_tool.tasks.seed_college_filter_metadata_task",
    bind=True,
    queue="ingestion_queue",
)
def seed_college_filter_metadata_task(self):
    db = SessionLocal()
    try:
        seed_college_filter_metadata(db)
        return "SUCCESS"
    except Exception:
        db.rollback()
        logger.exception("Failed seeding college filter metadata.")
        raise
    finally:
        db.close()


@shared_task(
    name="student_portal.college_filter_tool.tasks.rebuild_college_filter_task",
    bind=True,
    queue="ingestion_queue",
)
def rebuild_college_filter_task(
    self,
    rebuild_mode: str = "FULL_STACK",
    trigger_exam_code: str | None = None,
    trigger_reason: str = "MANUAL",
    created_by: str | None = None,
):
    return execute_college_filter_rebuild(
        rebuild_mode=rebuild_mode,
        trigger_exam_code=trigger_exam_code,
        trigger_reason=trigger_reason,
        created_by=created_by,
    )


@shared_task(
    name="student_portal.college_filter_tool.tasks.build_college_filter_read_model_task",
    bind=True,
    queue="ingestion_queue",
)
def build_college_filter_read_model_task(
    self,
    trigger_exam_code: str | None = None,
    trigger_reason: str = "MANUAL",
    created_by: str | None = None,
):
    """
    Backward-compatible legacy task surface.

    Existing callers expecting the old full-stack behavior continue to work.
    """
    return execute_college_filter_rebuild(
        rebuild_mode=CollegeFilterRebuildMode.FULL_STACK.value,
        trigger_exam_code=trigger_exam_code,
        trigger_reason=trigger_reason,
        created_by=created_by,
    )