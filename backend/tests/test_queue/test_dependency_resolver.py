"""Tests for dependency resolver functionality."""

import pytest
from typing import Dict, List, Set

from app.task_queue.dependency_resolver import (
    DependencyResolver,
    CircularDependencyError,
    DependencyNode,
    TaskDependency
)


class TestDependencyNode:
    """Test cases for DependencyNode class."""
    
    def test_dependency_node_creation(self):
        """Test DependencyNode creation and attributes."""
        node = DependencyNode(
            task_id="task_1",
            dependencies=["task_2", "task_3"],
            metadata={"priority": 1}
        )
        
        assert node.task_id == "task_1"
        assert node.dependencies == ["task_2", "task_3"]
        assert node.metadata == {"priority": 1}
        assert node.status == "pending"
    
    def test_dependency_node_add_dependency(self):
        """Test adding dependencies to a node."""
        node = DependencyNode("task_1")
        node.add_dependency("task_2")
        node.add_dependency("task_3")
        
        assert "task_2" in node.dependencies
        assert "task_3" in node.dependencies
        assert len(node.dependencies) == 2
    
    def test_dependency_node_remove_dependency(self):
        """Test removing dependencies from a node."""
        node = DependencyNode("task_1", dependencies=["task_2", "task_3"])
        node.remove_dependency("task_2")
        
        assert "task_2" not in node.dependencies
        assert "task_3" in node.dependencies
        assert len(node.dependencies) == 1


class TestTaskDependency:
    """Test cases for TaskDependency data class."""
    
    def test_task_dependency_creation(self):
        """Test TaskDependency creation."""
        dep = TaskDependency(
            task_id="task_1",
            depends_on="task_2",
            dependency_type="sequential"
        )
        
        assert dep.task_id == "task_1"
        assert dep.depends_on == "task_2"
        assert dep.dependency_type == "sequential"


class TestDependencyResolver:
    """Test cases for DependencyResolver class."""
    
    @pytest.fixture
    def resolver(self):
        """Create a DependencyResolver instance for testing."""
        return DependencyResolver()
    
    def test_dependency_resolver_initialization(self, resolver):
        """Test DependencyResolver initialization."""
        assert resolver is not None
        assert hasattr(resolver, 'dependency_graph')
        assert len(resolver.dependency_graph) == 0
    
    def test_add_task_no_dependencies(self, resolver):
        """Test adding a task with no dependencies."""
        resolver.add_task("task_1")
        
        assert "task_1" in resolver.dependency_graph
        assert len(resolver.dependency_graph["task_1"].dependencies) == 0
    
    def test_add_task_with_dependencies(self, resolver):
        """Test adding a task with dependencies."""
        # First add prerequisite tasks
        resolver.add_task("task_1")
        resolver.add_task("task_2")
        
        # Then add task with dependencies
        resolver.add_task("task_3", dependencies=["task_1", "task_2"])
        
        assert "task_3" in resolver.dependency_graph
        assert "task_1" in resolver.dependency_graph["task_3"].dependencies
        assert "task_2" in resolver.dependency_graph["task_3"].dependencies
    
    def test_add_dependency_between_existing_tasks(self, resolver):
        """Test adding dependency between existing tasks."""
        resolver.add_task("task_1")
        resolver.add_task("task_2")
        
        resolver.add_dependency("task_2", "task_1")
        
        assert "task_1" in resolver.dependency_graph["task_2"].dependencies
    
    def test_remove_dependency(self, resolver):
        """Test removing dependency between tasks."""
        resolver.add_task("task_1")
        resolver.add_task("task_2", dependencies=["task_1"])
        
        resolver.remove_dependency("task_2", "task_1")
        
        assert "task_1" not in resolver.dependency_graph["task_2"].dependencies
    
    def test_topological_sort_simple(self, resolver):
        """Test topological sorting with simple dependencies."""
        # Create: task_1 -> task_2 -> task_3
        resolver.add_task("task_1")
        resolver.add_task("task_2", dependencies=["task_1"])
        resolver.add_task("task_3", dependencies=["task_2"])
        
        sorted_tasks = resolver.topological_sort()
        
        assert sorted_tasks == ["task_1", "task_2", "task_3"]
    
    def test_topological_sort_complex(self, resolver):
        """Test topological sorting with complex dependencies."""
        # Create complex dependency graph
        resolver.add_task("task_1")
        resolver.add_task("task_2")
        resolver.add_task("task_3", dependencies=["task_1", "task_2"])
        resolver.add_task("task_4", dependencies=["task_1"])
        resolver.add_task("task_5", dependencies=["task_3", "task_4"])
        
        sorted_tasks = resolver.topological_sort()
        
        # Verify that dependencies come before dependents
        task_1_pos = sorted_tasks.index("task_1")
        task_2_pos = sorted_tasks.index("task_2")
        task_3_pos = sorted_tasks.index("task_3")
        task_4_pos = sorted_tasks.index("task_4")
        task_5_pos = sorted_tasks.index("task_5")
        
        assert task_1_pos < task_3_pos
        assert task_2_pos < task_3_pos
        assert task_1_pos < task_4_pos
        assert task_3_pos < task_5_pos
        assert task_4_pos < task_5_pos
    
    def test_circular_dependency_detection_simple(self, resolver):
        """Test detection of simple circular dependency."""
        resolver.add_task("task_1")
        resolver.add_task("task_2", dependencies=["task_1"])
        
        # This should create a circular dependency
        with pytest.raises(CircularDependencyError):
            resolver.add_dependency("task_1", "task_2")
    
    def test_circular_dependency_detection_complex(self, resolver):
        """Test detection of complex circular dependency."""
        resolver.add_task("task_1")
        resolver.add_task("task_2", dependencies=["task_1"])
        resolver.add_task("task_3", dependencies=["task_2"])
        
        # This should create a circular dependency: task_1 -> task_2 -> task_3 -> task_1
        with pytest.raises(CircularDependencyError):
            resolver.add_dependency("task_1", "task_3")
    
    def test_has_circular_dependency_false(self, resolver):
        """Test circular dependency check when no cycles exist."""
        resolver.add_task("task_1")
        resolver.add_task("task_2", dependencies=["task_1"])
        resolver.add_task("task_3", dependencies=["task_2"])
        
        assert not resolver.has_circular_dependency()
    
    def test_has_circular_dependency_true(self, resolver):
        """Test circular dependency check when cycles exist."""
        resolver.add_task("task_1")
        resolver.add_task("task_2", dependencies=["task_1"])
        
        # Manually create circular dependency (bypassing validation)
        resolver.dependency_graph["task_1"].dependencies.append("task_2")
        
        assert resolver.has_circular_dependency()
    
    def test_get_ready_tasks_no_dependencies(self, resolver):
        """Test getting tasks ready for execution (no dependencies)."""
        resolver.add_task("task_1")
        resolver.add_task("task_2")
        resolver.add_task("task_3")
        
        ready_tasks = resolver.get_ready_tasks()
        
        assert set(ready_tasks) == {"task_1", "task_2", "task_3"}
    
    def test_get_ready_tasks_with_dependencies(self, resolver):
        """Test getting tasks ready for execution with dependencies."""
        resolver.add_task("task_1")
        resolver.add_task("task_2")
        resolver.add_task("task_3", dependencies=["task_1", "task_2"])
        
        ready_tasks = resolver.get_ready_tasks()
        
        # Only task_1 and task_2 should be ready initially
        assert set(ready_tasks) == {"task_1", "task_2"}
    
    def test_mark_task_completed(self, resolver):
        """Test marking a task as completed."""
        resolver.add_task("task_1")
        resolver.add_task("task_2", dependencies=["task_1"])
        
        # Initially only task_1 is ready
        ready_tasks = resolver.get_ready_tasks()
        assert ready_tasks == ["task_1"]
        
        # Mark task_1 as completed
        resolver.mark_task_completed("task_1")
        
        # Now task_2 should be ready
        ready_tasks = resolver.get_ready_tasks()
        assert ready_tasks == ["task_2"]
    
    def test_get_task_dependencies(self, resolver):
        """Test getting dependencies for a specific task."""
        resolver.add_task("task_1")
        resolver.add_task("task_2")
        resolver.add_task("task_3", dependencies=["task_1", "task_2"])
        
        dependencies = resolver.get_task_dependencies("task_3")
        
        assert set(dependencies) == {"task_1", "task_2"}
    
    def test_get_task_dependents(self, resolver):
        """Test getting tasks that depend on a specific task."""
        resolver.add_task("task_1")
        resolver.add_task("task_2", dependencies=["task_1"])
        resolver.add_task("task_3", dependencies=["task_1"])
        
        dependents = resolver.get_task_dependents("task_1")
        
        assert set(dependents) == {"task_2", "task_3"}
    
    def test_remove_task(self, resolver):
        """Test removing a task from the dependency graph."""
        resolver.add_task("task_1")
        resolver.add_task("task_2", dependencies=["task_1"])
        
        resolver.remove_task("task_1")
        
        assert "task_1" not in resolver.dependency_graph
        # task_2 should still exist but without dependencies
        assert "task_2" in resolver.dependency_graph
        assert len(resolver.dependency_graph["task_2"].dependencies) == 0
    
    def test_is_task_ready(self, resolver):
        """Test checking if a specific task is ready for execution."""
        resolver.add_task("task_1")
        resolver.add_task("task_2", dependencies=["task_1"])
        
        assert resolver.is_task_ready("task_1") is True
        assert resolver.is_task_ready("task_2") is False
        
        resolver.mark_task_completed("task_1")
        assert resolver.is_task_ready("task_2") is True
    
    def test_get_execution_order(self, resolver):
        """Test getting the complete execution order."""
        resolver.add_task("task_1")
        resolver.add_task("task_2")
        resolver.add_task("task_3", dependencies=["task_1", "task_2"])
        resolver.add_task("task_4", dependencies=["task_3"])
        
        execution_order = resolver.get_execution_order()
        
        # Should be a valid topological order
        assert len(execution_order) == 4
        task_3_pos = execution_order.index("task_3")
        task_4_pos = execution_order.index("task_4")
        
        # task_3 should come before task_4
        assert task_3_pos < task_4_pos
        
        # task_1 and task_2 should come before task_3
        assert execution_order.index("task_1") < task_3_pos
        assert execution_order.index("task_2") < task_3_pos


class TestCircularDependencyError:
    """Test cases for CircularDependencyError exception."""
    
    def test_circular_dependency_error_creation(self):
        """Test CircularDependencyError creation and message."""
        error = CircularDependencyError("Circular dependency detected in task chain")
        
        assert str(error) == "Circular dependency detected in task chain"
        assert isinstance(error, Exception) 