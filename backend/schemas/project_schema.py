from pydantic import BaseModel, Field, HttpUrl
from typing import Literal


class ProjectRegisterRequest(BaseModel):
    persona: Literal["SDE", "PM"]
    source_type: Literal["github", "zip", "local_git"]
    source_value: str = Field(..., min_length=1, max_length=500)


class ProjectRegisterResponse(BaseModel):
    project_id: str
    persona: str
    source_type: str
    source_value: str
    status: str
    message: str