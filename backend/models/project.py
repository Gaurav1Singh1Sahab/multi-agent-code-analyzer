from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from backend.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(String, unique=True, index=True, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    persona = Column(String, nullable=False)
    source_type = Column(String, nullable=False)
    source_value = Column(String, nullable=False)
    status = Column(String, nullable=False, default="REGISTERED")

    created_at = Column(DateTime, default=datetime.utcnow)
    analysis_started_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="projects")