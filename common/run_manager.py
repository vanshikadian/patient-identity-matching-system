from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from common.database import SessionLocal
from common.models import MatchRun
from common.pipeline import fail_match_run, run_matching_pipeline


class RunManager:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="match-runner")
        self._lock = Lock()
        self._active_run_id: str | None = None

    def has_active_run(self) -> bool:
        with self._lock:
            return self._active_run_id is not None

    def active_run_id(self) -> str | None:
        with self._lock:
            return self._active_run_id

    def enqueue(self, run_id: str, top_k: int) -> None:
        with self._lock:
            self._active_run_id = run_id
        self._executor.submit(self._run_job, run_id, top_k)

    def _run_job(self, run_id: str, top_k: int) -> None:
        db = SessionLocal()
        try:
            run_matching_pipeline(db, run_id=run_id, top_k=top_k)
        except Exception as exc:  # pragma: no cover
            fail_match_run(db, run_id, str(exc))
        finally:
            db.close()
            with self._lock:
                if self._active_run_id == run_id:
                    self._active_run_id = None


run_manager = RunManager()
