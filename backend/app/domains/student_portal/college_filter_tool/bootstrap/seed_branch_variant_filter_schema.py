import logging
from uuid import uuid4

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models import ExamPathCatalog, ExamPathFilterSchema

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


VARIANT_FILTER_KEY = "variant"
VARIANT_FILTER_LABEL = "Specialization"
BRANCH_FILTER_KEY = "branch"

TARGET_PATH_KEYS = {
    "kcet",
    "neet_ka",
    "mhcet_technical_be",
    "mhcet_technical_pharma",
    "jee_main",
    "jee_adv",
}


def seed_branch_variant_filter_schema(db: Session) -> None:
    """
    One-off additive metadata seed.

    Purpose:
    - add the governed backend filter `variant` after `branch`
    - preserve all existing path/filter rows
    - shift later sort_order values by +1 only when needed
    - remain idempotent across repeated runs
    """
    logger.info("Seeding branch -> variant filter schema rows...")

    target_paths = (
        db.query(ExamPathCatalog)
        .filter(
            ExamPathCatalog.path_key.in_(TARGET_PATH_KEYS),
            ExamPathCatalog.supports_branch.is_(True),
            ExamPathCatalog.active.is_(True),
        )
        .all()
    )

    logger.info("Found %s branch-enabled target paths.", len(target_paths))

    for path in target_paths:
        existing_variant = (
            db.query(ExamPathFilterSchema)
            .filter(
                ExamPathFilterSchema.path_id == path.path_id,
                ExamPathFilterSchema.filter_key == VARIANT_FILTER_KEY,
            )
            .one_or_none()
        )
        if existing_variant is not None:
            logger.info(
                "Skipping path_key=%s because variant filter already exists.",
                path.path_key,
            )
            continue

        branch_row = (
            db.query(ExamPathFilterSchema)
            .filter(
                ExamPathFilterSchema.path_id == path.path_id,
                ExamPathFilterSchema.filter_key == BRANCH_FILTER_KEY,
            )
            .one_or_none()
        )
        if branch_row is None:
            logger.warning(
                "Skipping path_key=%s because branch filter does not exist.",
                path.path_key,
            )
            continue

        variant_sort_order = int(branch_row.sort_order) + 1

        later_rows = (
            db.query(ExamPathFilterSchema)
            .filter(
                ExamPathFilterSchema.path_id == path.path_id,
                ExamPathFilterSchema.sort_order >= variant_sort_order,
            )
            .order_by(ExamPathFilterSchema.sort_order.desc())
            .all()
        )

        for row in later_rows:
            row.sort_order = int(row.sort_order) + 1

        variant_row = ExamPathFilterSchema(
            id=uuid4(),
            path_id=path.path_id,
            filter_key=VARIANT_FILTER_KEY,
            filter_label=VARIANT_FILTER_LABEL,
            control_type="AUTOCOMPLETE",
            option_source="BRANCH",
            is_required=False,
            is_visible=True,
            is_auto_fillable=False,
            sort_order=variant_sort_order,
            depends_on_filter_key=BRANCH_FILTER_KEY,
        )
        db.add(variant_row)

        logger.info(
            "Inserted variant filter for path_key=%s at sort_order=%s",
            path.path_key,
            variant_sort_order,
        )

    db.commit()
    logger.info("Completed seeding branch -> variant filter schema rows.")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed_branch_variant_filter_schema(db)
    except Exception:
        db.rollback()
        logger.exception("Failed seeding branch -> variant filter schema rows.")
        raise
    finally:
        db.close()