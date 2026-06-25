import os, shutil, json
from datetime import datetime
from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from backend.models.project import Project
from backend.models.user import User
from backend.schemas.project_schema import ProjectRegisterRequest
from backend.utils.project_id_generator import generate_project_id

import zipfile

from git import Repo


UPLOAD_DIR = "uploads/zip_repos"

WORKSPACE_ROOT = "project_workspaces"

IGNORED_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    "node_modules",
    "dist",
    "build",
    ".idea",
    ".pytest_cache",
    ".mypy_cache"
}


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

    if project.source_type == "github":
        clone_github_repo(project.source_value, workspace_path)

    elif project.source_type == "zip":
        extract_zip_to_workspace(project.source_value, workspace_path)

    elif project.source_type == "local_git":
        copy_local_repo_to_workspace(project.source_value, workspace_path)

    # NEW: scan ingested source files and save inventory
    file_inventory = scan_project_files(workspace_path)
    save_file_inventory(workspace_path, file_inventory)

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
    


def extract_zip_to_workspace(zip_path: str, workspace_path: str) -> None:
    source_dir = os.path.join(workspace_path, "source")

    if not os.path.exists(zip_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ZIP file not found at path: {zip_path}"
        )

    if not zip_path.lower().endswith(".zip"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provided source file is not a ZIP file"
        )

    # Prevent extraction into a non-empty source dir
    if os.path.exists(source_dir) and os.listdir(source_dir):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source directory is not empty, cannot extract ZIP"
        )

    try:
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(source_dir)
    except zipfile.BadZipFile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is not a valid ZIP archive"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to extract ZIP file: {str(e)}"
        )
    

def copy_local_repo_to_workspace(local_repo_path: str, workspace_path: str) -> None:
    source_dir = os.path.join(workspace_path, "source")

    if not os.path.exists(local_repo_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Local repository path not found: {local_repo_path}"
        )

    if not os.path.isdir(local_repo_path):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provided local repository path is not a directory"
        )

    # Prevent copying into a non-empty source dir
    if os.path.exists(source_dir) and os.listdir(source_dir):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source directory is not empty, cannot copy local repository"
        )

    try:
        # Copy the CONTENTS of local repo into source_dir
        for item in os.listdir(local_repo_path):
            src_item = os.path.join(local_repo_path, item)
            dst_item = os.path.join(source_dir, item)

            if os.path.isdir(src_item):
                shutil.copytree(src_item, dst_item)
            else:
                shutil.copy2(src_item, dst_item)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to copy local repository: {str(e)}"
        )
    

def scan_project_files(workspace_path: str) -> list[dict]:
    source_dir = os.path.join(workspace_path, "source")

    if not os.path.exists(source_dir):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source directory not found for workspace: {workspace_path}"
        )

    file_inventory = []

    for root, dirs, files in os.walk(source_dir):
        # Remove ignored directories from traversal
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        for file_name in files:
            file_path = os.path.join(root, file_name)

            try:
                relative_path = os.path.relpath(file_path, source_dir)
                extension = os.path.splitext(file_name)[1]
                size_bytes = os.path.getsize(file_path)

                file_inventory.append({
                    "relative_path": relative_path,
                    "file_name": file_name,
                    "extension": extension,
                    "absolute_path": file_path,
                    "size_bytes": size_bytes
                })
            except Exception:
                # Skip problematic files rather than breaking the whole scan
                continue

    return file_inventory

def save_file_inventory(workspace_path: str, file_inventory: list[dict]) -> str:
    artifacts_dir = os.path.join(workspace_path, "artifacts")
    os.makedirs(artifacts_dir, exist_ok=True)

    inventory_path = os.path.join(artifacts_dir, "file_inventory.json")

    with open(inventory_path, "w", encoding="utf-8") as f:
        json.dump(file_inventory, f, indent=4)

    return inventory_path