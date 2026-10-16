import argparse
import sys
import getpass
from app.core.database import SessionLocal, check_db_connection
from app.services.auth_service import auth_service
from app.core.security import validate_password_strength
from app.core.logging import setup_logging, logger


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description="Forging CMS Administrative CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # create-superadmin command
    create_admin_parser = subparsers.add_parser("create-superadmin", help="Create or bootstrap a Super Admin user")
    create_admin_parser.add_argument("--email", "-e", help="Super Admin Email address")
    create_admin_parser.add_argument("--name", "-n", help="Super Admin Full Name")
    create_admin_parser.add_argument("--password", "-p", help="Super Admin Password (leave blank for secure prompt)")

    # seed-cms command
    subparsers.add_parser("seed-cms", help="Seed initial Phase 3 manufacturing CMS modules")

    args = parser.parse_args()

    if args.command == "seed-cms":
        if not check_db_connection():
            print("ERROR: Database connection failed. Please check your DATABASE_URL configuration.")
            sys.exit(1)
        from app.services.seed_service import seed_cms_data
        db = SessionLocal()
        try:
            stats = seed_cms_data(db)
            print(f"SUCCESS: CMS seeded with initial data: {stats}")
        finally:
            db.close()
        return

    if args.command == "create-superadmin":
        if not check_db_connection():
            print("ERROR: Database connection failed. Please check your DATABASE_URL configuration.")
            sys.exit(1)

        email = args.email or input("Enter Super Admin Email: ").strip()
        name = args.name or input("Enter Super Admin Full Name: ").strip()

        password = args.password
        if not password:
            password = getpass.getpass("Enter Super Admin Password: ")
            password_confirm = getpass.getpass("Confirm Password: ")
            if password != password_confirm:
                print("ERROR: Passwords do not match.")
                sys.exit(1)

        is_valid, msg = validate_password_strength(password)
        if not is_valid:
            print(f"ERROR: Weak password - {msg}")
            sys.exit(1)

        db = SessionLocal()
        try:
            user = auth_service.bootstrap_superadmin(
                db=db,
                email=email,
                password=password,
                full_name=name,
            )
            if user:
                print(f"SUCCESS: Super Admin created successfully: {user.email} (ID: {user.id})")
            else:
                print(f"NOTICE: User with email '{email}' already exists or super admin already initialized.")
        finally:
            db.close()


if __name__ == "__main__":
    main()
