from sqlalchemy.orm import Session

from backend.models.project import Project
from backend.models.user import User
from backend.schemas.project_schema import ProjectRegisterRequest
from backend.utils.project_id_generator import generate_project_id


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