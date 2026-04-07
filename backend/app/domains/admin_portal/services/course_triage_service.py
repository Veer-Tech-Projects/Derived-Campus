import re
from typing import Type, List
from sqlalchemy.orm import Session
from sqlalchemy import select, update, func
from fastapi import HTTPException

# Adjust imports based on your project structure
from app.models import (
    ExamCourseType, ExamCourseTypeAlias, ExamCourseTypeCandidate,
    ExamBranchRegistry, ExamBranchAlias, ExamBranchCandidate,
    DiscoveredArtifact
)

class TriageConcurrencyEngine:
    """
    Core distributed systems engine for preventing race conditions and deadlocks.
    """
    @staticmethod
    def normalize_string(val: str) -> str:
        if not val:
            return ""
        return re.sub(r'\s+', ' ', val.strip()).lower()

    @staticmethod
    def acquire_advisory_locks(db: Session, exam_code: str, names: List[str]):
        if not names:
            return
            
        # Deduplicate and sort to guarantee Deadlock Immunity
        sorted_unique_names = sorted(list(set(names)))
        
        for name in sorted_unique_names:
            # 64-bit lock utilizing exam_code and string hashes
            db.execute(
                select(func.pg_advisory_xact_lock(
                    func.hashtext(exam_code), 
                    func.hashtext(name)
                ))
            )

    @staticmethod
    def verify_namespace_collision(db: Session, exam_code: str, normalized_name: str, registry_model: Type, alias_model: Type):
        registry_exists = db.scalar(
            select(registry_model.id)
            .where(registry_model.exam_code == exam_code, registry_model.normalized_name == normalized_name)
        )
        if registry_exists:
            raise HTTPException(status_code=409, detail=f"Conflict: '{normalized_name}' already exists as Canonical.")

        alias_exists = db.scalar(
            select(alias_model.id)
            .where(alias_model.exam_code == exam_code, alias_model.normalized_alias == normalized_name)
        )
        if alias_exists:
            raise HTTPException(status_code=409, detail=f"Conflict: '{normalized_name}' is already an Alias.")


class CourseTypeTriageService:
    
    @staticmethod
    def promote_candidate(db: Session, candidate_id: str, canonical_name: str) -> ExamCourseType:
        # Lock the row and enforce PENDING state
        candidate = db.scalar(
            select(ExamCourseTypeCandidate)
            .where(ExamCourseTypeCandidate.id == candidate_id, ExamCourseTypeCandidate.status == 'PENDING')
            .with_for_update()
        )
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found or not in PENDING state.")

        normalized_canonical = TriageConcurrencyEngine.normalize_string(canonical_name)
        target_locks = [normalized_canonical, candidate.normalized_name]

        TriageConcurrencyEngine.acquire_advisory_locks(db, candidate.exam_code, target_locks)

        TriageConcurrencyEngine.verify_namespace_collision(
            db, candidate.exam_code, normalized_canonical, ExamCourseType, ExamCourseTypeAlias
        )
        if candidate.normalized_name != normalized_canonical:
            TriageConcurrencyEngine.verify_namespace_collision(
                db, candidate.exam_code, candidate.normalized_name, ExamCourseType, ExamCourseTypeAlias
            )

        new_registry = ExamCourseType(
            exam_code=candidate.exam_code,
            canonical_name=canonical_name,
            normalized_name=normalized_canonical
        )
        db.add(new_registry)
        db.flush()

        db.add(ExamCourseTypeAlias(
            exam_code=candidate.exam_code, course_type_id=new_registry.id, normalized_alias=normalized_canonical
        ))

        if candidate.normalized_name != normalized_canonical:
            db.add(ExamCourseTypeAlias(
                exam_code=candidate.exam_code, course_type_id=new_registry.id, normalized_alias=candidate.normalized_name
            ))

        db.execute(
            update(DiscoveredArtifact)
            .where(DiscoveredArtifact.id == candidate.source_artifact_id)
            .values(requires_reprocessing=True)
        )
        db.delete(candidate)
        
        return new_registry

    @staticmethod
    def link_candidate(db: Session, candidate_id: str, target_course_type_id: str):
        candidate = db.scalar(
            select(ExamCourseTypeCandidate)
            .where(ExamCourseTypeCandidate.id == candidate_id, ExamCourseTypeCandidate.status == 'PENDING')
            .with_for_update()
        )
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found or not PENDING.")

        target_registry = db.scalar(select(ExamCourseType).where(ExamCourseType.id == target_course_type_id))
        if not target_registry or target_registry.exam_code != candidate.exam_code:
            raise HTTPException(status_code=400, detail="Target Course Type invalid or cross-exam mismatch.")

        TriageConcurrencyEngine.acquire_advisory_locks(db, candidate.exam_code, [candidate.normalized_name])
        TriageConcurrencyEngine.verify_namespace_collision(
            db, candidate.exam_code, candidate.normalized_name, ExamCourseType, ExamCourseTypeAlias
        )

        db.add(ExamCourseTypeAlias(
            exam_code=candidate.exam_code,
            course_type_id=target_course_type_id,
            normalized_alias=candidate.normalized_name
        ))

        db.execute(
            update(DiscoveredArtifact)
            .where(DiscoveredArtifact.id == candidate.source_artifact_id)
            .values(requires_reprocessing=True)
        )
        db.delete(candidate)

    @staticmethod
    def reject_candidate(db: Session, candidate_id: str):
        candidate = db.scalar(
            select(ExamCourseTypeCandidate)
            .where(ExamCourseTypeCandidate.id == candidate_id, ExamCourseTypeCandidate.status == 'PENDING')
            .with_for_update()
        )
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found or not PENDING.")
            
        candidate.status = "REJECTED"


class BranchTriageService:
    
    @staticmethod
    def _generate_branch_normalized_name(discipline: str, variant: str | None) -> str:
        norm_disc = TriageConcurrencyEngine.normalize_string(discipline)
        if not variant:
            return norm_disc
        norm_var = TriageConcurrencyEngine.normalize_string(variant)
        return f"{norm_disc} - {norm_var}"

    @staticmethod
    def promote_candidate(db: Session, candidate_id: str, discipline: str, variant: str | None) -> ExamBranchRegistry:
        candidate = db.scalar(
            select(ExamBranchCandidate)
            .where(ExamBranchCandidate.id == candidate_id, ExamBranchCandidate.status == 'PENDING')
            .with_for_update()
        )
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found or not PENDING.")

        normalized_canonical = BranchTriageService._generate_branch_normalized_name(discipline, variant)
        target_locks = [normalized_canonical, candidate.normalized_name]

        TriageConcurrencyEngine.acquire_advisory_locks(db, candidate.exam_code, target_locks)

        TriageConcurrencyEngine.verify_namespace_collision(
            db, candidate.exam_code, normalized_canonical, ExamBranchRegistry, ExamBranchAlias
        )
        if candidate.normalized_name != normalized_canonical:
            TriageConcurrencyEngine.verify_namespace_collision(
                db, candidate.exam_code, candidate.normalized_name, ExamBranchRegistry, ExamBranchAlias
            )

        new_registry = ExamBranchRegistry(
            exam_code=candidate.exam_code, discipline=discipline, variant=variant, normalized_name=normalized_canonical
        )
        db.add(new_registry)
        db.flush()

        db.add(ExamBranchAlias(
            exam_code=candidate.exam_code, branch_id=new_registry.id, normalized_alias=normalized_canonical
        ))

        if candidate.normalized_name != normalized_canonical:
            db.add(ExamBranchAlias(
                exam_code=candidate.exam_code, branch_id=new_registry.id, normalized_alias=candidate.normalized_name
            ))

        db.execute(
            update(DiscoveredArtifact)
            .where(DiscoveredArtifact.id == candidate.source_artifact_id)
            .values(requires_reprocessing=True)
        )
        db.delete(candidate)
        
        return new_registry

    @staticmethod
    def link_candidate(db: Session, candidate_id: str, target_branch_id: str):
        candidate = db.scalar(
            select(ExamBranchCandidate)
            .where(ExamBranchCandidate.id == candidate_id, ExamBranchCandidate.status == 'PENDING')
            .with_for_update()
        )
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found or not PENDING.")

        target_registry = db.scalar(select(ExamBranchRegistry).where(ExamBranchRegistry.id == target_branch_id))
        if not target_registry or target_registry.exam_code != candidate.exam_code:
            raise HTTPException(status_code=400, detail="Target Branch invalid or cross-exam mismatch.")

        TriageConcurrencyEngine.acquire_advisory_locks(db, candidate.exam_code, [candidate.normalized_name])
        TriageConcurrencyEngine.verify_namespace_collision(
            db, candidate.exam_code, candidate.normalized_name, ExamBranchRegistry, ExamBranchAlias
        )

        db.add(ExamBranchAlias(
            exam_code=candidate.exam_code, branch_id=target_branch_id, normalized_alias=candidate.normalized_name
        ))

        db.execute(
            update(DiscoveredArtifact)
            .where(DiscoveredArtifact.id == candidate.source_artifact_id)
            .values(requires_reprocessing=True)
        )
        db.delete(candidate)

    @staticmethod
    def reject_candidate(db: Session, candidate_id: str):
        candidate = db.scalar(
            select(ExamBranchCandidate)
            .where(ExamBranchCandidate.id == candidate_id, ExamBranchCandidate.status == 'PENDING')
            .with_for_update()
        )
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found or not PENDING.")
            
        candidate.status = "REJECTED"