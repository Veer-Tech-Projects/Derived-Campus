from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.domains.admin_auth.config import auth_settings
from app.domains.admin_auth.services.security_service import SecurityService 
from app.models import AdminUser, AdminRole # Ensure AdminRole is imported
import uuid

# The URL where the frontend can exchange username/password for a token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# --- RBAC HIERARCHY ---
# Higher number = More privilege
ROLE_HIERARCHY = {
    AdminRole.SUPERADMIN: 3,
    AdminRole.EDITOR: 2,
    AdminRole.VIEWER: 1
}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

async def get_current_admin(
    token: str = Depends(oauth2_scheme), 
    db: Session = Depends(get_db)
) -> AdminUser:
    """
    Level 1 Security: Validates JWT Signature & Session Fingerprint.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(
            token, 
            auth_settings.SECRET_KEY, 
            algorithms=[auth_settings.ALGORITHM]
        )
        
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        token_fingerprint: str = payload.get("fingerprint")

        if user_id is None or token_type != "access":
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception

    try:
        # Convert string ID to UUID for DB lookup
        admin = db.query(AdminUser).filter(AdminUser.id == uuid.UUID(user_id)).first()
    except ValueError:
        raise credentials_exception
    
    if admin is None:
        raise credentials_exception
        
    if not admin.is_active:
        raise HTTPException(status_code=400, detail="Inactive admin account")
    
    # Session Invalidation Check
    current_fingerprint = SecurityService.generate_fingerprint(admin.hashed_password)
    if token_fingerprint != current_fingerprint:
        raise credentials_exception

    return admin

# --- LEVEL 2 SECURITY: ROLE ENFORCER ---
def require_role(min_role: AdminRole):
    """
    Factory that creates a dependency to check if the user meets the minimum role rank.
    Usage: Depends(require_role(AdminRole.EDITOR))
    """
    def role_checker(current_admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
        user_rank = ROLE_HIERARCHY.get(current_admin.role, 0)
        required_rank = ROLE_HIERARCHY.get(min_role, 0)

        if user_rank < required_rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient privileges. Required: {min_role.value}"
            )
        return current_admin
    
    return role_checker