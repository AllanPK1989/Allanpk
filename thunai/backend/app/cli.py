"""Admin commands: python -m app.cli <command>

  init                 seed SAMPLE data when the database is empty and SEED_SAMPLE_DATA=true
  seed                 seed SAMPLE data (only into an empty database)
  create-admin         create an admin user: --employee-id E123 --name "Name" --pin 4321
  purge-media          delete audio files older than the retention period (run nightly)
"""
import argparse
import sys

from sqlalchemy import func, select

from . import jobs  # noqa: F401  (job hooks)
from . import audit, seed, tasks
from .config import get_config
from .db import SessionLocal
from .models import User
from .security import hash_pin, valid_pin


def cmd_init(_args) -> int:
    with SessionLocal() as db:
        if seed.is_empty(db) and get_config().seed_sample_data:
            seed.seed(db)
            db.commit()
            print("Seeded SAMPLE data. Sample users: D-ADMIN, D-SUP1, D-TECH1 (PIN 1234).")
        elif seed.is_empty(db):
            print("Database is empty. Create the first admin: python -m app.cli create-admin ...")
        else:
            print("Database already has data; nothing to seed.")
    return 0


def cmd_seed(_args) -> int:
    with SessionLocal() as db:
        if not seed.is_empty(db):
            print("Refusing to seed: the database already has users.", file=sys.stderr)
            return 1
        seed.seed(db)
        db.commit()
    print("Seeded SAMPLE data.")
    return 0


def cmd_create_admin(args) -> int:
    if not valid_pin(args.pin):
        print("PIN must be 4 digits", file=sys.stderr)
        return 1
    with SessionLocal() as db:
        emp = args.employee_id.strip().upper()
        if db.scalar(select(User).where(func.upper(User.employee_id) == emp)):
            print(f"{emp} already exists", file=sys.stderr)
            return 1
        user = User(employee_id=emp, name=args.name, role="admin", preferred_language="en", pin_hash=hash_pin(args.pin))
        db.add(user)
        db.flush()
        audit.record(db, None, "user", emp, "create", None, audit.snapshot(user))
        db.commit()
    print(f"Admin {emp} created.")
    return 0


def cmd_purge_media(_args) -> int:
    print(f"Purged {tasks.purge_expired_media()} files.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    sub.add_parser("seed")
    p = sub.add_parser("create-admin")
    p.add_argument("--employee-id", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--pin", required=True)
    sub.add_parser("purge-media")
    args = parser.parse_args(argv)
    handler = {
        "init": cmd_init,
        "seed": cmd_seed,
        "create-admin": cmd_create_admin,
        "purge-media": cmd_purge_media,
    }[args.command]
    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
