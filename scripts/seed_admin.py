from app.database import SessionLocal
from app.models import AdminUser, AdminRole
from app.domains.admin_auth.services.security_service import SecurityService

db = SessionLocal()

# CHANGE THIS PASSWORD
password = "Veer@1483815" 
pwd_hash = SecurityService.get_password_hash(password)

# Check if exists
exists = db.query(AdminUser).filter(AdminUser.username == "admin").first()
if not exists:
    admin = AdminUser(
        username="Veer",
        email="veeramundaganur@gmail.com",
        hashed_password=pwd_hash,
        role=AdminRole.SUPERADMIN
    )
    db.add(admin)
    db.commit()
    print(f"Super Admin 'admin' created with password '{password}'")
else:
    print("Admin user already exists.")