"""Local administrative commands for the first QA account."""

import argparse
import json
from getpass import getpass
from pathlib import Path

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
    commands.add_parser("check-db", help="Validate migrated PostgreSQL without changing data")
    export = commands.add_parser('export-openapi', help='Export the public API contract without a database connection')
    export.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()

    if args.command == 'export-openapi':
        from app.main import app
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(app.openapi(), ensure_ascii=False, sort_keys=True, indent=2)+'\n', encoding='utf-8')
        print('OpenAPI contract exported.')
        return

    if args.command == 'check-db':
        from app.db.validation import validate_database
        with get_engine().connect() as connection:
            result = validate_database(connection)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(0 if result['ok'] else 1)

    password = getpass("Password (at least 12 characters): ")
    confirmation = getpass("Repeat password: ")
    if password != confirmation:
        parser.exit(1, "Passwords do not match.\n")
    try:
        request = RegisterRequest(
            full_name=args.name, email=args.email, password=password
        )
    except ValidationError as exc:
        fields = ', '.join('.'.join(str(part) for part in error['loc']) for error in exc.errors())
        parser.exit(1, f"Invalid account fields: {fields}. Passwords require at least 12 characters.\n")

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
