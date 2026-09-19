"""Local administrative commands for the first QA account."""

import argparse
from getpass import getpass

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db import models  # noqa: F401
from app.db.session import get_engine
from app.db.types import UserRole
from app.modules.auth.models import User
from app.modules.auth.schemas import RegisterRequest


def main() -> None:
    parser = argparse.ArgumentParser(description="LoadForge local administration")
    commands = parser.add_subparsers(dest="command", required=True)
    bootstrap = commands.add_parser("create-qa", help="Create the first QA account")
    bootstrap.add_argument("--name", required=True)
    bootstrap.add_argument("--email", required=True)
    args = parser.parse_args()

    password = getpass("Password (at least 12 characters): ")
    confirmation = getpass("Repeat password: ")
    if password != confirmation:
        parser.exit(1, "Passwords do not match.\n")
    try:
        request = RegisterRequest(
            full_name=args.name, email=args.email, password=password
        )
    except ValidationError as exc:
        parser.exit(1, f"Invalid account data: {exc}\n")

    with Session(get_engine()) as db:
        if db.scalar(select(User.id).where(User.role == UserRole.QA).limit(1)):
            parser.exit(1, "A QA account already exists. Use the authenticated API.\n")
        user = User(
            full_name=request.full_name,
            email=str(request.email).lower(),
            password_hash=hash_password(request.password),
            role=UserRole.QA,
        )
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            parser.exit(1, "This email is already registered.\n")
    print("First QA account created.")


if __name__ == "__main__":
    main()
