import concurrent.futures
import threading
import time
import random

from apiculture_api.util.config import TASK_RUNNER_RANDOM_DELAY_CEILING


class TaskRunner:
    """
    A class to run periodic tasks using ThreadPoolExecutor with graceful shutdown support.

    Args:
    tasks (list): List of tuples (task_func, task_args, task_interval) where:
                  - task_func is a callable function to execute periodically
                  - task_args is a tuple of arguments to pass to task_func (or None for no args)
                  - task_interval is the time in seconds between executions for this task
                    (or None to use default_interval)
    default_interval (int): Default time in seconds between executions (default: 300 seconds = 5 minutes).

    Each task will have a random initial delay between 1 and 100 seconds before the first execution,
    to stagger the starts.

    Example usage:
    def task1(param):
        print(f"Task 1 executed with {param}")

    def task2():
        print("Task 2 executed")

    tasks = [(task1, ('hello',), 300), (task2, None, 600)]
    runner = TaskRunner(tasks, default_interval=300)

    # To keep the main program running (optional)
    # time.sleep(3600)  # Run for 1 hour

    # To stop gracefully
    runner.shutdown(wait=True)
    """

    def __init__(self, tasks, default_interval=300):
        self.stop_event = threading.Event()
        self.default_interval = default_interval
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=len(tasks))
        self.futures = []
        for task_func, task_args, task_interval in tasks:
            interval = task_interval if task_interval is not None else default_interval
            self.futures.append(
                self.executor.submit(self._periodic_runner, task_func, task_args, interval, self.stop_event))

    def _periodic_runner(self, task_func, task_args, interval, stop_event):
        # Random initial delay to stagger starts (1 to 100 seconds)
        time.sleep(random.uniform(1, TASK_RUNNER_RANDOM_DELAY_CEILING))

        while not stop_event.is_set():
            try:
                if task_args:
                    task_func(*task_args)
                else:
                    task_func()
            except Exception as e:
                print(f"Error in task: {e}")
            stop_event.wait(interval)

    def shutdown(self, wait=True):
        """Gracefully stop all tasks."""
        self.stop_event.set()
        self.executor.shutdown(wait=wait)