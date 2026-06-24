from fastapi import APIRouter, Depends, status
from backend.models.user import User
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.schemas.user_schema import UserSignup, UserResponse, UserLogin, TokenResponse, CurrentUserResponse
from backend.services.auth_service import create_user, login_user
from backend.utils.auth_dependency import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Signup router
@router.post("/signup", 
             response_model=UserResponse, 
             status_code=status.HTTP_201_CREATED)

def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    return create_user(db, user_data)


#Login Router
@router.post("/login",
             response_model=TokenResponse,
             status_code=status.HTTP_200_OK
             )
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    return login_user(db, user_data)


# Me router
@router.get(
    "/me",
    response_model=CurrentUserResponse,
    status_code=status.HTTP_200_OK,
)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user


