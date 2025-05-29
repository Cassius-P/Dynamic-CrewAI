"""Task manager for orchestrating crew executions with dependencies."""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from .task_queue import TaskQueue
from .dependency_resolver import DependencyResolver


class ExecutionState(Enum):
    """Execution states for task management."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class ExecutionResult:
    """Result of a task execution."""
    execution_id: str
    state: ExecutionState
    result: Optional[str] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    task_results: Optional[Dict[str, Any]] = None


@dataclass
class TaskExecution:
    """Represents a task execution with metadata."""
    execution_id: str
    crew_config: Dict[str, Any]
    dependencies: List[str]
    priority: int
    state: ExecutionState = ExecutionState.PENDING
    task_id: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None


class TaskManager:
    """Manages task execution with dependency resolution."""
    
    def __init__(self, redis_url: Optional[str] = None):
        """Initialize TaskManager.
        
        Args:
            redis_url: Redis connection URL for task queue
        """
        self.task_queue = TaskQueue(redis_url)
        self.dependency_resolver = DependencyResolver()
        self.executions: Dict[str, TaskExecution] = {}
    
    def submit_execution(self, execution_id: str, crew_config: Dict[str, Any],
                        dependencies: Optional[List[str]] = None,
                        priority: int = 5) -> str:
        """Submit a crew execution to the task manager.
        
        Args:
            execution_id: Unique identifier for the execution
            crew_config: Configuration for the crew
            dependencies: List of execution IDs this execution depends on
            priority: Task priority (0-9, higher number = higher priority)
            
        Returns:
            Task ID for tracking the execution
        """
        dependencies = dependencies or []
        
        # Create execution record
        execution = TaskExecution(
            execution_id=execution_id,
            crew_config=crew_config,
            dependencies=dependencies,
            priority=priority
        )
        
        # Add to dependency resolver
        self.dependency_resolver.add_task(execution_id, dependencies)
        
        # Submit to task queue if ready
        if self.dependency_resolver.is_task_ready(execution_id):
            task_id = self.task_queue.submit_crew_execution(
                execution_id=execution_id,
                crew_config=crew_config,
                dependencies=dependencies,
                priority=priority
            )
            execution.task_id = task_id
            execution.state = ExecutionState.RUNNING
            execution.start_time = datetime.utcnow()
        
        # Store execution
        self.executions[execution_id] = execution
        
        return execution.task_id or execution_id
    
    def submit_parallel_executions(self, execution_configs: List[Tuple[str, Dict[str, Any]]],
                                 priority: int = 5) -> List[str]:
        """Submit multiple executions in parallel.
        
        Args:
            execution_configs: List of (execution_id, crew_config) tuples
            priority: Task priority for all executions
            
        Returns:
            List of task IDs
        """
        task_ids = []
        
        for execution_id, crew_config in execution_configs:
            task_id = self.submit_execution(
                execution_id=execution_id,
                crew_config=crew_config,
                dependencies=[],  # No dependencies for parallel execution
                priority=priority
            )
            task_ids.append(task_id)
        
        return task_ids
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of an execution.
        
        Args:
            execution_id: The execution ID to check
            
        Returns:
            Execution status information or None if not found
        """
        if execution_id not in self.executions:
            return None
        
        execution = self.executions[execution_id]
        
        # Get task status from queue if available
        task_status = None
        if execution.task_id:
            task_status = self.task_queue.get_task_status(execution.task_id)
        
        return {
            "execution_id": execution_id,
            "state": execution.state.value,
            "task_id": execution.task_id,
            "dependencies": execution.dependencies,
            "priority": execution.priority,
            "result": execution.result,
            "error": execution.error,
            "start_time": execution.start_time.isoformat() if execution.start_time else None,
            "end_time": execution.end_time.isoformat() if execution.end_time else None,
            "task_status": task_status
        }
    
    def cancel_execution(self, execution_id: str) -> bool:
        """Cancel an execution.
        
        Args:
            execution_id: The execution ID to cancel
            
        Returns:
            True if cancellation was successful, False otherwise
        """
        if execution_id not in self.executions:
            return False
        
        execution = self.executions[execution_id]
        
        # Cancel task in queue if it exists
        success = True
        if execution.task_id:
            success = self.task_queue.cancel_task(execution.task_id)
        
        if success:
            execution.state = ExecutionState.CANCELLED
            execution.end_time = datetime.utcnow()
            
            # Remove from dependency resolver
            self.dependency_resolver.remove_task(execution_id)
        
        return success
    
    def get_ready_executions(self) -> List[str]:
        """Get executions that are ready to run.
        
        Returns:
            List of execution IDs ready for execution
        """
        ready_executions = []
        
        for execution_id, execution in self.executions.items():
            if (execution.state == ExecutionState.PENDING and 
                self.dependency_resolver.is_task_ready(execution_id)):
                ready_executions.append(execution_id)
        
        return ready_executions
    
    def mark_execution_completed(self, execution_id: str, result: str) -> None:
        """Mark an execution as completed.
        
        Args:
            execution_id: The execution ID to mark as completed
            result: The execution result
        """
        if execution_id in self.executions:
            execution = self.executions[execution_id]
            execution.state = ExecutionState.COMPLETED
            execution.result = result
            execution.end_time = datetime.utcnow()
            
            # Mark as completed in dependency resolver
            self.dependency_resolver.mark_task_completed(execution_id)
    
    def mark_execution_failed(self, execution_id: str, error: str) -> None:
        """Mark an execution as failed.
        
        Args:
            execution_id: The execution ID to mark as failed
            error: The error message
        """
        if execution_id in self.executions:
            execution = self.executions[execution_id]
            execution.state = ExecutionState.FAILED
            execution.error = error
            execution.end_time = datetime.utcnow()
            
            # Mark as failed in dependency resolver
            self.dependency_resolver.mark_task_failed(execution_id)
    
    def process_completed_tasks(self) -> List[str]:
        """Process completed tasks and start ready dependent tasks.
        
        Returns:
            List of newly started execution IDs
        """
        started_executions = []
        
        # Check for newly ready executions
        ready_executions = self.get_ready_executions()
        
        for execution_id in ready_executions:
            execution = self.executions[execution_id]
            
            # Submit to task queue
            task_id = self.task_queue.submit_crew_execution(
                execution_id=execution_id,
                crew_config=execution.crew_config,
                dependencies=execution.dependencies,
                priority=execution.priority
            )
            
            # Update execution state
            execution.task_id = task_id
            execution.state = ExecutionState.RUNNING
            execution.start_time = datetime.utcnow()
            
            started_executions.append(execution_id)
        
        return started_executions
    
    def get_execution_metrics(self) -> Dict[str, Any]:
        """Get execution metrics.
        
        Returns:
            Dictionary containing execution statistics
        """
        total_executions = len(self.executions)
        
        state_counts = {
            "pending_executions": 0,
            "running_executions": 0,
            "completed_executions": 0,
            "failed_executions": 0,
            "cancelled_executions": 0
        }
        
        for execution in self.executions.values():
            if execution.state == ExecutionState.PENDING:
                state_counts["pending_executions"] += 1
            elif execution.state == ExecutionState.RUNNING:
                state_counts["running_executions"] += 1
            elif execution.state == ExecutionState.COMPLETED:
                state_counts["completed_executions"] += 1
            elif execution.state == ExecutionState.FAILED:
                state_counts["failed_executions"] += 1
            elif execution.state == ExecutionState.CANCELLED:
                state_counts["cancelled_executions"] += 1
        
        # Get queue metrics
        queue_metrics = self.task_queue.get_queue_metrics()
        
        return {
            "total_executions": total_executions,
            **state_counts,
            "queue_metrics": queue_metrics
        }
    
    def get_execution_dependency_graph(self) -> Dict[str, Any]:
        """Get information about the execution dependency graph.
        
        Returns:
            Dictionary containing dependency graph information
        """
        return self.dependency_resolver.get_graph_info()
    
    def get_execution_order(self) -> List[str]:
        """Get the execution order based on dependencies.
        
        Returns:
            List of execution IDs in dependency order
        """
        return self.dependency_resolver.get_execution_order() 