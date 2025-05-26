"""Simplified task queue implementation using Celery and Redis."""

import json
import traceback
import uuid
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List, Union, cast

import redis
from celery import Celery, Task
from celery.result import AsyncResult
from celery.exceptions import Retry

from app.core.execution_engine import ExecutionEngine
from app.config import settings


class TaskState(Enum):
    """Task execution states."""
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


@dataclass
class TaskResult:
    """Task execution result container."""
    task_id: str
    execution_id: str
    state: TaskState
    result: Optional[str] = None
    error: Optional[str] = None
    traceback: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    retries: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert TaskResult to dictionary."""
        data = asdict(self)
        data['state'] = self.state.value
        if self.start_time:
            data['start_time'] = self.start_time.isoformat()
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskResult':
        """Create TaskResult from dictionary."""
        if 'start_time' in data and data['start_time']:
            data['start_time'] = datetime.fromisoformat(data['start_time'])
        if 'end_time' in data and data['end_time']:
            data['end_time'] = datetime.fromisoformat(data['end_time'])
        if 'state' in data:
            data['state'] = TaskState(data['state'])
        return cls(**data)


# Initialize Celery app
celery_app = Celery(
    'crew_tasks',
    broker=getattr(settings, 'redis_url', 'redis://localhost:6379/0'),
    backend=getattr(settings, 'redis_url', 'redis://localhost:6379/0'),
    include=['app.queue.task_queue']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_routes={
        'app.queue.task_queue.execute_crew_task': {'queue': 'crew_execution'},
        'app.queue.task_queue.retry_failed_task': {'queue': 'retry'},
    },
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)


class CrewExecutionTask(Task):
    """Custom Celery task for crew execution with retry logic."""
    
    autoretry_for = (Exception,)
    retry_kwargs = {'max_retries': 3, 'countdown': 60}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


@celery_app.task(bind=True, base=CrewExecutionTask, name='app.queue.task_queue.execute_crew_task')
def execute_crew_task(self, execution_id: str, crew_config: Dict[str, Any], 
                     task_dependencies: Optional[List[str]] = None) -> Dict[str, Any]:
    """Execute a crew task with proper error handling and retry logic."""
    start_time = datetime.utcnow()
    task_id = getattr(self.request, 'id', None) or str(uuid.uuid4())
    
    try:
        # Update task state to STARTED (only if we have a proper Celery context)
        if hasattr(self, 'request') and self.request.id:
            self.update_state(
                state=TaskState.STARTED.value,
                meta={
                    'execution_id': execution_id,
                    'start_time': start_time.isoformat(),
                    'current_step': 'initializing'
                }
            )
        
        # Initialize execution engine
        engine = ExecutionEngine()
        
        # Update progress (only if we have a proper Celery context)
        if hasattr(self, 'request') and self.request.id:
            self.update_state(
                state=TaskState.STARTED.value,
                meta={
                    'execution_id': execution_id,
                    'start_time': start_time.isoformat(),
                    'current_step': 'executing_crew'
                }
            )
        
        # Execute the crew
        result = engine.execute_crew_from_config(crew_config, execution_id)
        
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        
        # Prepare success result
        task_result = {
            "task_id": task_id,
            "execution_id": execution_id,
            "status": result.get("status", "COMPLETED"),
            "result": result.get("result"),
            "error": result.get("error"),
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "execution_time": execution_time,
            "retries": self.request.retries
        }
        
        return task_result
        
    except Exception as exc:
        end_time = datetime.utcnow()
        execution_time = (end_time - start_time).total_seconds()
        
        error_msg = str(exc)
        error_traceback = traceback.format_exc()
        
        # Prepare failure result
        task_result = {
            "task_id": task_id,
            "execution_id": execution_id,
            "status": "FAILED",
            "result": None,
            "error": error_msg,
            "traceback": error_traceback,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "execution_time": execution_time,
            "retries": self.request.retries
        }
        
        # Update task state to FAILURE (only if we have a proper Celery context)
        if hasattr(self, 'request') and self.request.id:
            self.update_state(
                state=TaskState.FAILURE.value,
                meta=task_result
            )
        
        # Raise for retry if retries are available (only in Celery context)
        if hasattr(self, 'request') and self.request.id and self.request.retries < self.max_retries:
            raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
        
        return task_result


@celery_app.task(name='app.queue.task_queue.retry_failed_task')
def retry_failed_task(task_id: str, max_retries: int = 3, countdown: int = 60) -> bool:
    """Retry a failed task."""
    try:
        # Get the original task result
        result = AsyncResult(task_id, app=celery_app)
        
        if result.state == TaskState.FAILURE.value:
            # Retry the task
            execute_crew_task.retry(task_id=task_id, countdown=countdown, max_retries=max_retries)
            return True
        
        return False
        
    except Exception as e:
        print(f"Failed to retry task {task_id}: {str(e)}")
        return False


def cancel_task(task_id: str) -> bool:
    """Cancel a running or pending task."""
    try:
        celery_app.control.revoke(task_id, terminate=True)
        return True
    except Exception as e:
        print(f"Failed to cancel task {task_id}: {str(e)}")
        return False


class TaskQueue:
    """Task queue manager for crew executions."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize TaskQueue."""
        self.celery_app = celery_app
        self.redis_url = redis_url or getattr(settings, 'redis_url', 'redis://localhost:6379/0')
        try:
            self.redis_client = redis.from_url(self.redis_url)
        except Exception as e:
            print(f"Warning: Could not connect to Redis: {e}")
            self.redis_client = None
        
    def submit_crew_execution(self, execution_id: str, crew_config: Dict[str, Any],
                            dependencies: Optional[List[str]] = None,
                            priority: int = 5) -> str:
        """Submit a crew execution to the task queue."""
        # Submit task to Celery
        result = execute_crew_task.apply_async(
            args=[execution_id, crew_config, dependencies],
            priority=priority,
            retry=True
        )
        
        task_id = result.id
        
        # Store basic task metadata in Redis (simplified)
        if self.redis_client:
            try:
                task_metadata = {
                    'task_id': task_id,
                    'execution_id': execution_id,
                    'submitted_at': datetime.utcnow().isoformat(),
                    'status': TaskState.PENDING.value
                }
                
                self.redis_client.set(
                    f"task:{task_id}",
                    json.dumps(task_metadata),
                    ex=7 * 24 * 3600  # 7 days TTL
                )
            except Exception as e:
                print(f"Warning: Could not store task metadata: {e}")
        
        return task_id
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a task."""
        try:
            # Get task result from Celery
            result = AsyncResult(task_id, app=self.celery_app)
            
            status = {
                'task_id': task_id,
                'state': result.state,
                'info': result.info or {},
                'successful': result.successful(),
                'failed': result.failed(),
                'ready': result.ready(),
                'traceback': result.traceback,
            }
            
            # Try to get additional metadata from Redis (simplified)
            if self.redis_client:
                try:
                    metadata_str = self.redis_client.get(f"task:{task_id}")
                    if metadata_str:
                        if isinstance(metadata_str, bytes):
                            metadata_str = metadata_str.decode('utf-8')
                        elif not isinstance(metadata_str, str):
                            metadata_str = str(metadata_str)
                        metadata = json.loads(metadata_str)
                        status.update(metadata)
                except Exception:
                    pass  # Continue without Redis metadata
            
            return status
            
        except Exception as e:
            print(f"Error getting task status for {task_id}: {str(e)}")
            return None
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task."""
        return cancel_task(task_id)
    
    def get_queue_metrics(self) -> Dict[str, Any]:
        """Get queue performance metrics."""
        try:
            # Get basic Celery stats (may be None if no workers available)
            stats = None
            active_tasks = None
            reserved_tasks = None
            
            try:
                stats = self.celery_app.control.inspect().stats()
                active_tasks = self.celery_app.control.inspect().active()
                reserved_tasks = self.celery_app.control.inspect().reserved()
            except Exception:
                pass  # Continue with None values
            
            # Get Redis metrics (simplified)
            redis_metrics = self._get_redis_metrics()
            
            # Combine metrics
            metrics = {
                'celery_stats': stats,
                'active_tasks': len(active_tasks) if active_tasks else 0,
                'reserved_tasks': len(reserved_tasks) if reserved_tasks else 0,
                **redis_metrics
            }
            
            return metrics
            
        except Exception as e:
            print(f"Error getting queue metrics: {str(e)}")
            return {
                'error': str(e),
                'active_tasks': 0,
                'pending_tasks': 0,
                'failed_tasks': 0,
                'completed_tasks': 0
            }
    
    def _get_redis_metrics(self) -> Dict[str, Any]:
        """Get simplified metrics from Redis."""
        if not self.redis_client:
            return {
                'pending_tasks': 0,
                'active_tasks': 0,
                'completed_tasks': 0,
                'failed_tasks': 0,
                'total_tracked_tasks': 0
            }
            
        try:
            # Count basic task keys
            task_keys = self.redis_client.keys("task:*")
            
            # Handle the case where task_keys might be a different type
            total_tasks = 0
            if task_keys:
                try:
                    # Cast to list to satisfy type checker
                    task_list = cast(List[str], task_keys)
                    total_tasks = len(task_list)
                except (TypeError, AttributeError):
                    total_tasks = 0
            
            return {
                'pending_tasks': 0,
                'active_tasks': 0,
                'completed_tasks': 0,
                'failed_tasks': 0,
                'total_tracked_tasks': total_tasks
            }
            
        except Exception as e:
            print(f"Error getting Redis metrics: {str(e)}")
            return {
                'pending_tasks': 0,
                'active_tasks': 0,
                'completed_tasks': 0,
                'failed_tasks': 0,
                'total_tracked_tasks': 0
            } 