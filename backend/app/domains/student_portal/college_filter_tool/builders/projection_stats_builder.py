import logging
from collections import defaultdict
from statistics import mean, median, pstdev
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models import (
    CutoffOutcome,
    ExamConfiguration,
    ExamPathCatalog,
    RoundProjectionStats,
)

logger = logging.getLogger(__name__)


class ProjectionStatsBuilder:
    """
    Step 5: Offline projection stats builder.

    Guarantees:
    - same-round aligned only
    - last 3 years only
    - exact college-level comparable path
    - binds only to deployed RoundProjectionStats schema
    - stores projection inputs, not final probabilities/bands
    """

    LOOKBACK_YEARS = 3
    EPSILON = 1e-9

    def __init__(self, db: Session):
        self.db = db

    def build_for_scope(self, trigger_exam_code: str | None = None) -> dict:
        logger.info(
            "Starting ProjectionStatsBuilder for trigger_exam_code=%s",
            trigger_exam_code,
        )

        active_paths = (
            self.db.query(ExamPathCatalog)
            .filter(
                ExamPathCatalog.active.is_(True),
                ExamPathCatalog.resolved_exam_code.isnot(None),
            )
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

        if not scoped_paths:
            return {
                "trigger_exam_code": trigger_exam_code,
                "round_projection_stats_rows": 0,
            }

        scoped_path_ids = [p.path_id for p in scoped_paths]
        scoped_exam_codes = sorted({str(p.resolved_exam_code).upper() for p in scoped_paths})

        (
            self.db.query(RoundProjectionStats)
            .filter(RoundProjectionStats.path_id.in_(scoped_path_ids))
            .delete(synchronize_session=False)
        )

        exam_metric_type = self._load_exam_metric_types(scoped_exam_codes)

        rows_written = 0
        for path in scoped_paths:
            exam_code = str(path.resolved_exam_code).upper()
            configured_metric_type = exam_metric_type.get(exam_code, "rank")

            rows_written += self._build_path_projection_stats(
                path_id=path.path_id,
                exam_code=exam_code,
                configured_metric_type=configured_metric_type,
            )

        self.db.flush()

        return {
            "trigger_exam_code": trigger_exam_code,
            "round_projection_stats_rows": rows_written,
        }

    def _load_exam_metric_types(self, exam_codes: list[str]) -> dict[str, str]:
        metric_map: dict[str, str] = {}

        rows = (
            self.db.query(ExamConfiguration.exam_code, ExamConfiguration.metric_type)
            .filter(ExamConfiguration.exam_code.in_([code.lower() for code in exam_codes]))
            .all()
        )

        for exam_code, metric_type in rows:
            metric_map[str(exam_code).upper()] = str(metric_type).lower()

        return metric_map

    def _build_path_projection_stats(
        self,
        *,
        path_id: Any,
        exam_code: str,
        configured_metric_type: str,
    ) -> int:
        latest_year_for_exam = (
            self.db.query(func.max(CutoffOutcome.year))
            .filter(
                CutoffOutcome.exam_code == exam_code,
                CutoffOutcome.is_latest.is_(True),
            )
            .scalar()
        )

        if latest_year_for_exam is None:
            return 0

        latest_year_for_exam = int(latest_year_for_exam)
        lower_year_bound = latest_year_for_exam - (self.LOOKBACK_YEARS - 1)

        scoped_rows = (
            self.db.query(CutoffOutcome)
            .filter(
                CutoffOutcome.exam_code == exam_code,
                CutoffOutcome.is_latest.is_(True),
                CutoffOutcome.year >= lower_year_bound,
            )
            .all()
        )

        if not scoped_rows:
            return 0

        # Group by exact comparable path:
        # college + seat bucket + program + round
        by_scope: dict[tuple[Any, str, str | None, int], list[CutoffOutcome]] = defaultdict(list)

        skipped_missing_college_id = 0

        for row in scoped_rows:
            if not row.college_id:
                skipped_missing_college_id += 1
                continue

            key = (
                row.college_id,
                str(row.seat_bucket_code),
                str(row.program_code) if row.program_code is not None else None,
                int(row.round_number),
            )
            by_scope[key].append(row)

        if skipped_missing_college_id:
            logger.warning(
                "ProjectionStatsBuilder skipped %s rows for exam=%s due to missing college_id.",
                skipped_missing_college_id,
                exam_code,
            )

        rows_written = 0

        for (college_id, seat_bucket_code, program_code, round_number), group_rows in by_scope.items():
            primary_metric = self._resolve_primary_metric(
                configured_metric_type=configured_metric_type,
                rows=group_rows,
            )

            metric_points: list[float] = []
            source_years: list[int] = []

            for row in group_rows:
                metric_value = self._extract_metric_value(row, primary_metric)
                if metric_value is None:
                    continue

                metric_points.append(float(metric_value))
                source_years.append(int(row.year))

            observation_count = len(metric_points)

            same_round_mean = mean(metric_points) if observation_count > 0 else None
            same_round_median = median(metric_points) if observation_count > 0 else None
            same_round_stddev = pstdev(metric_points) if observation_count >= 2 else None

            source_years_sorted = sorted(set(source_years))

            current_year_presence_score = (
                1.0 if latest_year_for_exam in source_years_sorted else 0.0
            )

            round_evidence_score = min(
                observation_count / float(self.LOOKBACK_YEARS),
                1.0,
            )

            round_stability_score = self._compute_stability_score(
                metric_points=metric_points,
                median_value=same_round_median,
                stddev_value=same_round_stddev,
            )

            is_cold_start = observation_count < 2

            relaxation_ratio_from_prev_round = self._compute_relaxation_ratio_from_prev_round(
                scoped_rows=scoped_rows,
                college_id=college_id,
                seat_bucket_code=seat_bucket_code,
                program_code=program_code,
                round_number=round_number,
                primary_metric=primary_metric,
            )

            stats_row = RoundProjectionStats(
                path_id=path_id,
                college_id=college_id,
                exam_code=exam_code,
                seat_bucket_code=seat_bucket_code,
                program_code=program_code,
                round_number=round_number,
                same_round_mean=same_round_mean,
                same_round_median=same_round_median,
                same_round_stddev=same_round_stddev,
                same_round_observation_count=observation_count,
                relaxation_ratio_from_prev_round=relaxation_ratio_from_prev_round,
                current_year_presence_score=current_year_presence_score,
                round_evidence_score=round_evidence_score,
                round_stability_score=round_stability_score,
                is_cold_start=is_cold_start,
                source_years=source_years_sorted,
            )
            self.db.add(stats_row)
            rows_written += 1

        return rows_written

    def _compute_relaxation_ratio_from_prev_round(
        self,
        *,
        scoped_rows: list[CutoffOutcome],
        college_id: Any,
        seat_bucket_code: str,
        program_code: str | None,
        round_number: int,
        primary_metric: str,
    ) -> float | None:
        """
        Median of same-college same-path transition ratios:
            current_round_value / previous_round_value
        using only years where both consecutive rounds exist.
        """
        if round_number <= 1:
            return None

        prev_round = round_number - 1

        by_year_and_round: dict[tuple[int, int], CutoffOutcome] = {}

        for row in scoped_rows:
            if row.college_id != college_id:
                continue

            if str(row.seat_bucket_code) != seat_bucket_code:
                continue

            row_program_code = str(row.program_code) if row.program_code is not None else None
            if row_program_code != program_code:
                continue

            by_year_and_round[(int(row.year), int(row.round_number))] = row

        ratios: list[float] = []
        years = sorted({year for year, _ in by_year_and_round.keys()})

        for year in years:
            prev_row = by_year_and_round.get((year, prev_round))
            curr_row = by_year_and_round.get((year, round_number))

            if not prev_row or not curr_row:
                continue

            prev_value = self._extract_metric_value(prev_row, primary_metric)
            curr_value = self._extract_metric_value(curr_row, primary_metric)

            if prev_value is None or curr_value is None:
                continue
            if abs(prev_value) <= self.EPSILON:
                continue

            ratios.append(curr_value / prev_value)

        if not ratios:
            return None

        return float(median(ratios))

    def _resolve_primary_metric(
        self,
        *,
        configured_metric_type: str,
        rows: list[CutoffOutcome],
    ) -> str:
        configured = str(configured_metric_type or "rank").lower()

        has_percentile = any(r.cutoff_percentile is not None for r in rows)
        has_rank = any(r.closing_rank is not None for r in rows)

        if configured == "percentile" and has_percentile:
            return "percentile"

        if has_rank:
            return "rank"

        if has_percentile:
            return "percentile"

        return "rank"

    @staticmethod
    def _extract_metric_value(row: CutoffOutcome, metric_type: str) -> float | None:
        if metric_type == "percentile":
            return float(row.cutoff_percentile) if row.cutoff_percentile is not None else None
        return float(row.closing_rank) if row.closing_rank is not None else None

    def _compute_stability_score(
        self,
        *,
        metric_points: list[float],
        median_value: float | None,
        stddev_value: float | None,
    ) -> float:
        if not metric_points or median_value is None or stddev_value is None:
            return 0.0

        denominator = max(abs(float(median_value)) * 0.15, self.EPSILON)
        normalized_dispersion = min(1.0, float(stddev_value) / denominator)
        score = 1.0 - normalized_dispersion
        return max(0.0, min(1.0, score))