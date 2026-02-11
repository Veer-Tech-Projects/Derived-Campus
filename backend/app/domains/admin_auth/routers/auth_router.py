from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone # <--- Added timezone
from jose import jwt, JWTError

from app.domains.admin_auth.services.auth_dependency import get_db, get_current_admin
from app.domains.admin_auth.services.security_service import SecurityService
from app.domains.admin_auth.schemas.auth_schemas import AdminLoginRequest, Token
from app.domains.admin_auth.config import auth_settings
from app.models import AdminUser, AdminAuditTrail

router = APIRouter(prefix="/auth", tags=["Admin Security"])

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 30

@router.post("/login", response_model=Token)
def login_for_access_token(
    response: Response,
    form_data: AdminLoginRequest,
    db: Session = Depends(get_db)
):
    # 1. Fetch User
    admin = db.query(AdminUser).filter(AdminUser.username == form_data.username).first()
    
    # 2. FAIL-FAST: Lockout Check (Timezone Aware Fix)
    if admin and admin.locked_until:
        # [FIX] Use timezone-aware UTC time for comparison
        now_utc = datetime.now(timezone.utc)
        
        if admin.locked_until > now_utc:
            remaining = int((admin.locked_until - now_utc).total_seconds() / 60)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Account locked. Try again in {remaining} minutes.",
            )
        else:
            # Auto-reset if lock expired
            admin.locked_until = None
            admin.failed_login_attempts = 0
            db.add(admin)
            db.commit()
            db.refresh(admin)

    # 3. Verify Credentials
    valid_password = False
    if admin:
        valid_password = SecurityService.verify_password(form_data.password, admin.hashed_password)

    if not valid_password:
        # [FIX] Initialize default message HERE to prevent UnboundLocalError
        error_msg = "Incorrect username or password"
        
        if admin:
            # --- LOCKING LOGIC ---
            admin.failed_login_attempts += 1
            
            if admin.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
                # [FIX] Use timezone-aware UTC time for setting lock
                admin.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_DURATION_MINUTES)
                
                audit = AdminAuditTrail(
                    admin_id=admin.id, 
                    action="ACCOUNT_LOCKED", 
                    details={"reason": "brute_force", "attempts": admin.failed_login_attempts}
                )
                db.add(audit)
            
            db.add(admin)
            db.commit()
            
            # Construct Warning Message
            remaining = MAX_FAILED_ATTEMPTS - admin.failed_login_attempts
            if remaining <= 2 and remaining > 0:
                error_msg += f". Warning: Lockout in {remaining} attempts."
            
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_msg, # Use the safely initialized variable
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 4. Check Account Status
    if not admin.is_active:
        raise HTTPException(status_code=400, detail="Account is disabled")

    # 5. Success
    admin.failed_login_attempts = 0
    admin.locked_until = None
    # [FIX] Use timezone-aware UTC
    admin.last_login_at = datetime.now(timezone.utc)
    
    audit = AdminAuditTrail(admin_id=admin.id, action="LOGIN", details={"status": "success"})
    db.add(audit)
    db.commit()

    # --- GENERATE FINGERPRINT ---
    fingerprint = SecurityService.generate_fingerprint(admin.hashed_password)

    access_token = SecurityService.create_access_token(
        subject=str(admin.id), 
        role=admin.role.value,
        credential_fingerprint=fingerprint
    )
    refresh_token = SecurityService.create_refresh_token(
        subject=str(admin.id),
        credential_fingerprint=fingerprint
    )

    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=False, 
        samesite="lax",
        max_age=7 * 24 * 60 * 60 
    )

    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/refresh", response_model=Token)
def refresh_token(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    try:
        payload = jwt.decode(
            refresh_token, 
            auth_settings.SECRET_KEY, 
            algorithms=[auth_settings.ALGORITHM]
        )
        user_id: str = payload.get("sub")
        token_type: str = payload.get("type")
        token_fingerprint: str = payload.get("fingerprint")

        if user_id is None or token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token")
            
        import uuid
        admin = db.query(AdminUser).filter(AdminUser.id == uuid.UUID(user_id)).first()
        
        if not admin or not admin.is_active:
             raise HTTPException(status_code=401, detail="User inactive")
             
        # --- VERIFY FINGERPRINT ---
        current_fingerprint = SecurityService.generate_fingerprint(admin.hashed_password)
        if token_fingerprint != current_fingerprint:
            raise HTTPException(status_code=401, detail="Session expired (Password Changed)")

    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    new_access_token = SecurityService.create_access_token(
        subject=str(admin.id),
        role=admin.role.value,
        credential_fingerprint=current_fingerprint
    )
    
    return {"access_token": new_access_token, "token_type": "bearer"}

@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"message": "Logged out successfully"}

@router.get("/me")
def read_users_me(current_admin: AdminUser = Depends(get_current_admin)):
    return {
        "id": str(current_admin.id),
        "username": current_admin.username,
        "role": current_admin.role,
        "email": current_admin.email
    }