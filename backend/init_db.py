from backend.database import Base, engine
from backend.models.user import User

Base.metadata.create_all(bind=engine)

print("Database initialized successfully")