"""
Threading utilities for GUI operations.

Manages background thread execution for non-blocking GUI operations
while maintaining thread safety for Tkinter updates.
"""

import threading
import queue
import concurrent.futures
from typing import Callable, Any, Optional
import time

from hedwig.core.logging_config import get_logger


class GUIThreadManager:
    """
    Manages background threads for GUI operations.
    
    Provides thread pool execution for long-running tasks while keeping
    the GUI responsive and thread-safe.
    """
    
    def __init__(self, max_workers: int = 4):
        """
        Initialize the thread manager.
        
        Args:
            max_workers: Maximum number of background threads
        """
        self.logger = get_logger("hedwig.gui.threading")
        self.max_workers = max_workers
        self.executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        self.active_tasks = set()
        self._shutdown = False
        
        self._start_executor()
    
    def _start_executor(self) -> None:
        """Start the thread pool executor."""
        if self.executor is None or self.executor._shutdown:
            self.executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=self.max_workers,
                thread_name_prefix="hedwig-gui"
            )
            self.logger.info(f"Started thread pool with {self.max_workers} workers")
    
    def submit_task(self, task: Callable[[], Any], callback: Optional[Callable] = None) -> concurrent.futures.Future:
        """
        Submit a task for background execution.
        
        Args:
            task: Function to execute in background
            callback: Optional callback for when task completes
            
        Returns:
            Future object for the submitted task
        """
        if self._shutdown:
            raise RuntimeError("Thread manager has been shut down")
        
        def wrapped_task():
            task_id = id(threading.current_thread())
            self.active_tasks.add(task_id)
            
            try:
                self.logger.debug(f"Starting task {task_id}")
                result = task()
                
                if callback:
                    callback(result)
                
                return result
                
            except Exception as e:
                self.logger.error(f"Task {task_id} failed: {str(e)}")
                raise
            finally:
                self.active_tasks.discard(task_id)
                self.logger.debug(f"Completed task {task_id}")
        
        future = self.executor.submit(wrapped_task)
        return future
    
    def submit_with_progress(self, task: Callable[[Callable], Any], progress_callback: Callable[[int], None]) -> concurrent.futures.Future:
        """
        Submit a task with progress reporting.
        
        Args:
            task: Function that accepts a progress callback
            progress_callback: Function to call with progress updates (0-100)
            
        Returns:
            Future object for the submitted task
        """
        def progress_wrapper(progress: int):
            """Wrapper to safely call progress callback."""
            try:
                progress_callback(max(0, min(100, progress)))
            except Exception as e:
                self.logger.warning(f"Progress callback failed: {str(e)}")
        
        def wrapped_task():
            return task(progress_wrapper)
        
        return self.submit_task(wrapped_task)
    
    def wait_for_completion(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for all active tasks to complete.
        
        Args:
            timeout: Maximum time to wait in seconds
            
        Returns:
            True if all tasks completed, False if timeout occurred
        """
        start_time = time.time()
        
        while self.active_tasks:
            if timeout and (time.time() - start_time) > timeout:
                return False
            time.sleep(0.1)
        
        return True
    
    def cancel_all_tasks(self) -> int:
        """
        Cancel all pending tasks.
        
        Returns:
            Number of tasks that were cancelled
        """
        if not self.executor:
            return 0
        
        # Get pending futures
        cancelled = 0
        futures = list(self.executor._threads.keys()) if hasattr(self.executor, '_threads') else []
        
        for future in futures:
            if future.cancel():
                cancelled += 1
        
        self.logger.info(f"Cancelled {cancelled} pending tasks")
        return cancelled
    
    def get_active_task_count(self) -> int:
        """Get the number of currently active tasks."""
        return len(self.active_tasks)
    
    def is_busy(self) -> bool:
        """Check if any tasks are currently running."""
        return len(self.active_tasks) > 0
    
    def shutdown(self, wait: bool = True, timeout: float = 5.0) -> None:
        """
        Shutdown the thread manager.
        
        Args:
            wait: Whether to wait for active tasks to complete
            timeout: Maximum time to wait for completion
        """
        if self._shutdown:
            return
        
        self._shutdown = True
        self.logger.info("Shutting down thread manager")
        
        if self.executor:
            if wait:
                # Wait for active tasks to complete
                self.wait_for_completion(timeout)
            
            # Cancel any remaining tasks
            cancelled = self.cancel_all_tasks()
            if cancelled > 0:
                self.logger.info(f"Cancelled {cancelled} tasks during shutdown")
            
            # Shutdown the executor
            self.executor.shutdown(wait=wait, timeout=timeout)
            self.executor = None
        
        self.active_tasks.clear()
        self.logger.info("Thread manager shutdown complete")
    
    def restart(self) -> None:
        """Restart the thread manager after shutdown."""
        if not self._shutdown:
            self.shutdown(wait=True)
        
        self._shutdown = False
        self._start_executor()
        self.logger.info("Thread manager restarted")


class ThreadSafeQueue:
    """
    Thread-safe queue for GUI message passing.
    
    Provides a simple interface for passing messages between
    background threads and the GUI thread.
    """
    
    def __init__(self, maxsize: int = 0):
        """
        Initialize the queue.
        
        Args:
            maxsize: Maximum queue size (0 for unlimited)
        """
        self.queue = queue.Queue(maxsize=maxsize)
        self.logger = get_logger("hedwig.gui.queue")
    
    def put(self, item: Any, block: bool = True, timeout: Optional[float] = None) -> None:
        """
        Put an item in the queue.
        
        Args:
            item: Item to add to queue
            block: Whether to block if queue is full
            timeout: Timeout for blocking operations
        """
        try:
            self.queue.put(item, block=block, timeout=timeout)
        except queue.Full:
            self.logger.warning("Queue is full, dropping message")
    
    def get(self, block: bool = True, timeout: Optional[float] = None) -> Any:
        """
        Get an item from the queue.
        
        Args:
            block: Whether to block if queue is empty
            timeout: Timeout for blocking operations
            
        Returns:
            Item from queue
            
        Raises:
            queue.Empty: If queue is empty and not blocking
        """
        return self.queue.get(block=block, timeout=timeout)
    
    def get_nowait(self) -> Any:
        """
        Get an item from the queue without blocking.
        
        Returns:
            Item from queue
            
        Raises:
            queue.Empty: If queue is empty
        """
        return self.queue.get_nowait()
    
    def empty(self) -> bool:
        """Check if the queue is empty."""
        return self.queue.empty()
    
    def qsize(self) -> int:
        """Get the approximate queue size."""
        return self.queue.qsize()
    
    def clear(self) -> int:
        """
        Clear all items from the queue.
        
        Returns:
            Number of items that were removed
        """
        count = 0
        try:
            while True:
                self.queue.get_nowait()
                count += 1
        except queue.Empty:
            pass
        
        if count > 0:
            self.logger.debug(f"Cleared {count} items from queue")
        
        return count


def run_in_background(func: Callable) -> Callable:
    """
    Decorator to run a function in a background thread.
    
    Args:
        func: Function to run in background
        
    Returns:
        Wrapped function that returns a Future
    """
    def wrapper(*args, **kwargs):
        thread_manager = getattr(wrapper, '_thread_manager', None)
        if not thread_manager:
            thread_manager = GUIThreadManager(max_workers=2)
            wrapper._thread_manager = thread_manager
        
        return thread_manager.submit_task(lambda: func(*args, **kwargs))
    
    return wrapper