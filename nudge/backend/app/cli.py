"""Admin commands:  python -m app.cli <command>

  init            create tables, default baskets (and sample data when SEED_SAMPLE_DATA=true)
  set-pin 4321    set a new PIN and log out every device
  clear-sample    delete the demo tasks before you start using Nudge for real
  backup          copy the database to data/backups now
  tick            run the reminder scheduler once (for testing)
"""
import sys

from . import backup, scheduler, security, seed
from .db import SessionLocal
from .main import prepare


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 1
    cmd, args = argv[0], argv[1:]
    if cmd == "init":
        prepare()
        print("Ready.")
        return 0
    db = SessionLocal()
    try:
        if cmd == "set-pin":
            if not args or not security.valid_pin_format(args[0]):
                print("Usage: set-pin <4 to 8 digits>")
                return 1
            security.set_pin(db, args[0])
            security.end_all_sessions(db)
            db.commit()
            print("PIN changed. All devices have been logged out.")
        elif cmd == "clear-sample":
            n = seed.clear_sample(db)
            db.commit()
            print(f"Removed {n} sample tasks.")
        elif cmd == "backup":
            path = backup.run_backup()
            print(f"Saved {path}" if path else "Nothing to back up.")
        elif cmd == "tick":
            print(scheduler.tick(db))
            db.commit()
        else:
            print(__doc__)
            return 1
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
