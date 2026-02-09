import uuid
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, desc, func, distinct, cast, String
from sqlalchemy.dialects.postgresql import insert

from app.models import SeatPolicyQuarantine, SeatBucketTaxonomy, DiscoveredArtifact

logger = logging.getLogger("SeatTriageService")

class SeatTriageService:
    
    async def get_pending_violations(self, db: AsyncSession, skip: int = 0, limit: int = 100):
        """
        Groups violations by Slug. Returns exactly ONE row per unique bucket type.
        """
        query = (
            select(
                # Cast UUID to text to fix 'min(uuid)' Postgres error
                func.min(cast(SeatPolicyQuarantine.id, String)).label("id"),
                SeatPolicyQuarantine.seat_bucket_code,
                SeatPolicyQuarantine.exam_code,
                func.max(SeatPolicyQuarantine.source_year).label("source_year"),
                func.count(SeatPolicyQuarantine.id).label("count")
            )
            .where(SeatPolicyQuarantine.status == "OPEN")
            .group_by(SeatPolicyQuarantine.seat_bucket_code, SeatPolicyQuarantine.exam_code)
            .order_by(desc("count"))
            .offset(skip)
            .limit(limit)
        )
        
        result = await db.execute(query)
        # Return flat dictionaries for the frontend
        return [
            {
                "id": row.id,
                "seat_bucket_code": row.seat_bucket_code,
                "exam_code": row.exam_code,
                "source_year": row.source_year,
                "count": row.count
            }
            for row in result.all()
        ]

    async def promote_bucket(self, db: AsyncSession, violation_id: uuid.UUID) -> bool:
        # 1. Identify which SLUG we are approving
        target = await db.execute(select(SeatPolicyQuarantine).where(SeatPolicyQuarantine.id == violation_id))
        ref = target.scalar_one_or_none()
        if not ref: raise ValueError("Reference not found")
            
        target_slug = ref.seat_bucket_code
        attrs = ref.raw_row # These are the pre-saved DNA attributes from Step 1

        try:
            # 2. Add to Master Taxonomy once
            stmt = insert(SeatBucketTaxonomy).values(
                seat_bucket_code=target_slug,
                exam_code=ref.exam_code,
                category_name=attrs.get('category_group', 'Unknown'),
                is_reserved=attrs.get('is_reserved', False),
                course_type=attrs.get('course_type'),
                location_type=attrs.get('location_type'),
                reservation_type=attrs.get('reservation_type'),
                attributes=attrs.get('extra_attributes', {})
            ).on_conflict_do_nothing(index_elements=['seat_bucket_code'])
            await db.execute(stmt)

            # 3. Resolve ALL violations sharing this slug across ALL colleges
            await db.execute(
                update(SeatPolicyQuarantine)
                .where(and_(SeatPolicyQuarantine.seat_bucket_code == target_slug, SeatPolicyQuarantine.status == "OPEN"))
                .values(status="RESOLVED")
            )

            # 4. Trigger Reprocessing for ALL affected artifacts
            files_res = await db.execute(
                select(distinct(SeatPolicyQuarantine.source_file)).where(SeatPolicyQuarantine.seat_bucket_code == target_slug)
            )
            file_ids = [uuid.UUID(row[0]) for row in files_res.all() if row[0]]

            if file_ids:
                await db.execute(
                    update(DiscoveredArtifact)
                    .where(DiscoveredArtifact.id.in_(file_ids))
                    .values(requires_reprocessing=True, status="APPROVED")
                )

            await db.commit()
            return True
        except Exception as e:
            await db.rollback()
            raise e

    async def ignore_bucket(self, db: AsyncSession, violation_id: uuid.UUID):
        target = await db.execute(select(SeatPolicyQuarantine.seat_bucket_code).where(SeatPolicyQuarantine.id == violation_id))
        slug = target.scalar_one_or_none()
        if slug:
            await db.execute(
                update(SeatPolicyQuarantine)
                .where(and_(SeatPolicyQuarantine.seat_bucket_code == slug, SeatPolicyQuarantine.status == "OPEN"))
                .values(status="IGNORED")
            )
            await db.commit()