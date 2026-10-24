"""Background jobs (translation, classification, offline transcription, media clean-up).

Jobs are queued on the database session and sent only after the request commits, so a job never
looks for a row that is not saved yet. JOBS_MODE picks how they run:
  rq     - Redis queue, processed by the `worker` container (production)
  thread - small in-process thread pool (development without Redis)
  sync   - right after commit, in the same thread (tests)
"""
import logging
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy import event
from sqlalchemy.orm import Session

from .config import get_config

log = logging.getLogger("thunai.jobs")
_pool: ThreadPoolExecutor | None = None
QUEUE = "thunai"


def run_task(name: str, **kwargs) -> None:
    from . import tasks

    try:
        getattr(tasks, name)(**kwargs)
    except Exception:  # a failed job must never break the request that queued it
        log.exception("Job %s failed (%s)", name, kwargs)
        if get_config().jobs_mode == "rq":
            raise


def enqueue(db: Session, name: str, **kwargs) -> None:
    db.info.setdefault("pending_jobs", []).append((name, kwargs))


def _dispatch(name: str, kwargs: dict) -> None:
    global _pool
    mode = get_config().jobs_mode
    if mode == "rq":
        from redis import Redis
        from rq import Queue

        Queue(QUEUE, connection=Redis.from_url(get_config().redis_url)).enqueue_call(
            func=run_task, args=(name,), kwargs=kwargs, timeout=600
        )
    elif mode == "sync":
        run_task(name, **kwargs)
    else:
        if _pool is None:
            _pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="thunai-job")
        _pool.submit(run_task, name, **kwargs)


@event.listens_for(Session, "after_commit")
def _after_commit(session: Session) -> None:
    pending = session.info.pop("pending_jobs", [])
    for name, kwargs in pending:
        try:
            _dispatch(name, kwargs)
        except Exception:
            log.exception("Could not queue job %s", name)


@event.listens_for(Session, "after_rollback")
def _after_rollback(session: Session) -> None:
    session.info.pop("pending_jobs", None)
