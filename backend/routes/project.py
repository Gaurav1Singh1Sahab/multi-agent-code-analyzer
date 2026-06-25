from fastapi import APIRouter, Depends, status, UploadFile, File

from backend.models.user import User
from backend.schemas.project_schema import (
    ProjectRegisterRequest,
    ProjectRegisterResponse,
    ZipUploadResponse
)
from backend.services.project_service import register_project, upload_zip_file
from backend.database import get_db
from sqlalchemy.orm import Session
from backend.utils.auth_dependency import get_current_user

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.post(
    "/upload-zip",
    response_model=ZipUploadResponse,
    status_code=status.HTTP_201_CREATED
)
def upload_zip(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    return upload_zip_file(file)


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


from fastapi import APIRouter, Depends, status, UploadFile, File
from sqlalchemy.orm import Session

from backend.models.user import User
from backend.schemas.project_schema import (
    ProjectRegisterRequest,
    ProjectRegisterResponse,
    ZipUploadResponse,
    StartAnalysisResponse
)
from backend.services.project_service import (
    register_project,
    upload_zip_file,
    start_project_analysis
)
from backend.database import get_db
from backend.utils.auth_dependency import get_current_user

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "/upload-zip",
    response_model=ZipUploadResponse,
    status_code=status.HTTP_201_CREATED
)
def upload_zip(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    return upload_zip_file(file)


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


@router.post(
    "/{project_id}/start-analysis",
    response_model=StartAnalysisResponse,
    status_code=status.HTTP_200_OK
)


def start_analysis(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)):
    
    project, workspace_path = start_project_analysis(db, current_user, project_id)

    return StartAnalysisResponse(
        project_id=project.project_id,
        persona=project.persona,
        source_type=project.source_type,
        source_value=project.source_value,
        status=project.status,
        workspace_path=workspace_path,
        message=f"Analysis started successfully for project {project.project_id}"
    )