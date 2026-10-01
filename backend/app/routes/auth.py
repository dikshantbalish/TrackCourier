from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.admin import AdminUser
from app.schemas.auth import AdminLoginRequest, AdminLoginResponse, AdminResponse
from app.services.authentication import authenticate_admin

router = APIRouter(prefix="/api/auth", tags=["admin authentication"])


def require_admin(request: Request, database: Session = Depends(get_db)) -> AdminUser:
    admin_id = request.session.get("admin_id")
    if not isinstance(admin_id, int):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    admin = database.get(AdminUser, admin_id)
    if admin is None or request.session.get("session_version") != admin.session_version:
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )
    return admin


@router.post("/login", response_model=AdminLoginResponse)
def login(
    credentials: AdminLoginRequest, request: Request, database: Session = Depends(get_db)
) -> AdminLoginResponse:
    admin = authenticate_admin(database, credentials.username, credentials.password)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    request.session.clear()
    request.session["admin_id"] = admin.id
    request.session["session_version"] = admin.session_version
    return AdminLoginResponse(username=admin.username)


@router.get("/me", response_model=AdminResponse)
def current_admin(admin: AdminUser = Depends(require_admin)) -> AdminUser:
    return admin


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request) -> None:
    request.session.clear()
