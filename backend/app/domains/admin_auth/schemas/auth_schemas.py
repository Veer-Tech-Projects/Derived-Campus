from pydantic import BaseModel, EmailStr, Field
from typing import Optional, Any, Dict
from datetime import datetime
from uuid import UUID
from enum import Enum

# Re-declare Enum for Pydantic to avoid circular imports
class AdminRole(str, Enum):
    SUPERADMIN = "SUPERADMIN"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"

# --- EXISTING SCHEMAS (Preserved) ---
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None
    
class AdminLoginRequest(BaseModel):
    username: str
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# --- NEW: ADMIN MANAGEMENT SCHEMAS ---

class AdminCreateRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: AdminRole

class AdminResponse(BaseModel):
    id: UUID
    username: str
    email: str
    role: AdminRole
    is_active: bool
    last_login_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class AdminUpdateRequest(BaseModel):
    role: Optional[AdminRole] = None
    is_active: Optional[bool] = None
    password: Optional[str] = None

# --- NEW: AUDIT LOG SCHEMAS ---

class AuditLogResponse(BaseModel):
    id: UUID
    admin_username: Optional[str] # Flattened from relationship
    action: str
    target_resource: Optional[str]
    details: Optional[Dict[str, Any]]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True