from pydantic import BaseModel, Field, HttpUrl
from typing import Literal


class ProjectRegisterRequest(BaseModel):
    persona: Literal["SDE", "PM"]
    github_url: HttpUrl


class ProjectRegisterResponse(BaseModel):
    project_id: str
    persona: str
    source_type: str
    source_value: str
    status: str
    message: str