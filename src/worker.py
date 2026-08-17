"""
Background job runner with queue - single job at a time
"""
import threading
import queue
import time
import traceback
from typing import Callable, Dict, Any, Optional
from pathlib import Path


class Job:
    """Represents a background job."""
    def __init__(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        on_progress: Callable[[int, str], None] = None,
        on_complete: Callable[[Dict[str, Any]], None] = None,
        on_error: Callable[[str], None] = None,
        name: str = "Job",
    ):
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error
        self.name = name
        self.cancelled = False
        self._thread: Optional[threading.Thread] = None


class JobRunner:
    """Manages a queue of jobs, running one at a time."""
    
    def __init__(self, ui_callback: Callable = None):
        self._queue: queue.Queue[Job] = queue.Queue()
        self._current_job: Optional[Job] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._ui_callback = ui_callback  # Called on UI thread via after()
        
    def submit(
        self,
        func: Callable,
        args: tuple = (),
        kwargs: dict = None,
        on_progress: Callable[[int, str], None] = None,
        on_complete: Callable[[Dict[str, Any]], None] = None,
        on_error: Callable[[str], None] = None,
        name: str = "Job",
    ) -> Job:
        """Submit a job to the queue."""
        job = Job(func, args, kwargs, on_progress, on_complete, on_error, name)
        self._queue.put(job)
        if not self._running:
            self._start_worker()
        return job
    
    def _start_worker(self):
        """Start the background worker thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._worker_thread = threading.Thread(target=self._run_loop, daemon=True)
            self._worker_thread.start()
    
    def _run_loop(self):
        """Main worker loop - processes jobs sequentially."""
        while self._running:
            try:
                # Wait for next job (with timeout to check _running)
                job = self._queue.get(timeout=0.5)
            except queue.Empty:
                continue
            
            self._current_job = job
            self._execute_job(job)
            self._current_job = None
            self._queue.task_done()
        
        # Worker stopped
        with self._lock:
            self._running = False
    
    def _execute_job(self, job: Job):
        """Execute a single job with progress reporting."""
        def progress_cb(percent: int, message: str):
            if job.cancelled:
                raise RuntimeError("Job cancelled")
            if job.on_progress:
                # Schedule on UI thread
                if self._ui_callback:
                    self._ui_callback(lambda: job.on_progress(percent, message))
                else:
                    job.on_progress(percent, message)
        
        try:
            # Inject progress callback into kwargs if function accepts it
            import inspect
            sig = inspect.signature(job.func)
            if 'progress_cb' in sig.parameters:
                job.kwargs['progress_cb'] = progress_cb
            
            result = job.func(*job.args, **job.kwargs)
            
            if not job.cancelled and job.on_complete:
                if self._ui_callback:
                    self._ui_callback(lambda: job.on_complete(result))
                else:
                    job.on_complete(result)
                    
        except Exception as e:
            if not job.cancelled:
                error_msg = f"{type(e).__name__}: {e}"
                traceback.print_exc()
                if job.on_error:
                    if self._ui_callback:
                        self._ui_callback(lambda: job.on_error(error_msg))
                    else:
                        job.on_error(error_msg)
    
    def cancel_current(self):
        """Cancel the currently running job."""
        if self._current_job:
            self._current_job.cancelled = True
    
    def cancel_all(self):
        """Cancel current job and clear queue."""
        self.cancel_current()
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except queue.Empty:
                break
    
    def is_busy(self) -> bool:
        """Check if a job is currently running."""
        return self._current_job is not None
    
    def queue_size(self) -> int:
        """Get number of pending jobs."""
        return self._queue.qsize()
    
    def shutdown(self):
        """Stop the worker thread."""
        self.cancel_all()
        self._running = False
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=2.0)


# Global job runner instance
_job_runner: Optional[JobRunner] = None


def get_job_runner(ui_callback: Callable = None) -> JobRunner:
    """Get or create the global job runner."""
    global _job_runner
    if _job_runner is None:
        _job_runner = JobRunner(ui_callback)
    elif ui_callback and _job_runner._ui_callback is None:
        _job_runner._ui_callback = ui_callback
    return _job_runner


def run_job(
    func: Callable,
    args: tuple = (),
    kwargs: dict = None,
    on_progress: Callable[[int, str], None] = None,
    on_complete: Callable[[Dict[str, Any]], None] = None,
    on_error: Callable[[str], None] = None,
    name: str = "Job",
) -> Job:
    """Convenience function to submit a job to the global runner."""
    runner = get_job_runner()
    return runner.submit(func, args, kwargs, on_progress, on_complete, on_error, name)


def is_job_running() -> bool:
    """Check if any job is currently running."""
    runner = get_job_runner()
    return runner.is_busy()