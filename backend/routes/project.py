from fastapi import APIRouter, Depends, status

from backend.models.user import User
from backend.schemas.project_schema import (
    ProjectRegisterRequest,
    ProjectRegisterResponse
)
from backend.services.project_service import register_project
from backend.database import get_db
from sqlalchemy.orm import Session
from backend.utils.auth_dependency import get_current_user

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "/register",
    response_model=ProjectRegisterResponse,
    status_code=status.HTTP_201_CREATED
)
def create_project(
    project_data: ProjectRegisterRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = register_project(db, current_user, project_data)

    return ProjectRegisterResponse(
        project_id=project.project_id,
        persona=project.persona,
        source_type=project.source_type,
        source_value=project.source_value,
        status=project.status,
        message="Project registered successfully"
    )