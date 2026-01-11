from aiocache import cached
from fastapi import APIRouter, Depends, Request, status

from api.dependencies import RoleChecker, get_section_service
from app.limiter import limiter
from models.py_object_id import PyObjectId
from models.sections import Section
from models.update_section import UpdateSection
from services.sections import SectionService

router = APIRouter(prefix="/api/sections", tags=["Sections"])


@router.post(
    "/create",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(RoleChecker(["admin"]))],
)
@limiter.limit("5/minute")
async def create_section(
    request: Request,
    section: Section,
    section_service: SectionService = Depends(get_section_service),
):
    return await section_service.create_section(section)


@router.get("/all")
@limiter.limit("10/minute")
@cached(
    ttl=3600,
    key="all_sections",
    alias="default",
)
async def get_all_sections(
    request: Request, section_service: SectionService = Depends(get_section_service)
):
    return await section_service.get_all_sections()


@router.get("/{section_id}/download")
@limiter.limit("5/minute")
@cached(
    ttl=600,
    key_builder=lambda f, *args, **kwargs: f"download_{kwargs['section_id']}",
    alias="default",
)
async def download_section(
    request: Request,
    section_id: PyObjectId,
    section_service: SectionService = Depends(get_section_service),
):
    return await section_service.get_section_for_download(str(section_id))


@router.get("/{section_id}")
@limiter.limit("10/minute")
async def get_section(
    request: Request,
    section_id: PyObjectId,
    section_service: SectionService = Depends(get_section_service),
):
    return await section_service.get_section(str(section_id))


@router.put("/update/{section_id}", dependencies=[Depends(RoleChecker(["admin"]))])
@limiter.limit("10/minute")
async def update_section(
    request: Request,
    section_id: PyObjectId,
    updated_info: UpdateSection,
    section_service: SectionService = Depends(get_section_service),
):
    return await section_service.update_section(str(section_id), updated_info)


@router.delete(
    "/delete/{section_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker(["admin"]))],
)
@limiter.limit("10/minute")
async def delete_section(
    request: Request,
    section_id: PyObjectId,
    section_service: SectionService = Depends(get_section_service),
):
    await section_service.delete_section(str(section_id))
