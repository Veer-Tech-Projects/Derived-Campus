from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import ExamBranchRegistry, ExamBranchAlias, ExamCourseType, ExamCourseTypeAlias

class TaxonomyCache:
    """
    In-Memory O(1) resolution layer to prevent N+1 Database queries 
    during massive PDF parsing loops.
    """
    def __init__(self, db: Session, exam_code: str):
        self.valid_branches = set()
        self.valid_courses = set()
        self._load(db, exam_code)

    def _load(self, db: Session, exam_code: str):
        # Pre-load Branches (Canonicals + Aliases)
        self.valid_branches.update(db.scalars(
            select(ExamBranchRegistry.normalized_name).where(ExamBranchRegistry.exam_code == exam_code)
        ).all())
        self.valid_branches.update(db.scalars(
            select(ExamBranchAlias.normalized_alias).where(ExamBranchAlias.exam_code == exam_code)
        ).all())
        
        # Pre-load Courses (Canonicals + Aliases)
        self.valid_courses.update(db.scalars(
            select(ExamCourseType.normalized_name).where(ExamCourseType.exam_code == exam_code)
        ).all())
        self.valid_courses.update(db.scalars(
            select(ExamCourseTypeAlias.normalized_alias).where(ExamCourseTypeAlias.exam_code == exam_code)
        ).all())

    def is_branch_known(self, norm_name: str) -> bool:
        return norm_name in self.valid_branches

    def is_course_known(self, norm_name: str) -> bool:
        return norm_name in self.valid_courses