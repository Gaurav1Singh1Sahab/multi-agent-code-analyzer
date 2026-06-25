import os, shutil, json
from datetime import datetime
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.models.project import Project
from backend.models.user import User
from backend.schemas.project_schema import ProjectRegisterRequest
from backend.utils.project_id_generator import generate_project_id

from git import Repo


UPLOAD_DIR = "uploads/zip_repos"

WORKSPACE_ROOT = "project_workspaces"


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
        
def upload_zip_file(file: UploadFile) -> dict:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No file provided"
        )

    if not file.filename.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .zip files are allowed"
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_filename = file.filename.replace(" ", "_")
    stored_filename = f"repo_{timestamp}_{safe_filename}"
    stored_path = os.path.join(UPLOAD_DIR, stored_filename)

    with open(stored_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "filename": stored_filename,
        "stored_path": stored_path,
        "message": "ZIP uploaded successfully"
    }



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
    source_type=project_data.source_type,
    source_value=project_data.source_value,
    status="REGISTERED"
)

    db.add(new_project)
    db.commit()
    db.refresh(new_project)

    return new_project



def start_project_analysis(
    db: Session,
    user: User,
    project_id: str
) -> tuple[Project, str]:
    project = (
        db.query(Project)
        .filter(Project.project_id == project_id, Project.user_id == user.id)
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found for this user"
        )

    if project.status == "ANALYSIS_STARTED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analysis already started for this project"
        )

    project.status = "ANALYSIS_STARTED"
    project.analysis_started_at = datetime.utcnow()

    db.commit()
    db.refresh(project)

    workspace_path = prepare_project_workspace(project)

    # Step 2 addition: clone GitHub repo into workspace/source
    if project.source_type == "github":
        clone_github_repo(project.source_value, workspace_path)

    return project, workspace_path




def prepare_project_workspace(project: Project) -> str:
    os.makedirs(WORKSPACE_ROOT, exist_ok=True)

    project_workspace = os.path.join(WORKSPACE_ROOT, project.project_id)
    source_dir = os.path.join(project_workspace, "source")
    artifacts_dir = os.path.join(project_workspace, "artifacts")
    logs_dir = os.path.join(project_workspace, "logs")

    os.makedirs(project_workspace, exist_ok=True)
    os.makedirs(source_dir, exist_ok=True)
    os.makedirs(artifacts_dir, exist_ok=True)
    os.makedirs(logs_dir, exist_ok=True)

    metadata = {
        "project_id": project.project_id,
        "user_id": project.user_id,
        "persona": project.persona,
        "source_type": project.source_type,
        "source_value": project.source_value,
        "status": "ANALYSIS_STARTED",
        "created_at": str(project.created_at) if project.created_at else None,
        "analysis_started_at": str(project.analysis_started_at) if project.analysis_started_at else None
    }

    metadata_file = os.path.join(project_workspace, "metadata.json")
    with open(metadata_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=4)

    return project_workspace


def clone_github_repo(repo_url: str, workspace_path: str) -> None:
    source_dir = os.path.join(workspace_path, "source")

    # Prevent cloning into a non-empty source dir
    if os.path.exists(source_dir) and os.listdir(source_dir):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source directory is not empty, cannot clone repository"
        )

    try:
        Repo.clone_from(repo_url, source_dir)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clone GitHub repository: {str(e)}"
        )