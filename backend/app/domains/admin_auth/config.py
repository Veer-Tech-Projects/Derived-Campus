import os
from pydantic_settings import BaseSettings

class AuthConfig(BaseSettings):
    # CRITICAL: Change this in production! 
    # run: openssl rand -hex 32
    SECRET_KEY: str = os.getenv("AUTH_SECRET_KEY", "UNSAFE_DEFAULT_CHANGE_THIS_IMMEDIATELY")
    ALGORITHM: str = "HS256"
    
    # 15 Minutes for Access Token (Short-lived for security)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    
    # 7 Days for Refresh Token (Long-lived for UX)
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    class Config:
        env_file = ".env"

auth_settings = AuthConfig()