from datetime import datetime, timedelta
from typing import Optional, Union, Any
from jose import jwt
from passlib.context import CryptContext
import hashlib  # <--- NEW IMPORT
from app.domains.admin_auth.config import auth_settings

# --- CRYPTO CONTEXT (ARGON2) ---
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

class SecurityService:
    
    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    @staticmethod
    def generate_fingerprint(hashed_password: str) -> str:
        """
        Creates a deterministic, opaque fingerprint of the current password hash.
        If the password changes, this fingerprint changes, invalidating old tokens.
        """
        # We hash the hash to avoid exposing Argon2 parameters or salt in the JWT
        return hashlib.sha256(hashed_password.encode()).hexdigest()[:16]

    @staticmethod
    def create_access_token(
        subject: Union[str, Any], 
        role: str, 
        credential_fingerprint: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=auth_settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode = {
            "sub": str(subject),
            "role": role,
            "type": "access",
            "fingerprint": credential_fingerprint,
            "exp": expire
        }
        
        encoded_jwt = jwt.encode(to_encode, auth_settings.SECRET_KEY, algorithm=auth_settings.ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(
        subject: Union[str, Any],
        credential_fingerprint: str
    ) -> str:
        expire = datetime.utcnow() + timedelta(days=auth_settings.REFRESH_TOKEN_EXPIRE_DAYS)
        
        to_encode = {
            "sub": str(subject),
            "type": "refresh",
            "fingerprint": credential_fingerprint,
            "exp": expire
        }
        
        encoded_jwt = jwt.encode(to_encode, auth_settings.SECRET_KEY, algorithm=auth_settings.ALGORITHM)
        return encoded_jwt