from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(String, unique=True, index=True, nullable=False)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    persona = Column(String, nullable=False)         # SDE / PM
    source_type = Column(String, nullable=False)     # github for now
    source_value = Column(String, nullable=False)    # github url
    status = Column(String, nullable=False, default="REGISTERED")

    user = relationship("User")