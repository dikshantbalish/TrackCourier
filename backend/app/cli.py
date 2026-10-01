import argparse
import sys
from getpass import getpass

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.database.connection import SessionLocal
from app.models.admin import AdminUser
from app.services.authentication import (
    ADMIN_PASSWORD_MAX_LENGTH,
    ADMIN_PASSWORD_MIN_LENGTH,
    hash_password,
)


def create_admin() -> int:
    username = input("Admin username: ").strip().casefold()
    if not 3 <= len(username) <= 120:
        print("Username must contain between 3 and 120 characters.", file=sys.stderr)
        return 1

    password = getpass("Admin password (12 to 128 characters): ")
    confirmation = getpass("Confirm password: ")
    if password != confirmation:
        print("Passwords do not match.", file=sys.stderr)
        return 1
    if len(password) < ADMIN_PASSWORD_MIN_LENGTH:
        print(
            f"Password must contain at least {ADMIN_PASSWORD_MIN_LENGTH} characters.",
            file=sys.stderr,
        )
        return 1
    if len(password) > ADMIN_PASSWORD_MAX_LENGTH:
        print(
            f"Password must contain no more than {ADMIN_PASSWORD_MAX_LENGTH} characters.",
            file=sys.stderr,
        )
        return 1

    with SessionLocal() as database:
        if database.scalar(
            select(AdminUser.id).where(func.lower(AdminUser.username) == username)
        ) is not None:
            print("An administrator with that username already exists.", file=sys.stderr)
            return 1
        database.add(AdminUser(username=username, password_hash=hash_password(password)))
        try:
            database.commit()
        except SQLAlchemyError:
            database.rollback()
            print("Unable to create administrator.", file=sys.stderr)
            return 1

    print("Administrator created.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Shree Balaji Couriers backend setup")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("create-admin", help="Interactively create an administrator account")
    arguments = parser.parse_args()
    if arguments.command == "create-admin":
        return create_admin()
    return 2


if __name__ == "__main__":
    sys.exit(main())
