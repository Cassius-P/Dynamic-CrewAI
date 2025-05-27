"""Delegation tools for manager agents in CrewAI hierarchical process."""

from typing import List, Dict, Any, Optional
from crewai.tools import BaseTool
from crewai import Agent as CrewAIAgent
import json
import logging

logger = logging.getLogger(__name__)


class TaskDecompositionTool(BaseTool):
    """Tool for breaking down high-level goals into specific tasks."""
    
    name: str = "task_decomposition"
    description: str = "Break down high-level objectives into specific, actionable tasks suitable for available agents"
    
    def _run(self, objective: str, available_agents: List[str]) -> Dict[str, Any]:
        """
        Decompose objective into tasks suitable for available agents.
        
        Args:
            objective: High-level goal to decompose
            available_agents: List of available agent roles
            
        Returns:
            Dictionary with decomposed tasks and assignments
        """
        try:
            # Use LLM reasoning to decompose the objective
            decomposition_prompt = f"""
            Analyze this objective and break it down into specific, actionable tasks:
            
            OBJECTIVE: {objective}
            
            AVAILABLE AGENTS: {', '.join(available_agents)}
            
            For each task, provide:
            1. Task description (clear and specific)
            2. Most suitable agent role from available agents
            3. Expected output format
            4. Dependencies on other tasks (if any)
            5. Estimated complexity (low/medium/high)
            
            Return your analysis as a JSON structure with this format:
            {{
                "decomposition_analysis": "Your reasoning for how to break down this objective",
                "tasks": [
                    {{
                        "id": "task_1",
                        "description": "Specific task description",
                        "suitable_agent": "agent_role",
                        "expected_output": "What this task should produce",
                        "dependencies": ["task_id1", "task_id2"],
                        "complexity": "low|medium|high",
                        "priority": 1
                    }}
                ]
            }}
            """
            
            # For now, implement rule-based decomposition
            # In a full implementation, this would use the manager's LLM
            tasks = self._rule_based_decomposition(objective, available_agents)
            
            return {
                "decomposition_analysis": f"Broke down objective into {len(tasks)} tasks based on available agents",
                "tasks": tasks,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Task decomposition failed: {e}")
            return {
                "error": str(e),
                "success": False,
                "tasks": []
            }
    
    def _rule_based_decomposition(self, objective: str, available_agents: List[str]) -> List[Dict[str, Any]]:
        """
        Rule-based task decomposition as fallback/starting point.
        
        Args:
            objective: Objective to decompose
            available_agents: Available agent roles
            
        Returns:
            List of task dictionaries
        """
        # Simple keyword-based decomposition
        tasks = []
        task_id = 1
        
        # Common task patterns based on objective keywords
        if "research" in objective.lower() or "analyze" in objective.lower():
            if any("research" in agent.lower() for agent in available_agents):
                tasks.append({
                    "id": f"task_{task_id}",
                    "description": f"Research and gather information for: {objective}",
                    "suitable_agent": next((agent for agent in available_agents if "research" in agent.lower()), available_agents[0]),
                    "expected_output": "Comprehensive research findings and data",
                    "dependencies": [],
                    "complexity": "medium",
                    "priority": 1
                })
                task_id += 1
        
        if "write" in objective.lower() or "report" in objective.lower() or "document" in objective.lower():
            if any("writer" in agent.lower() or "content" in agent.lower() for agent in available_agents):
                dependencies = [f"task_{i}" for i in range(1, task_id)]
                tasks.append({
                    "id": f"task_{task_id}",
                    "description": f"Write and document findings for: {objective}",
                    "suitable_agent": next((agent for agent in available_agents if "writer" in agent.lower() or "content" in agent.lower()), available_agents[0]),
                    "expected_output": "Well-structured written document or report",
                    "dependencies": dependencies,
                    "complexity": "medium",
                    "priority": 2
                })
                task_id += 1
        
        if "analyze" in objective.lower() or "evaluate" in objective.lower():
            if any("analyst" in agent.lower() for agent in available_agents):
                tasks.append({
                    "id": f"task_{task_id}",
                    "description": f"Analyze and evaluate data for: {objective}",
                    "suitable_agent": next((agent for agent in available_agents if "analyst" in agent.lower()), available_agents[0]),
                    "expected_output": "Detailed analysis with insights and recommendations",
                    "dependencies": [],
                    "complexity": "high",
                    "priority": 1
                })
                task_id += 1
        
        # Default task if no specific patterns match
        if not tasks:
            tasks.append({
                "id": f"task_{task_id}",
                "description": f"Complete the objective: {objective}",
                "suitable_agent": available_agents[0] if available_agents else "default_agent",
                "expected_output": "Successful completion of the stated objective",
                "dependencies": [],
                "complexity": "medium",
                "priority": 1
            })
        
        return tasks


class AgentCoordinationTool(BaseTool):
    """Tool for coordinating agent assignments and task dependencies."""
    
    name: str = "agent_coordination"
    description: str = "Coordinate optimal task-agent assignments and manage dependencies between tasks"
    
    def _run(self, tasks: List[Dict], agents: List[Dict]) -> Dict[str, Any]:
        """
        Coordinate optimal task-agent assignments.
        
        Args:
            tasks: List of task dictionaries with requirements
            agents: List of agent dictionaries with capabilities
            
        Returns:
            Optimized task-agent assignment plan
        """
        try:
            assignments = self._optimize_assignments(tasks, agents)
            coordination_plan = self._create_coordination_plan(assignments)
            
            return {
                "assignments": assignments,
                "coordination_plan": coordination_plan,
                "execution_order": self._determine_execution_order(assignments),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Agent coordination failed: {e}")
            return {
                "error": str(e),
                "success": False,
                "assignments": []
            }
    
    def _optimize_assignments(self, tasks: List[Dict], agents: List[Dict]) -> List[Dict[str, Any]]:
        """
        Optimize task-agent assignments based on capabilities and workload.
        
        Args:
            tasks: List of tasks
            agents: List of agents with capabilities
            
        Returns:
            List of optimized assignments
        """
        assignments = []
        agent_workloads = {agent["role"]: 0 for agent in agents}
        
        # Sort tasks by priority and complexity
        sorted_tasks = sorted(tasks, key=lambda t: (t.get("priority", 1), t.get("complexity", "medium")))
        
        for task in sorted_tasks:
            # Find best agent for this task
            best_agent = self._find_best_agent(task, agents, agent_workloads)
            
            assignment = {
                "task_id": task["id"],
                "task_description": task["description"],
                "assigned_agent": best_agent["role"],
                "agent_capabilities": best_agent.get("capabilities", []),
                "estimated_effort": self._estimate_effort(task, best_agent),
                "dependencies": task.get("dependencies", []),
                "priority": task.get("priority", 1)
            }
            
            assignments.append(assignment)
            agent_workloads[best_agent["role"]] += assignment["estimated_effort"]
        
        return assignments
    
    def _find_best_agent(self, task: Dict, agents: List[Dict], workloads: Dict[str, int]) -> Dict:
        """
        Find the best agent for a given task.
        
        Args:
            task: Task dictionary
            agents: Available agents
            workloads: Current agent workloads
            
        Returns:
            Best agent for the task
        """
        # Score agents based on capability match and current workload
        agent_scores = []
        
        for agent in agents:
            score = 0
            
            # Capability matching
            agent_role = agent["role"].lower()
            task_desc = task["description"].lower()
            
            if "research" in task_desc and "research" in agent_role:
                score += 10
            if "write" in task_desc and ("writer" in agent_role or "content" in agent_role):
                score += 10
            if "analyz" in task_desc and "analyst" in agent_role:
                score += 10
            
            # Workload balancing (prefer less loaded agents)
            current_workload = workloads.get(agent["role"], 0)
            workload_penalty = current_workload * 2
            score -= workload_penalty
            
            agent_scores.append((score, agent))
        
        # Return agent with highest score
        agent_scores.sort(key=lambda x: x[0], reverse=True)
        return agent_scores[0][1]
    
    def _estimate_effort(self, task: Dict, agent: Dict) -> int:
        """
        Estimate effort required for task-agent combination.
        
        Args:
            task: Task dictionary
            agent: Agent dictionary
            
        Returns:
            Effort estimate (1-10 scale)
        """
        complexity_mapping = {"low": 2, "medium": 5, "high": 8}
        base_effort = complexity_mapping.get(task.get("complexity", "medium"), 5)
        
        # Adjust based on agent capabilities
        # If agent is well-suited, reduce effort
        # This is a simplified heuristic
        
        return base_effort
    
    def _create_coordination_plan(self, assignments: List[Dict]) -> Dict[str, Any]:
        """
        Create coordination plan for task execution.
        
        Args:
            assignments: List of task assignments
            
        Returns:
            Coordination plan
        """
        return {
            "total_tasks": len(assignments),
            "agents_involved": list(set(a["assigned_agent"] for a in assignments)),
            "parallel_opportunities": self._identify_parallel_tasks(assignments),
            "critical_path": self._find_critical_path(assignments)
        }
    
    def _determine_execution_order(self, assignments: List[Dict]) -> List[str]:
        """
        Determine optimal execution order based on dependencies.
        
        Args:
            assignments: Task assignments
            
        Returns:
            Ordered list of task IDs
        """
        # Simple topological sort for task dependencies
        task_deps = {a["task_id"]: a["dependencies"] for a in assignments}
        execution_order = []
        remaining_tasks = set(task_deps.keys())
        
        while remaining_tasks:
            # Find tasks with no remaining dependencies
            ready_tasks = [
                task_id for task_id in remaining_tasks
                if all(dep in execution_order for dep in task_deps[task_id])
            ]
            
            if not ready_tasks:
                # Handle circular dependencies by picking lowest priority task
                ready_tasks = [min(remaining_tasks)]
            
            # Add ready tasks to execution order
            for task_id in ready_tasks:
                execution_order.append(task_id)
                remaining_tasks.remove(task_id)
        
        return execution_order
    
    def _identify_parallel_tasks(self, assignments: List[Dict]) -> List[List[str]]:
        """
        Identify tasks that can be executed in parallel.
        
        Args:
            assignments: Task assignments
            
        Returns:
            List of parallel task groups
        """
        # Simple implementation - tasks without dependencies can run in parallel
        no_deps = [a["task_id"] for a in assignments if not a["dependencies"]]
        if len(no_deps) > 1:
            return [no_deps]
        return []
    
    def _find_critical_path(self, assignments: List[Dict]) -> List[str]:
        """
        Find critical path through task dependencies.
        
        Args:
            assignments: Task assignments
            
        Returns:
            Critical path as list of task IDs
        """
        # Simplified critical path - longest dependency chain
        task_deps = {a["task_id"]: a["dependencies"] for a in assignments}
        
        def get_path_length(task_id, visited=None):
            if visited is None:
                visited = set()
            if task_id in visited:
                return 0
            visited.add(task_id)
            
            deps = task_deps.get(task_id, [])
            if not deps:
                return 1
            
            return 1 + max(get_path_length(dep, visited.copy()) for dep in deps)
        
        # Find task with longest path
        longest_task = max(task_deps.keys(), key=lambda t: get_path_length(t))
        
        # Build the path
        path = []
        current = longest_task
        while current:
            path.append(current)
            deps = task_deps.get(current, [])
            current = deps[0] if deps else None
        
        return list(reversed(path))


class DelegationValidationTool(BaseTool):
    """Tool for validating delegation decisions and assignments."""
    
    name: str = "delegation_validation"
    description: str = "Validate that delegation decisions are appropriate, feasible, and optimally structured"
    
    def _run(self, delegation_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate delegation plan for feasibility and optimality.
        
        Args:
            delegation_plan: Proposed delegation plan with assignments and coordination
            
        Returns:
            Validation results with recommendations
        """
        try:
            validation_results = {
                "is_valid": True,
                "warnings": [],
                "errors": [],
                "recommendations": [],
                "score": 0
            }
            
            # Validate assignments exist
            assignments = delegation_plan.get("assignments", [])
            if not assignments:
                validation_results["errors"].append("No task assignments found in delegation plan")
                validation_results["is_valid"] = False
                return validation_results
            
            # Validate each assignment
            for i, assignment in enumerate(assignments):
                self._validate_assignment(assignment, i, validation_results)
            
            # Validate coordination plan
            coordination_plan = delegation_plan.get("coordination_plan", {})
            self._validate_coordination(coordination_plan, validation_results)
            
            # Validate execution order
            execution_order = delegation_plan.get("execution_order", [])
            self._validate_execution_order(execution_order, assignments, validation_results)
            
            # Calculate overall score
            validation_results["score"] = self._calculate_delegation_score(delegation_plan, validation_results)
            
            return validation_results
            
        except Exception as e:
            logger.error(f"Delegation validation failed: {e}")
            return {
                "is_valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
                "recommendations": [],
                "score": 0
            }
    
    def _validate_assignment(self, assignment: Dict, index: int, results: Dict):
        """
        Validate individual task assignment.
        
        Args:
            assignment: Task assignment dictionary
            index: Assignment index for error reporting
            results: Results dictionary to update
        """
        required_fields = ["task_id", "task_description", "assigned_agent"]
        
        for field in required_fields:
            if field not in assignment:
                results["errors"].append(f"Assignment {index}: Missing required field '{field}'")
                results["is_valid"] = False
        
        # Validate effort estimation
        effort = assignment.get("estimated_effort", 0)
        if not isinstance(effort, (int, float)) or effort <= 0:
            results["warnings"].append(f"Assignment {index}: Invalid effort estimate")
        
        # Validate dependencies format
        dependencies = assignment.get("dependencies", [])
        if not isinstance(dependencies, list):
            results["errors"].append(f"Assignment {index}: Dependencies must be a list")
            results["is_valid"] = False
    
    def _validate_coordination(self, coordination_plan: Dict, results: Dict):
        """
        Validate coordination plan structure.
        
        Args:
            coordination_plan: Coordination plan dictionary
            results: Results dictionary to update
        """
        expected_fields = ["total_tasks", "agents_involved"]
        
        for field in expected_fields:
            if field not in coordination_plan:
                results["warnings"].append(f"Coordination plan missing '{field}' field")
        
        # Check for workload balance
        total_tasks = coordination_plan.get("total_tasks", 0)
        agents_count = len(coordination_plan.get("agents_involved", []))
        
        if agents_count > 0:
            avg_tasks_per_agent = total_tasks / agents_count
            if avg_tasks_per_agent > 5:
                results["recommendations"].append("Consider distributing tasks more evenly among agents")
            elif avg_tasks_per_agent < 1:
                results["recommendations"].append("Some agents may be underutilized")
    
    def _validate_execution_order(self, execution_order: List[str], assignments: List[Dict], results: Dict):
        """
        Validate execution order against task dependencies.
        
        Args:
            execution_order: Proposed execution order
            assignments: Task assignments
            results: Results dictionary to update
        """
        if not execution_order:
            results["warnings"].append("No execution order specified")
            return
        
        # Build dependency map
        task_deps = {}
        for assignment in assignments:
            task_id = assignment.get("task_id")
            dependencies = assignment.get("dependencies", [])
            if task_id:
                task_deps[task_id] = dependencies
        
        # Validate order respects dependencies
        completed_tasks = set()
        for task_id in execution_order:
            deps = task_deps.get(task_id, [])
            unmet_deps = [dep for dep in deps if dep not in completed_tasks]
            
            if unmet_deps:
                results["errors"].append(f"Task '{task_id}' scheduled before dependencies: {unmet_deps}")
                results["is_valid"] = False
            
            completed_tasks.add(task_id)
    
    def _calculate_delegation_score(self, delegation_plan: Dict, validation_results: Dict) -> int:
        """
        Calculate delegation quality score (0-100).
        
        Args:
            delegation_plan: Delegation plan
            validation_results: Validation results
            
        Returns:
            Score from 0-100
        """
        score = 100
        
        # Deduct for errors
        score -= len(validation_results["errors"]) * 20
        
        # Deduct for warnings
        score -= len(validation_results["warnings"]) * 5
        
        # Bonus for good practices
        assignments = delegation_plan.get("assignments", [])
        if assignments:
            # Bonus for workload distribution
            agents = set(a.get("assigned_agent") for a in assignments)
            if len(agents) > 1:
                score += 10
            
            # Bonus for having dependencies mapped
            has_deps = any(a.get("dependencies") for a in assignments)
            if has_deps:
                score += 5
        
        return max(0, min(100, score))
