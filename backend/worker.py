"""
Celery worker entry point.
This file ensures proper task discovery when starting the Celery worker.
"""

import os
import sys

# Add the parent directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the Celery app and ensure tasks are loaded
from app.task_queue.task_queue import celery_app

# Import all task modules to ensure they are registered
from app.task_queue import task_queue

# This will ensure tasks are discovered
if __name__ == '__main__':
    celery_app.start()
