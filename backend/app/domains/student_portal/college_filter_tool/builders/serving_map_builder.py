import logging
from collections import defaultdict

from sqlalchemy.orm import Session

from app.models import (
    ExamBranchAlias,
    ExamBranchRegistry,
    ExamPathCatalog,
    ExamPathFilterSchema,
    ExamPathOptionMap,
    ExamProgramServingMap,
    ExamSeatFilterServingMap,
    MappingStatusEnum,
    SeatBucketTaxonomy,
    CutoffOutcome,
)

logger = logging.getLogger(__name__)


class ServingMapBuilder:
    TAXONOMY_COURSE_TYPE_PATH_KEYS = {
        "kcet",
        "neet_ka",
        "mhcet_medical_neetug",
        "mhcet_medical_nursing",
        "mhcet_medical_ayush_aiq",
    }

    def __init__(self, db: Session):
        self.db = db

    def build_for_scope(self, trigger_exam_code: str | None = None) -> dict:
        logger.info(
            "Starting ServingMapBuilder for trigger_exam_code=%s",
            trigger_exam_code,
        )

        active_paths = (
            self.db.query(ExamPathCatalog)
            .filter(ExamPathCatalog.active.is_(True))
            .all()
        )

        if trigger_exam_code:
            trigger_exam_code_norm = str(trigger_exam_code).strip().upper()
            scoped_paths = [
                p for p in active_paths
                if (p.resolved_exam_code or "").upper() == trigger_exam_code_norm
            ]
        else:
            scoped_paths = active_paths

        path_filter_keys = self._load_path_filter_keys()
        self._refresh_exam_path_option_map(scoped_paths)
        seat_rows_written = self._refresh_exam_seat_filter_serving_map(
            scoped_paths=scoped_paths,
            path_filter_keys=path_filter_keys,
        )
        branch_rows_written = self._refresh_exam_program_serving_map(
            scoped_paths=scoped_paths,
            path_filter_keys=path_filter_keys,
        )

        option_rows = (
            self.db.query(ExamPathOptionMap)
            .filter(ExamPathOptionMap.active.is_(True))
            .count()
        )

        return {
            "trigger_exam_code": trigger_exam_code,
            "exam_path_option_map_rows": option_rows,
            "exam_seat_filter_serving_map_rows": seat_rows_written,
            "course_type_serving_candidates": 0,
            "branch_serving_candidates": branch_rows_written,
        }

    def _load_path_filter_keys(self) -> dict[str, set[str]]:
        path_filter_keys: dict[str, set[str]] = defaultdict(set)
        filter_rows = self.db.query(ExamPathFilterSchema).all()
        for row in filter_rows:
            path_filter_keys[str(row.path_id)].add(row.filter_key)
        return path_filter_keys

    def _refresh_exam_path_option_map(self, scoped_paths: list[ExamPathCatalog]) -> None:
        scoped_path_ids = [p.path_id for p in scoped_paths]
        if not scoped_path_ids:
            return

        (
            self.db.query(ExamPathOptionMap)
            .filter(ExamPathOptionMap.path_id.in_(scoped_path_ids))
            .delete(synchronize_session=False)
        )

        for path in scoped_paths:
            if not path.resolved_exam_code:
                continue

            self.db.add(
                ExamPathOptionMap(
                    path_id=path.path_id,
                    exam_code=path.resolved_exam_code,
                    course_type_value=None,
                    option_label=path.visible_label,
                    active=True,
                )
            )

        self.db.flush()

    def _refresh_exam_seat_filter_serving_map(
        self,
        *,
        scoped_paths: list[ExamPathCatalog],
        path_filter_keys: dict[str, set[str]],
    ) -> int:
        scoped_path_ids = [p.path_id for p in scoped_paths]
        if not scoped_path_ids:
            return 0

        (
            self.db.query(ExamSeatFilterServingMap)
            .filter(ExamSeatFilterServingMap.path_id.in_(scoped_path_ids))
            .delete(synchronize_session=False)
        )

        rows_written = 0

        for path in scoped_paths:
            if not path.resolved_exam_code:
                continue

            filter_keys = path_filter_keys.get(str(path.path_id), set())
            taxonomy_rows = (
                self.db.query(SeatBucketTaxonomy)
                .filter(SeatBucketTaxonomy.exam_code == path.resolved_exam_code)
                .all()
            )

            # Visible-option dedup only
            seen_options = set()

            if taxonomy_rows:
                for tax in taxonomy_rows:
                    attrs = tax.attributes or {}

                    # CATEGORY (primary from normalized taxonomy column)
                    if "category" in filter_keys and tax.category_name:
                        rows_written += self._add_option_if_new(
                            seen_options,
                            path_id=path.path_id,
                            filter_key="category",
                            option_key=self._normalize_option_key(tax.category_name),
                            option_label=self._normalize_category_label(tax.category_name),
                            category_name=tax.category_name,
                            is_reserved=tax.is_reserved,
                            course_type=tax.course_type,
                            location_type=tax.location_type,
                            reservation_type=tax.reservation_type,
                            seat_bucket_code=None,
                            display_meta={},
                        )

                    # LOCATION TYPE (primary from taxonomy column, secondary JSONB only for label expansion)
                    if "location_type" in filter_keys and tax.location_type:
                        rows_written += self._add_option_if_new(
                            seen_options,
                            path_id=path.path_id,
                            filter_key="location_type",
                            option_key=self._normalize_option_key(tax.location_type),
                            option_label=self._normalize_location_type_label(
                                path.path_key,
                                tax.location_type,
                                attrs,
                            ),
                            category_name=tax.category_name,
                            is_reserved=tax.is_reserved,
                            course_type=tax.course_type,
                            location_type=tax.location_type,
                            reservation_type=tax.reservation_type,
                            seat_bucket_code=None,
                            display_meta={"raw_location_type": tax.location_type},
                        )

                    # RESERVATION TYPE (primary from taxonomy column)
                    if "reservation_type" in filter_keys and tax.reservation_type:
                        rows_written += self._add_option_if_new(
                            seen_options,
                            path_id=path.path_id,
                            filter_key="reservation_type",
                            option_key=self._normalize_option_key(tax.reservation_type),
                            option_label=self._normalize_reservation_type_label(
                                tax.reservation_type
                            ),
                            category_name=tax.category_name,
                            is_reserved=tax.is_reserved,
                            course_type=tax.course_type,
                            location_type=tax.location_type,
                            reservation_type=tax.reservation_type,
                            seat_bucket_code=None,
                            display_meta={"raw_reservation_type": tax.reservation_type},
                        )

                    # GENDER (secondary from JSONB only where approved)
                    if "gender" in filter_keys:
                        gender = self._extract_gender(path.path_key, tax)
                        if gender:
                            rows_written += self._add_option_if_new(
                                seen_options,
                                path_id=path.path_id,
                                filter_key="gender",
                                option_key=self._normalize_option_key(gender),
                                option_label=self._normalize_gender_label(gender),
                                category_name=tax.category_name,
                                is_reserved=tax.is_reserved,
                                course_type=tax.course_type,
                                location_type=tax.location_type,
                                reservation_type=tax.reservation_type,
                                seat_bucket_code=None,
                                display_meta={"raw_gender": gender},
                            )

                    # PWD (secondary from JSONB only where approved)
                    if "is_pwd" in filter_keys:
                        is_pwd = self._extract_is_pwd(tax)
                        if is_pwd is not None:
                            rows_written += self._add_option_if_new(
                                seen_options,
                                path_id=path.path_id,
                                filter_key="is_pwd",
                                option_key="yes" if is_pwd else "no",
                                option_label="Yes" if is_pwd else "No",
                                category_name=tax.category_name,
                                is_reserved=tax.is_reserved,
                                course_type=tax.course_type,
                                location_type=tax.location_type,
                                reservation_type=tax.reservation_type,
                                seat_bucket_code=None,
                                display_meta={"is_pwd": is_pwd},
                            )

                    # COURSE TYPE (primary from taxonomy main column where approved)
                    if (
                        "course_type" in filter_keys
                        and path.path_key in self.TAXONOMY_COURSE_TYPE_PATH_KEYS
                        and tax.course_type
                    ):
                        normalized_course_type = self._normalize_course_type_label(
                            tax.course_type
                        )
                        rows_written += self._add_option_if_new(
                            seen_options,
                            path_id=path.path_id,
                            filter_key="course_type",
                            option_key=self._normalize_option_key(normalized_course_type),
                            option_label=normalized_course_type,
                            category_name=tax.category_name,
                            is_reserved=tax.is_reserved,
                            course_type=tax.course_type,
                            location_type=tax.location_type,
                            reservation_type=tax.reservation_type,
                            seat_bucket_code=None,
                            display_meta={"raw_course_type": tax.course_type},
                        )

            # JEE institute type comes from actual outcomes, not taxonomy
            if "institute_type" in filter_keys:
                rows_written += self._add_josaa_institute_type_options(
                    seen_options=seen_options,
                    path=path,
                )

        self.db.flush()
        return rows_written

    def _add_josaa_institute_type_options(self, *, seen_options: set, path: ExamPathCatalog) -> int:
        rows_written = 0
        exam_code = str(path.resolved_exam_code or "").upper()

        if exam_code == "JEE_ADV":
            rows_written += self._add_option_if_new(
                seen_options,
                path_id=path.path_id,
                filter_key="institute_type",
                option_key="iit",
                option_label="IIT",
                category_name=None,
                is_reserved=None,
                course_type=None,
                location_type=None,
                reservation_type=None,
                seat_bucket_code=None,
                display_meta={},
            )
            return rows_written

        if exam_code != "JEE_MAIN":
            return 0

        institute_names = (
            self.db.query(CutoffOutcome.institute_name)
            .filter(CutoffOutcome.exam_code == "JEE_MAIN")
            .distinct()
            .all()
        )

        found_types = set()
        for (name,) in institute_names:
            institute_type = self._infer_josaa_institute_type(name)
            if institute_type:
                found_types.add(institute_type)

        for institute_type in sorted(found_types):
            rows_written += self._add_option_if_new(
                seen_options,
                path_id=path.path_id,
                filter_key="institute_type",
                option_key=self._normalize_option_key(institute_type),
                option_label=institute_type,
                category_name=None,
                is_reserved=None,
                course_type=None,
                location_type=None,
                reservation_type=None,
                seat_bucket_code=None,
                display_meta={},
            )

        return rows_written

    def _add_option_if_new(
        self,
        seen_options: set,
        *,
        path_id,
        filter_key: str,
        option_key: str,
        option_label: str,
        category_name,
        is_reserved,
        course_type,
        location_type,
        reservation_type,
        seat_bucket_code,
        display_meta: dict,
    ) -> int:
        unique_key = (str(path_id), filter_key, option_key)
        if unique_key in seen_options:
            return 0

        seen_options.add(unique_key)
        self.db.add(
            ExamSeatFilterServingMap(
                path_id=path_id,
                filter_key=filter_key,
                option_key=option_key,
                option_label=option_label,
                category_name=category_name,
                is_reserved=is_reserved,
                course_type=course_type,
                location_type=location_type,
                reservation_type=reservation_type,
                seat_bucket_code=seat_bucket_code,
                display_meta=display_meta,
                active=True,
            )
        )
        return 1

    @staticmethod
    def _normalize_option_key(value: str) -> str:
        return str(value).strip().lower().replace(" ", "_")

    @staticmethod
    def _normalize_category_label(value: str) -> str:
        raw = str(value).strip()
        raw_upper = raw.upper()

        mapping = {
            "GN": "General",
            "G": "General",
            "F": "Female",
        }
        return mapping.get(raw_upper, raw)

    def _normalize_location_type_label(self, path_key: str, location_type: str, attributes: dict) -> str:
        raw = str(location_type).strip()
        raw_upper = raw.upper()

        if path_key == "kcet":
            if raw_upper == "HK":
                return "Hyderabad-Karnataka"
            if raw_upper == "GEN":
                return "General"
            if raw_upper == "PVT":
                return "Private"

        if path_key in {"mhcet_technical_be", "mhcet_technical_pharma"}:
            dynamic_quota_text = (attributes or {}).get("dynamic_quota_text")
            if dynamic_quota_text and dynamic_quota_text != "N/A":
                return dynamic_quota_text

        mapping = {
            "AI": "All India",
            "AIQ": "All India Quota",
            "JK": "Jammu & Kashmir",
            "LA": "Ladakh",
            "NAT": "National",
        }
        return mapping.get(raw_upper, raw)

    @staticmethod
    def _normalize_reservation_type_label(value: str) -> str:
        raw = str(value).strip()
        raw_upper = raw.upper()

        mapping = {
            "GN": "General",
            "G": "General",
            "F": "Female",
            "FEMALE": "Female",
            "REGULAR": "Regular",
            "AI": "All India",
            "AIQ": "All India Quota",
            "GO": "Goa State",
            "HS": "Home State",
            "OS": "Other State",
        }
        return mapping.get(raw_upper, raw)

    @staticmethod
    def _normalize_gender_label(value: str) -> str:
        raw = str(value).strip()
        raw_upper = raw.upper()
        mapping = {
            "GN": "General",
            "G": "General",
            "F": "Female",
            "FEMALE": "Female",
            "GENERAL": "General",
        }
        return mapping.get(raw_upper, raw)

    @staticmethod
    def _normalize_course_type_label(value: str) -> str:
        return str(value).strip().replace("_", " ")

    @staticmethod
    def _extract_gender(path_key: str, tax: SeatBucketTaxonomy) -> str | None:
        attrs = tax.attributes or {}

        if path_key in {"jee_main", "jee_adv", "mhcet_technical_be", "mhcet_technical_pharma"}:
            return attrs.get("gender")

        reservation_type = str(tax.reservation_type or "").strip()
        if reservation_type.upper() in {"F", "FEMALE"}:
            return "Female"

        return None

    @staticmethod
    def _extract_is_pwd(tax: SeatBucketTaxonomy) -> bool | None:
        attrs = tax.attributes or {}
        if "is_pwd" in attrs:
            return bool(attrs["is_pwd"])
        return None

    @staticmethod
    def _infer_josaa_institute_type(institute_name: str | None) -> str | None:
        raw = str(institute_name or "").strip().lower()
        if not raw:
            return None

        if "indian institute of technology" in raw:
            return "IIT"
        if "institute of information technology" in raw or "iiit" in raw:
            return "IIIT"
        if "national institute of technology" in raw:
            return "NIT"
        return "GFTI"
        
    def _refresh_exam_program_serving_map(
        self,
        *,
        scoped_paths: list[ExamPathCatalog],
        path_filter_keys: dict[str, set[str]],
    ) -> int:
        scoped_path_ids = [p.path_id for p in scoped_paths]
        if not scoped_path_ids:
            return 0

        (
            self.db.query(ExamProgramServingMap)
            .filter(ExamProgramServingMap.path_id.in_(scoped_path_ids))
            .delete(synchronize_session=False)
        )

        rows_written = 0

        for path in scoped_paths:
            if not path.resolved_exam_code:
                continue

            filter_keys = path_filter_keys.get(str(path.path_id), set())
            if "branch" not in filter_keys:
                continue

            exam_code_lower = self._resolve_branch_governance_exam_code(
                path.resolved_exam_code
            )
            exam_code_upper = str(path.resolved_exam_code).strip().upper()

            searchable_programs = (
                self.db.query(
                    CutoffOutcome.program_code,
                    CutoffOutcome.program_name,
                )
                .filter(
                    CutoffOutcome.exam_code == exam_code_upper,
                    CutoffOutcome.is_latest.is_(True),
                    CutoffOutcome.program_code.isnot(None),
                    CutoffOutcome.program_name.isnot(None),
                )
                .distinct()
                .all()
            )

            if not searchable_programs:
                logger.info(
                    "No searchable programs found for path_key=%s exam_code=%s",
                    path.path_key,
                    path.resolved_exam_code,
                )
                continue

            alias_rows = (
                self.db.query(
                    ExamBranchAlias.normalized_alias,
                    ExamBranchRegistry.normalized_name,
                    ExamBranchRegistry.discipline,
                    ExamBranchRegistry.variant,
                )
                .join(
                    ExamBranchRegistry,
                    ExamBranchRegistry.id == ExamBranchAlias.branch_id,
                )
                .filter(
                    ExamBranchAlias.exam_code == exam_code_lower,
                    ExamBranchRegistry.exam_code == exam_code_lower,
                )
                .all()
            )

            alias_map: dict[str, dict[str, str | None]] = {}
            for normalized_alias, combined_normalized_name, discipline, variant in alias_rows:
                alias_map[str(normalized_alias)] = {
                    "combined_key": str(combined_normalized_name),
                    "discipline": discipline,
                    "variant": variant,
                }

            seen_rows = set()

            for program_code, program_name in searchable_programs:
                normalized_program_name = self._normalize_branch_lookup_text(program_name)
                mapped = alias_map.get(normalized_program_name)
                if not mapped:
                    continue

                discipline = (mapped["discipline"] or "").strip()
                variant = (mapped["variant"] or "").strip()

                if not discipline:
                    continue

                branch_option_key = str(mapped["combined_key"]).strip()
                branch_label = self._compose_branch_label(
                    discipline=discipline,
                    variant=variant or None,
                )

                branch_discipline_key = self._normalize_branch_lookup_text(discipline)
                branch_discipline_label = discipline

                specialization_key = (
                    self._normalize_branch_lookup_text(variant) if variant else None
                )
                specialization_label = variant if variant else None
                has_specialization_dimension = bool(variant)

                dedup_key = (str(path.path_id), branch_option_key, str(program_code))
                if dedup_key in seen_rows:
                    continue
                seen_rows.add(dedup_key)

                self.db.add(
                    ExamProgramServingMap(
                        path_id=path.path_id,
                        branch_option_key=branch_option_key,
                        branch_label=branch_label,
                        branch_discipline_key=branch_discipline_key,
                        branch_discipline_label=branch_discipline_label,
                        specialization_key=specialization_key,
                        specialization_label=specialization_label,
                        has_specialization_dimension=has_specialization_dimension,
                        program_code=str(program_code),
                        program_name=program_name,
                        mapping_confidence=1.0,
                        mapping_status=MappingStatusEnum.APPROVED,
                        approved_by="system:serving_map_builder",
                        approved_at=None,
                    )
                )
                rows_written += 1

        self.db.flush()
        return rows_written

    @staticmethod
    def _normalize_branch_lookup_text(value: str) -> str:
        return " ".join(str(value).strip().lower().split())

    @staticmethod
    def _compose_branch_label(*, discipline: str, variant: str | None) -> str:
        if variant:
            return f"{discipline} - {variant}"
        return discipline

    @staticmethod
    def _resolve_branch_governance_exam_code(resolved_exam_code: str | None) -> str:
        exam_code = str(resolved_exam_code or "").strip().upper()

        if exam_code in {"JEE_MAIN", "JEE_ADV"}:
            return "josaa"

        return exam_code.lower()