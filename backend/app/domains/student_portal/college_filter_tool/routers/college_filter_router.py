from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domains.student_portal.college_filter_tool.schemas.runtime_search_schemas import (
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
from app.domains.student_portal.college_filter_tool.services.college_filter_runtime_service import (
    CollegeFilterRuntimeService,
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


@router.post("/search", response_model=CollegeFilterSearchResponse)
async def search_college_filter(
    request: CollegeFilterSearchRequest,
    db: AsyncSession = Depends(get_db),
):
    runtime_service = CollegeFilterRuntimeService(db)
    return await runtime_service.search(request=request)