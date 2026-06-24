from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.models.project import Project
from backend.models.user import User
from backend.schemas.project_schema import ProjectRegisterRequest
from backend.utils.project_id_generator import generate_project_id


def validate_source(project_data: ProjectRegisterRequest) -> None:
    if project_data.source_type == "github":
        if not (
            project_data.source_value.startswith("https://github.com/")
            or project_data.source_value.startswith("http://github.com/")
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="For source_type='github', source_value must be a valid GitHub repository URL"
            )

    elif project_data.source_type == "zip":
        if not project_data.source_value.lower().endswith(".zip"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="For source_type='zip', source_value must be a .zip filename or path"
            )

    elif project_data.source_type == "local_git":
        if len(project_data.source_value.strip()) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="For source_type='local_git', source_value cannot be empty"
            )
        


def register_project(
    db: Session,
    user: User,
    project_data: ProjectRegisterRequest
) -> Project:
    total_projects = db.query(Project).count()
    new_project_id = generate_project_id(total_projects)

    new_project = Project(
        project_id=new_project_id,
        user_id=user.id,
        persona=project_data.persona,
        source_type="github",
        source_value=str(project_data.github_url),
        status="REGISTERED"
    )

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return new_project