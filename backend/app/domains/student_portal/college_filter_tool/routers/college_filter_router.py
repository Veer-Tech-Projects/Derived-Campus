from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import StudentUser
from app.domains.student_auth.dependencies.student_auth_dependency import (
    get_current_student,
)
from app.domains.student_portal.college_filter_tool.schemas.runtime_search_schemas import (
    CollegeFilterInsufficientCreditsResponse,
    CollegeFilterMetadataResponse,
    CollegeFilterPathCatalogResponse,
    CollegeFilterSearchRequest,
    CollegeFilterSearchResponse,
)
from app.domains.student_portal.college_filter_tool.services.metadata_service import (
    college_filter_metadata_service,
)
from app.domains.student_portal.college_filter_tool.services.path_catalog_service import (
    college_filter_path_catalog_service,
)
from app.domains.student_portal.college_filter_tool.services.college_filter_billable_search_service import (
    college_filter_billable_search_service,
)
from app.domains.student_portal.student_billing.exceptions import (
    InsufficientCreditsError,
    StudentBillingError,
)

router = APIRouter(
    prefix="/student/college-filter",
    tags=["Student Portal: College Filter Tool"],
)


@router.get("/paths", response_model=CollegeFilterPathCatalogResponse)
async def get_college_filter_paths(
    db: AsyncSession = Depends(get_db),
):
    return await college_filter_path_catalog_service.build_path_catalog_response(db=db)


@router.get("/metadata/{path_id}", response_model=CollegeFilterMetadataResponse)
async def get_college_filter_metadata(
    path_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    return await college_filter_metadata_service.build_metadata_response(
        db=db,
        path_id=path_id,
    )


@router.post(
    "/search",
    response_model=CollegeFilterSearchResponse,
    status_code=status.HTTP_200_OK,
    responses={
        409: {
            "model": CollegeFilterInsufficientCreditsResponse,
            "description": "Student does not have enough credits for a new billable search.",
        }
    },
)
async def search_college_filter(
    request: CollegeFilterSearchRequest,
    current_student: StudentUser = Depends(get_current_student),
    db: AsyncSession = Depends(get_db),
) -> CollegeFilterSearchResponse:
    try:
        return await college_filter_billable_search_service.execute_billable_search(
            db=db,
            student=current_student,
            request=request,
        )
    except InsufficientCreditsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "INSUFFICIENT_CREDITS",
                "message": str(exc),
                "available_credits": exc.available_credits,
                "required_credits": exc.required_credits,
                "billing_redirect_path": "/student-billing/plans",
            },
        ) from exc
    except StudentBillingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc