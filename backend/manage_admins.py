import sys
import getpass
import uuid
from typing import Optional
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import AdminUser, AdminRole
from app.domains.admin_auth.services.security_service import SecurityService

# --- UTILS ---
def get_db():
    return SessionLocal()

def print_header(title: str):
    print(f"\n{'='*60}")
    print(f" {title.upper()}")
    print(f"{'='*60}")

def get_input(prompt: str, required: bool = True, default: str = None) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        value = input(f"{prompt}{suffix}: ").strip()
        if not value and default:
            return default
        if not value and required:
            print("❌ Value is required.")
            continue
        return value

def get_secure_input(prompt: str, confirm: bool = True) -> Optional[str]:
    while True:
        pwd = getpass.getpass(f"{prompt}: ").strip()
        if not pwd:
            print("❌ Password cannot be empty.")
            continue
        
        if confirm:
            conf = getpass.getpass(f"Confirm {prompt}: ").strip()
            if pwd != conf:
                print("❌ Passwords do not match. Try again.")
                continue
        return pwd

def select_role(current: str = None) -> AdminRole:
    roles = [r.value for r in AdminRole]
    print("\nAvailable Roles:")
    for i, r in enumerate(roles, 1):
        print(f"  {i}. {r}")
    
    while True:
        prompt = "Select Role Number"
        if current:
            prompt += f" (Leave empty for {current})"
        
        choice = input(f"{prompt}: ").strip()
        
        if not choice and current:
            return AdminRole(current)
            
        if choice.isdigit() and 1 <= int(choice) <= len(roles):
            return AdminRole(roles[int(choice)-1])
        print("❌ Invalid selection.")

# --- ACTIONS ---

def list_admins(db: Session, return_list: bool = False):
    admins = db.query(AdminUser).order_by(AdminUser.created_at).all()
    print_header("Existing Admins")
    print(f"{'ID':<4} | {'Username':<15} | {'Role':<12} | {'Status':<8} | {'Email'}")
    print("-" * 60)
    for idx, admin in enumerate(admins, 1):
        status = "Active" if admin.is_active else "Inactive"
        print(f"{idx:<4} | {admin.username:<15} | {admin.role.value:<12} | {status:<8} | {admin.email}")
    
    if return_list:
        return admins
    return None

def seed_admin(db: Session):
    print_header("Seed New Admin")
    try:
        username = get_input("Username")
        if db.query(AdminUser).filter(AdminUser.username == username).first():
            print(f"❌ User '{username}' already exists.")
            return

        email = get_input("Email")
        if db.query(AdminUser).filter(AdminUser.email == email).first():
            print(f"❌ Email '{email}' already exists.")
            return

        password = get_secure_input("Password")
        role = select_role()

        hashed = SecurityService.get_password_hash(password)
        
        new_admin = AdminUser(
            username=username,
            email=email,
            hashed_password=hashed,
            role=role,
            is_active=True
        )
        db.add(new_admin)
        db.commit()
        print(f"\n✅ Successfully created admin: {username} ({role.value})")
    except Exception as e:
        print(f"\n❌ Error seeding admin: {e}")

def delete_admin(db: Session):
    admins = list_admins(db, return_list=True)
    if not admins:
        print("No admins found.")
        return

    try:
        choice = get_input("\nEnter ID # to DELETE (or 'c' to cancel)")
        if choice.lower() == 'c': return

        if not choice.isdigit() or not (1 <= int(choice) <= len(admins)):
            print("❌ Invalid selection.")
            return

        target = admins[int(choice)-1]
        confirm = get_input(f"⚠️  Are you SURE you want to DELETE '{target.username}'? (yes/no)", required=True)
        
        if confirm.lower() == "yes":
            db.delete(target)
            db.commit()
            print(f"✅ Deleted user {target.username}")
        else:
            print("🚫 Operation cancelled.")
    except Exception as e:
        print(f"❌ Error: {e}")

def update_admin(db: Session):
    admins = list_admins(db, return_list=True)
    if not admins:
        print("No admins found.")
        return

    try:
        choice = get_input("\nEnter ID # to UPDATE (or 'c' to cancel)")
        if choice.lower() == 'c': return

        if not choice.isdigit() or not (1 <= int(choice) <= len(admins)):
            print("❌ Invalid selection.")
            return

        target = admins[int(choice)-1]
        print(f"\nUpdating User: {target.username}")
        print("(Press Enter to keep current value)")

        # Username
        new_user = get_input("New Username", required=False, default=target.username)
        if new_user != target.username:
            if db.query(AdminUser).filter(AdminUser.username == new_user).first():
                print(f"❌ Username '{new_user}' taken. Keeping old one.")
                new_user = target.username
        
        # Email
        new_email = get_input("New Email", required=False, default=target.email)
        
        # Role
        new_role = select_role(current=target.role.value)
        
        # Password (Optional)
        change_pwd = get_input("Change Password? (y/n)", required=True).lower()
        new_hash = target.hashed_password
        if change_pwd == 'y':
            new_pwd = get_secure_input("New Password")
            new_hash = SecurityService.get_password_hash(new_pwd)

        # Apply
        target.username = new_user
        target.email = new_email
        target.role = new_role
        target.hashed_password = new_hash
        
        db.commit()
        print(f"\n✅ Successfully updated {target.username}")

    except Exception as e:
        print(f"❌ Error: {e}")

# --- MAIN LOOP ---
def main():
    db = get_db()
    try:
        while True:
            print_header("Admin Management Console")
            print("1. Seed (Create New Admin)")
            print("2. List & Update Admin")
            print("3. Delete Admin")
            print("4. Exit")
            
            choice = input("\nSelect Option: ").strip()
            
            if choice == "1":
                seed_admin(db)
            elif choice == "2":
                update_admin(db)
            elif choice == "3":
                delete_admin(db)
            elif choice == "4":
                print("Exiting...")
                break
            else:
                print("❌ Invalid option")
            
            input("\nPress Enter to continue...")
    finally:
        db.close()

if __name__ == "__main__":
    main()