import logging
from typing import Iterable

from sqlalchemy.orm import Session

from app.models import (
    ExamPathCatalog,
    ExamPathFilterSchema,
    ProbabilityPolicyConfig,
    FilterControlTypeEnum,
    OptionSourceEnum,
)

logger = logging.getLogger(__name__)


def _upsert_exam_path(
    db: Session,
    *,
    path_key: str,
    visible_label: str,
    exam_family: str,
    resolved_exam_code: str | None,
    education_type: str | None,
    selection_type: str | None,
    metric_type: str,
    expected_max_rounds: int,
    supports_branch: bool,
    supports_course_relaxation: bool,
    supports_location_filter: bool,
    supports_opening_rank: bool,
    display_order: int,
    parent_path_id=None,
) -> ExamPathCatalog:
    row = db.query(ExamPathCatalog).filter(ExamPathCatalog.path_key == path_key).one_or_none()
    if row is None:
        row = ExamPathCatalog(path_key=path_key)

    row.parent_path_id = parent_path_id
    row.visible_label = visible_label
    row.exam_family = exam_family
    row.resolved_exam_code = resolved_exam_code
    row.education_type = education_type
    row.selection_type = selection_type
    row.metric_type = metric_type
    row.expected_max_rounds = expected_max_rounds
    row.supports_branch = supports_branch
    row.supports_course_relaxation = supports_course_relaxation
    row.supports_location_filter = supports_location_filter
    row.supports_opening_rank = supports_opening_rank
    row.active = True
    row.display_order = display_order

    db.add(row)
    db.flush()
    return row


def _replace_filter_schema(
    db: Session,
    *,
    path_id,
    schema_rows: Iterable[dict],
) -> None:
    db.query(ExamPathFilterSchema).filter(ExamPathFilterSchema.path_id == path_id).delete()

    for item in schema_rows:
        db.add(
            ExamPathFilterSchema(
                path_id=path_id,
                filter_key=item["filter_key"],
                filter_label=item["filter_label"],
                control_type=item["control_type"],
                option_source=item["option_source"],
                is_required=item["is_required"],
                is_visible=item["is_visible"],
                is_auto_fillable=item["is_auto_fillable"],
                sort_order=item["sort_order"],
                depends_on_filter_key=item.get("depends_on_filter_key"),
            )
        )


def seed_exam_paths_and_filter_schema(db: Session) -> None:
    logger.info("Seeding college filter exam paths and filter schema...")

    # Visible root / direct paths
    kcet = _upsert_exam_path(
        db,
        path_key="kcet",
        visible_label="KCET",
        exam_family="KCET",
        resolved_exam_code="KCET",
        education_type=None,
        selection_type=None,
        metric_type="rank",
        expected_max_rounds=3,
        supports_branch=True,
        supports_course_relaxation=True,
        supports_location_filter=True,
        supports_opening_rank=False,
        display_order=1,
    )

    neet_ka = _upsert_exam_path(
        db,
        path_key="neet_ka",
        visible_label="NEET Karnataka",
        exam_family="NEET",
        resolved_exam_code="NEET_KA",
        education_type=None,
        selection_type=None,
        metric_type="rank",
        expected_max_rounds=3,
        supports_branch=True,
        supports_course_relaxation=True,
        supports_location_filter=True,
        supports_opening_rank=False,
        display_order=2,
    )

    mhcet_root = _upsert_exam_path(
        db,
        path_key="mhcet",
        visible_label="Maharashtra CET",
        exam_family="MHCET",
        resolved_exam_code=None,
        education_type=None,
        selection_type=None,
        metric_type="rank",
        expected_max_rounds=3,
        supports_branch=False,
        supports_course_relaxation=False,
        supports_location_filter=False,
        supports_opening_rank=False,
        display_order=3,
    )

    mhcet_technical_be = _upsert_exam_path(
        db,
        path_key="mhcet_technical_be",
        visible_label="B.E./B.Tech",
        exam_family="MHCET",
        resolved_exam_code="MHTCET_BE",
        education_type="Technical Education",
        selection_type="B.E./B.Tech",
        metric_type="percentile",
        expected_max_rounds=3,
        supports_branch=True,
        supports_course_relaxation=True,
        supports_location_filter=True,
        supports_opening_rank=False,
        display_order=31,
        parent_path_id=mhcet_root.path_id,
    )

    mhcet_technical_pharma = _upsert_exam_path(
        db,
        path_key="mhcet_technical_pharma",
        visible_label="B.Pharmacy / Pharm D",
        exam_family="MHCET",
        resolved_exam_code="MHTCET_PHARMA",
        education_type="Technical Education",
        selection_type="B.Pharmacy / Pharm D",
        metric_type="percentile",
        expected_max_rounds=3,
        supports_branch=True,
        supports_course_relaxation=True,
        supports_location_filter=True,
        supports_opening_rank=False,
        display_order=32,
        parent_path_id=mhcet_root.path_id,
    )

    mhcet_medical_neetug = _upsert_exam_path(
        db,
        path_key="mhcet_medical_neetug",
        visible_label="NEET-UG",
        exam_family="MHCET",
        resolved_exam_code="MH_NEET_UG",
        education_type="Medical Education",
        selection_type="NEET-UG",
        metric_type="rank",
        expected_max_rounds=3,
        supports_branch=False,
        supports_course_relaxation=True,
        supports_location_filter=True,
        supports_opening_rank=False,
        display_order=33,
        parent_path_id=mhcet_root.path_id,
    )

    mhcet_medical_nursing = _upsert_exam_path(
        db,
        path_key="mhcet_medical_nursing",
        visible_label="B.Sc. Nursing",
        exam_family="MHCET",
        resolved_exam_code="MH_NURSING",
        education_type="Medical Education",
        selection_type="B.Sc. Nursing",
        metric_type="rank",
        expected_max_rounds=3,
        supports_branch=False,
        supports_course_relaxation=False,
        supports_location_filter=True,
        supports_opening_rank=False,
        display_order=34,
        parent_path_id=mhcet_root.path_id,
    )

    mhcet_medical_ayush = _upsert_exam_path(
        db,
        path_key="mhcet_medical_ayush_aiq",
        visible_label="AIQ (15%) for AYUSH Courses",
        exam_family="MHCET",
        resolved_exam_code="MH_AYUSH_AIQ",
        education_type="Medical Education",
        selection_type="AIQ (15%) for AYUSH Courses",
        metric_type="rank",
        expected_max_rounds=3,
        supports_branch=False,
        supports_course_relaxation=True,
        supports_location_filter=True,
        supports_opening_rank=False,
        display_order=35,
        parent_path_id=mhcet_root.path_id,
    )

    jee_main = _upsert_exam_path(
        db,
        path_key="jee_main",
        visible_label="JEE Main",
        exam_family="JOSAA",
        resolved_exam_code="JEE_MAIN",
        education_type=None,
        selection_type=None,
        metric_type="rank",
        expected_max_rounds=6,
        supports_branch=True,
        supports_course_relaxation=True,
        supports_location_filter=True,
        supports_opening_rank=True,
        display_order=4,
    )

    jee_adv = _upsert_exam_path(
        db,
        path_key="jee_adv",
        visible_label="JEE Advanced",
        exam_family="JOSAA",
        resolved_exam_code="JEE_ADV",
        education_type=None,
        selection_type=None,
        metric_type="rank",
        expected_max_rounds=6,
        supports_branch=True,
        supports_course_relaxation=True,
        supports_location_filter=True,
        supports_opening_rank=True,
        display_order=5,
    )

    path_schemas = {
        # Has course type + branch => course type required, branch optional
        "kcet": [
            {
                "filter_key": "score",
                "filter_label": "Rank",
                "control_type": FilterControlTypeEnum.NUMBER_INPUT,
                "option_source": OptionSourceEnum.STATIC,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 1,
            },
            {
                "filter_key": "category",
                "filter_label": "Category",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 2,
            },
            {
                "filter_key": "course_type",
                "filter_label": "Course Type",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 3,
            },
            {
                "filter_key": "location_type",
                "filter_label": "Location Type",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 4,
            },
            {
                "filter_key": "branch",
                "filter_label": "Branch",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.BRANCH,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 5,
                "depends_on_filter_key": "course_type",
            },
            {
                "filter_key": "state_code",
                "filter_label": "State",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 6,
            },
            {
                "filter_key": "district",
                "filter_label": "District",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 7,
            },
            {
                "filter_key": "pincode",
                "filter_label": "Pincode",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 8,
            },
        ],
        # Has course type + branch => course type required, branch optional
        "neet_ka": [
            {
                "filter_key": "score",
                "filter_label": "Rank",
                "control_type": FilterControlTypeEnum.NUMBER_INPUT,
                "option_source": OptionSourceEnum.STATIC,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 1,
            },
            {
                "filter_key": "category",
                "filter_label": "Category",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 2,
            },
            {
                "filter_key": "course_type",
                "filter_label": "Course Type",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 3,
            },
            {
                "filter_key": "branch",
                "filter_label": "Branch",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.BRANCH,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 4,
                "depends_on_filter_key": "course_type",
            },
            {
                "filter_key": "state_code",
                "filter_label": "State",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 5,
            },
            {
                "filter_key": "district",
                "filter_label": "District",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 6,
            },
            {
                "filter_key": "pincode",
                "filter_label": "Pincode",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 7,
            },
        ],
        # Branch only => branch required
        "mhcet_technical_be": [
            {
                "filter_key": "score",
                "filter_label": "Percentile",
                "control_type": FilterControlTypeEnum.NUMBER_INPUT,
                "option_source": OptionSourceEnum.STATIC,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 1,
            },
            {
                "filter_key": "category",
                "filter_label": "Category",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 2,
            },
            {
                "filter_key": "location_type",
                "filter_label": "Quota / Seat Type",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 3,
            },
            {
                "filter_key": "reservation_type",
                "filter_label": "Reservation Type",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 4,
            },
            {
                "filter_key": "gender",
                "filter_label": "Gender",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 5,
            },
            {
                "filter_key": "branch",
                "filter_label": "Branch",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.BRANCH,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 6,
            },
            {
                "filter_key": "state_code",
                "filter_label": "State",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 7,
            },
            {
                "filter_key": "district",
                "filter_label": "District",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 8,
            },
            {
                "filter_key": "pincode",
                "filter_label": "Pincode",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 9,
            },
        ],
        # Branch only => branch required
        "mhcet_technical_pharma": [
            {
                "filter_key": "score",
                "filter_label": "Percentile",
                "control_type": FilterControlTypeEnum.NUMBER_INPUT,
                "option_source": OptionSourceEnum.STATIC,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 1,
            },
            {
                "filter_key": "category",
                "filter_label": "Category",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 2,
            },
            {
                "filter_key": "location_type",
                "filter_label": "Quota / Seat Type",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 3,
            },
            {
                "filter_key": "reservation_type",
                "filter_label": "Reservation Type",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 4,
            },
            {
                "filter_key": "gender",
                "filter_label": "Gender",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 5,
            },
            {
                "filter_key": "branch",
                "filter_label": "Branch",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.BRANCH,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 6,
            },
            {
                "filter_key": "state_code",
                "filter_label": "State",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 7,
            },
            {
                "filter_key": "district",
                "filter_label": "District",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 8,
            },
            {
                "filter_key": "pincode",
                "filter_label": "Pincode",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 9,
            },
        ],
        # Course type only => course type required
        "mhcet_medical_neetug": [
            {
                "filter_key": "score",
                "filter_label": "Rank",
                "control_type": FilterControlTypeEnum.NUMBER_INPUT,
                "option_source": OptionSourceEnum.STATIC,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 1,
            },
            {
                "filter_key": "category",
                "filter_label": "Category",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 2,
            },
            {
                "filter_key": "course_type",
                "filter_label": "Course Type",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 3,
            },
            {
                "filter_key": "reservation_type",
                "filter_label": "Reservation Type",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 4,
            },
            {
                "filter_key": "state_code",
                "filter_label": "State",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 5,
            },
            {
                "filter_key": "district",
                "filter_label": "District",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 6,
            },
            {
                "filter_key": "pincode",
                "filter_label": "Pincode",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 7,
            },
        ],
        # Course type only => required; likely single governed option but keep metadata consistent
        "mhcet_medical_nursing": [
            {
                "filter_key": "score",
                "filter_label": "Rank",
                "control_type": FilterControlTypeEnum.NUMBER_INPUT,
                "option_source": OptionSourceEnum.STATIC,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 1,
            },
            {
                "filter_key": "category",
                "filter_label": "Category",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 2,
            },
            {
                "filter_key": "course_type",
                "filter_label": "Course Type",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 3,
            },
            {
                "filter_key": "reservation_type",
                "filter_label": "Reservation Type",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 4,
            },
            {
                "filter_key": "state_code",
                "filter_label": "State",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 5,
            },
            {
                "filter_key": "district",
                "filter_label": "District",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 6,
            },
            {
                "filter_key": "pincode",
                "filter_label": "Pincode",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 7,
            },
        ],
        # Course type only => course type required
        "mhcet_medical_ayush_aiq": [
            {
                "filter_key": "score",
                "filter_label": "Rank",
                "control_type": FilterControlTypeEnum.NUMBER_INPUT,
                "option_source": OptionSourceEnum.STATIC,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 1,
            },
            {
                "filter_key": "category",
                "filter_label": "Category",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 2,
            },
            {
                "filter_key": "course_type",
                "filter_label": "Course Type",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 3,
            },
            {
                "filter_key": "reservation_type",
                "filter_label": "Reservation Type",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 4,
            },
            {
                "filter_key": "state_code",
                "filter_label": "State",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 5,
            },
            {
                "filter_key": "district",
                "filter_label": "District",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 6,
            },
            {
                "filter_key": "pincode",
                "filter_label": "Pincode",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 7,
            },
        ],
        # Branch only => branch required, label = Academic Program
        "jee_main": [
            {
                "filter_key": "score",
                "filter_label": "Rank",
                "control_type": FilterControlTypeEnum.NUMBER_INPUT,
                "option_source": OptionSourceEnum.STATIC,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 1,
            },
            {
                "filter_key": "category",
                "filter_label": "Category",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 2,
            },
            {
                "filter_key": "institute_type",
                "filter_label": "Institute Type",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 3,
            },
            {
                "filter_key": "reservation_type",
                "filter_label": "Reservation Type",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 4,
            },
            {
                "filter_key": "is_pwd",
                "filter_label": "PwD",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 5,
            },
            {
                "filter_key": "gender",
                "filter_label": "Gender",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 6,
            },
            {
                "filter_key": "branch",
                "filter_label": "Academic Program",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.BRANCH,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 7,
            },
            {
                "filter_key": "state_code",
                "filter_label": "State",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 8,
            },
            {
                "filter_key": "district",
                "filter_label": "District",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 9,
            },
            {
                "filter_key": "pincode",
                "filter_label": "Pincode",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 10,
            },
        ],
        # Branch only => branch required, institute type fixed later by builder/UI, label = Academic Program
        "jee_adv": [
            {
                "filter_key": "score",
                "filter_label": "Rank",
                "control_type": FilterControlTypeEnum.NUMBER_INPUT,
                "option_source": OptionSourceEnum.STATIC,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 1,
            },
            {
                "filter_key": "category",
                "filter_label": "Category",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 2,
            },
            {
                "filter_key": "institute_type",
                "filter_label": "Institute Type",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 3,
            },
            {
                "filter_key": "reservation_type",
                "filter_label": "Reservation Type",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 4,
            },
            {
                "filter_key": "is_pwd",
                "filter_label": "PwD",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 5,
            },
            {
                "filter_key": "gender",
                "filter_label": "Gender",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.SERVING_MAP,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 6,
            },
            {
                "filter_key": "branch",
                "filter_label": "Academic Program",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.BRANCH,
                "is_required": True,
                "is_visible": True,
                "is_auto_fillable": False,
                "sort_order": 7,
            },
            {
                "filter_key": "state_code",
                "filter_label": "State",
                "control_type": FilterControlTypeEnum.SELECT,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 8,
            },
            {
                "filter_key": "district",
                "filter_label": "District",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 9,
            },
            {
                "filter_key": "pincode",
                "filter_label": "Pincode",
                "control_type": FilterControlTypeEnum.AUTOCOMPLETE,
                "option_source": OptionSourceEnum.LOCATION,
                "is_required": False,
                "is_visible": True,
                "is_auto_fillable": True,
                "sort_order": 10,
            },
        ],
    }

    path_map = {
        "kcet": kcet.path_id,
        "neet_ka": neet_ka.path_id,
        "mhcet_technical_be": mhcet_technical_be.path_id,
        "mhcet_technical_pharma": mhcet_technical_pharma.path_id,
        "mhcet_medical_neetug": mhcet_medical_neetug.path_id,
        "mhcet_medical_nursing": mhcet_medical_nursing.path_id,
        "mhcet_medical_ayush_aiq": mhcet_medical_ayush.path_id,
        "jee_main": jee_main.path_id,
        "jee_adv": jee_adv.path_id,
    }

    for path_key, rows in path_schemas.items():
        _replace_filter_schema(db, path_id=path_map[path_key], schema_rows=rows)

    logger.info("Seeded exam paths and filter schema.")


def seed_probability_policy(db: Session) -> None:
    logger.info("Seeding default probability policy...")

    row = (
        db.query(ProbabilityPolicyConfig)
        .filter(ProbabilityPolicyConfig.policy_key == "default_v1")
        .one_or_none()
    )

    if row is None:
        row = ProbabilityPolicyConfig(policy_key="default_v1")

    row.path_id = None
    row.is_active = True
    row.version_no = 1

    row.weight_round_evidence = 0.45
    row.weight_round_stability = 0.35
    row.weight_current_year_presence = 0.20

    row.weight_margin = 0.80
    row.weight_confidence = 0.20

    row.probability_base = 50.0
    row.probability_multiplier = 320.0
    row.probability_min = 5.0
    row.probability_max = 97.0

    row.safe_min_margin = 0.10
    row.safe_min_confidence = 0.55

    row.moderate_min_margin = 0.03
    row.moderate_min_confidence = 0.40

    row.hard_min_margin = -0.06
    row.hard_min_confidence = 0.25

    row.suggested_min_margin = 0.08
    row.suggested_min_confidence = 0.45
    row.suggested_score_penalty = 0.03
    row.suggested_probability_penalty = 5.0

    row.cold_start_probability_cap = 72.0
    row.cold_start_safe_min_margin = 0.14
    row.cold_start_safe_min_confidence = 0.50

    row.notes = "Default V1 current-round probability policy."

    db.add(row)
    db.flush()

    logger.info("Seeded default probability policy.")


def seed_college_filter_metadata(db: Session) -> None:
    seed_exam_paths_and_filter_schema(db)
    seed_probability_policy(db)
    db.commit()