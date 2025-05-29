"""Dependency resolver for managing task dependencies and execution order."""

from typing import Dict, List, Set, Optional
from dataclasses import dataclass
from collections import deque, defaultdict


class CircularDependencyError(Exception):
    """Exception raised when a circular dependency is detected."""
    pass


@dataclass
class TaskDependency:
    """Represents a dependency relationship between tasks."""
    task_id: str
    depends_on: str
    dependency_type: str = "sequential"  # sequential, parallel, etc.


class DependencyNode:
    """Represents a node in the dependency graph."""
    
    def __init__(self, task_id: str, dependencies: Optional[List[str]] = None, 
                 metadata: Optional[Dict] = None):
        """Initialize a dependency node.
        
        Args:
            task_id: Unique identifier for the task
            dependencies: List of task IDs this task depends on
            metadata: Additional metadata for the task
        """
        self.task_id = task_id
        self.dependencies = dependencies or []
        self.metadata = metadata or {}
        self.status = "pending"  # pending, running, completed, failed
    
    def add_dependency(self, task_id: str) -> None:
        """Add a dependency to this node."""
        if task_id not in self.dependencies:
            self.dependencies.append(task_id)
    
    def remove_dependency(self, task_id: str) -> None:
        """Remove a dependency from this node."""
        if task_id in self.dependencies:
            self.dependencies.remove(task_id)


class DependencyResolver:
    """Resolves task dependencies and provides execution order."""
    
    def __init__(self):
        """Initialize the dependency resolver."""
        self.dependency_graph: Dict[str, DependencyNode] = {}
        self.completed_tasks: Set[str] = set()
    
    def add_task(self, task_id: str, dependencies: Optional[List[str]] = None,
                metadata: Optional[Dict] = None) -> None:
        """Add a task to the dependency graph.
        
        Args:
            task_id: Unique identifier for the task
            dependencies: List of task IDs this task depends on
            metadata: Additional metadata for the task
            
        Raises:
            CircularDependencyError: If adding this task would create a cycle
        """
        # Create the node
        node = DependencyNode(task_id, dependencies, metadata)
        self.dependency_graph[task_id] = node
        
        # Check for circular dependencies after adding
        if self.has_circular_dependency():
            # Remove the task and raise error
            del self.dependency_graph[task_id]
            raise CircularDependencyError(
                f"Adding task '{task_id}' would create a circular dependency"
            )
    
    def add_dependency(self, task_id: str, depends_on: str) -> None:
        """Add a dependency between two existing tasks.
        
        Args:
            task_id: The task that depends on another
            depends_on: The task that must complete first
            
        Raises:
            CircularDependencyError: If this would create a cycle
            ValueError: If either task doesn't exist
        """
        if task_id not in self.dependency_graph:
            raise ValueError(f"Task '{task_id}' not found in dependency graph")
        if depends_on not in self.dependency_graph:
            raise ValueError(f"Task '{depends_on}' not found in dependency graph")
        
        # Add the dependency
        self.dependency_graph[task_id].add_dependency(depends_on)
        
        # Check for circular dependencies
        if self.has_circular_dependency():
            # Remove the dependency and raise error
            self.dependency_graph[task_id].remove_dependency(depends_on)
            raise CircularDependencyError(
                f"Adding dependency '{task_id}' -> '{depends_on}' would create a circular dependency"
            )
    
    def remove_dependency(self, task_id: str, depends_on: str) -> None:
        """Remove a dependency between two tasks.
        
        Args:
            task_id: The task to remove dependency from
            depends_on: The dependency to remove
        """
        if task_id in self.dependency_graph:
            self.dependency_graph[task_id].remove_dependency(depends_on)
    
    def remove_task(self, task_id: str) -> None:
        """Remove a task from the dependency graph.
        
        Args:
            task_id: The task to remove
        """
        # Remove the task from the graph
        if task_id in self.dependency_graph:
            del self.dependency_graph[task_id]
        
        # Remove this task from other tasks' dependencies
        for node in self.dependency_graph.values():
            node.remove_dependency(task_id)
        
        # Remove from completed tasks if present
        self.completed_tasks.discard(task_id)
    
    def has_circular_dependency(self) -> bool:
        """Check if the dependency graph has circular dependencies.
        
        Returns:
            True if circular dependency exists, False otherwise
        """
        # Use DFS to detect cycles
        visited = set()
        rec_stack = set()
        
        def has_cycle(node_id: str) -> bool:
            if node_id in rec_stack:
                return True
            if node_id in visited:
                return False
            
            visited.add(node_id)
            rec_stack.add(node_id)
            
            # Check all dependencies
            if node_id in self.dependency_graph:
                for dep in self.dependency_graph[node_id].dependencies:
                    if has_cycle(dep):
                        return True
            
            rec_stack.remove(node_id)
            return False
        
        # Check all nodes
        for task_id in self.dependency_graph:
            if task_id not in visited:
                if has_cycle(task_id):
                    return True
        
        return False
    
    def topological_sort(self) -> List[str]:
        """Perform topological sorting of the dependency graph.
        
        Returns:
            List of task IDs in execution order
            
        Raises:
            CircularDependencyError: If the graph has cycles
        """
        if self.has_circular_dependency():
            raise CircularDependencyError("Cannot sort graph with circular dependencies")
        
        # Kahn's algorithm for topological sorting
        in_degree = defaultdict(int)
        
        # Calculate in-degrees
        for task_id in self.dependency_graph:
            in_degree[task_id] = 0
        
        for node in self.dependency_graph.values():
            for dep in node.dependencies:
                in_degree[node.task_id] += 1
        
        # Find all nodes with no incoming edges
        queue = deque([task_id for task_id, degree in in_degree.items() if degree == 0])
        result = []
        
        while queue:
            task_id = queue.popleft()
            result.append(task_id)
            
            # For each dependent of this task
            for dependent_id, node in self.dependency_graph.items():
                if task_id in node.dependencies:
                    in_degree[dependent_id] -= 1
                    if in_degree[dependent_id] == 0:
                        queue.append(dependent_id)
        
        return result
    
    def get_ready_tasks(self) -> List[str]:
        """Get tasks that are ready for execution (no pending dependencies).
        
        Returns:
            List of task IDs ready for execution
        """
        ready_tasks = []
        
        for task_id, node in self.dependency_graph.items():
            if node.status in ["pending"] and self.is_task_ready(task_id):
                ready_tasks.append(task_id)
        
        return ready_tasks
    
    def is_task_ready(self, task_id: str) -> bool:
        """Check if a specific task is ready for execution.
        
        Args:
            task_id: The task to check
            
        Returns:
            True if task is ready, False otherwise
        """
        if task_id not in self.dependency_graph:
            return False
        
        node = self.dependency_graph[task_id]
        
        # Check if all dependencies are completed
        for dep in node.dependencies:
            if dep not in self.completed_tasks:
                return False
        
        return True
    
    def mark_task_completed(self, task_id: str) -> None:
        """Mark a task as completed.
        
        Args:
            task_id: The task to mark as completed
        """
        if task_id in self.dependency_graph:
            self.dependency_graph[task_id].status = "completed"
        self.completed_tasks.add(task_id)
    
    def mark_task_running(self, task_id: str) -> None:
        """Mark a task as running.
        
        Args:
            task_id: The task to mark as running
        """
        if task_id in self.dependency_graph:
            self.dependency_graph[task_id].status = "running"
    
    def mark_task_failed(self, task_id: str) -> None:
        """Mark a task as failed.
        
        Args:
            task_id: The task to mark as failed
        """
        if task_id in self.dependency_graph:
            self.dependency_graph[task_id].status = "failed"
    
    def get_task_dependencies(self, task_id: str) -> List[str]:
        """Get the dependencies for a specific task.
        
        Args:
            task_id: The task to get dependencies for
            
        Returns:
            List of task IDs this task depends on
        """
        if task_id in self.dependency_graph:
            return self.dependency_graph[task_id].dependencies.copy()
        return []
    
    def get_task_dependents(self, task_id: str) -> List[str]:
        """Get tasks that depend on a specific task.
        
        Args:
            task_id: The task to find dependents for
            
        Returns:
            List of task IDs that depend on this task
        """
        dependents = []
        
        for dependent_id, node in self.dependency_graph.items():
            if task_id in node.dependencies:
                dependents.append(dependent_id)
        
        return dependents
    
    def get_execution_order(self) -> List[str]:
        """Get the complete execution order for all tasks.
        
        Returns:
            List of task IDs in execution order
        """
        return self.topological_sort()
    
    def get_task_status(self, task_id: str) -> Optional[str]:
        """Get the status of a specific task.
        
        Args:
            task_id: The task to get status for
            
        Returns:
            Task status or None if task doesn't exist
        """
        if task_id in self.dependency_graph:
            return self.dependency_graph[task_id].status
        return None
    
    def get_graph_info(self) -> Dict:
        """Get information about the dependency graph.
        
        Returns:
            Dictionary containing graph statistics
        """
        total_tasks = len(self.dependency_graph)
        completed_tasks = len(self.completed_tasks)
        ready_tasks = len(self.get_ready_tasks())
        
        status_counts = defaultdict(int)
        for node in self.dependency_graph.values():
            status_counts[node.status] += 1
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed_tasks,
            "ready_tasks": ready_tasks,
            "status_counts": dict(status_counts),
            "has_cycles": self.has_circular_dependency()
        } 