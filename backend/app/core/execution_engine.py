"""Execution engine for running CrewAI crews with stored configurations."""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import json
import traceback

from app.core.crew_wrapper import CrewWrapper
from app.core.manager_agent_wrapper import ManagerAgentWrapper
from app.models.execution import Execution, ExecutionStatus


class ExecutionEngine:
    """Engine for executing CrewAI crews from stored configurations."""
    
    def __init__(self):
        """Initialize the execution engine."""
        self.crew_wrapper = CrewWrapper()
        self.manager_agent_wrapper = ManagerAgentWrapper()
    
    def execute_crew_from_config(self, 
                                crew_config: Dict[str, Any], 
                                execution_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a crew from configuration.
        
        Args:
            crew_config: Dictionary containing crew configuration
            execution_id: Optional execution ID for tracking
            
        Returns:
            Dictionary containing execution results
        """
        if not execution_id:
            execution_id = str(uuid.uuid4())
        
        start_time = datetime.utcnow()
        
        try:            # Create crew from configuration
            crew = self.crew_wrapper.create_crew_from_dict(crew_config)
            
            # Execute the crew
            result = crew.kickoff()
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            return {
                "execution_id": execution_id,
                "status": ExecutionStatus.COMPLETED.value,
                "result": str(result),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "execution_time": execution_time,
                "error": None
            }
            
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            return {
                "execution_id": execution_id,
                "status": ExecutionStatus.FAILED.value,
                "result": None,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "execution_time": execution_time,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def execute_crew_with_manager_tasks(self, 
                                      agents_models: List,
                                      text_input: str,
                                      execution_id: Optional[str] = None,
                                      **crew_kwargs) -> Dict[str, Any]:
        """Execute a crew with manager agent generating tasks from text input.
        
        Args:
            agents_models: List of agent models (should include one manager agent)
            text_input: Text description to generate tasks from
            execution_id: Optional execution ID for tracking
            **crew_kwargs: Additional crew configuration
            
        Returns:
            Dictionary containing execution results
        """
        if not execution_id:
            execution_id = str(uuid.uuid4())
        
        start_time = datetime.utcnow()
        
        try:
            # Create crew with manager agent task generation
            crew = self.crew_wrapper.create_crew_with_manager_tasks(
                agents_models, text_input, **crew_kwargs
            )
              # Execute the crew
            result = crew.kickoff()
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            return {
                "execution_id": execution_id,
                "status": ExecutionStatus.COMPLETED.value,
                "result": str(result),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "execution_time": execution_time,
                "error": None,
                "manager_agent_used": True,
                "text_input": text_input,
                "generated_tasks_count": len(crew.tasks) if hasattr(crew, 'tasks') else 0
            }
            
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            return {
                "execution_id": execution_id,
                "status": ExecutionStatus.FAILED.value,
                "result": None,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "execution_time": execution_time,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "manager_agent_used": True,
                "text_input": text_input
            }
    
    async def execute_crew_with_delegation(self, 
                                         agents_models: List,
                                         objective: str,
                                         delegation_mode: str = "native",
                                         execution_id: Optional[str] = None,
                                         **crew_kwargs) -> Dict[str, Any]:
        """Execute a crew using CrewAI native delegation or enhanced task-based mode.
        
        Args:
            agents_models: List of agent models (should include one manager agent)
            objective: High-level objective for delegation
            delegation_mode: "native" for CrewAI delegation, "task_based" for manual assignment
            execution_id: Optional execution ID for tracking
            **crew_kwargs: Additional crew configuration
            
        Returns:
            Dictionary containing execution results with delegation information
        """
        if not execution_id:
            execution_id = str(uuid.uuid4())
        
        start_time = datetime.utcnow()
        
        try:
            # Create crew with specified delegation mode
            crew = self.crew_wrapper.create_crew_with_manager(
                agents_models, objective, delegation_mode, **crew_kwargs
            )
            
            # Validate hierarchical configuration for delegation
            if delegation_mode == "native":
                if not hasattr(crew, 'process') or crew.process != "hierarchical":
                    raise ValueError("Crew must use hierarchical process for native delegation")
                
                if not hasattr(crew, 'manager_agent') or crew.manager_agent is None:
                    raise ValueError("Manager agent required for native delegation")
            
            # Execute the crew
            result = crew.kickoff()
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
              # Extract delegation information
            delegation_info = self._extract_delegation_information(crew, result, delegation_mode)
            
            return {
                "execution_id": execution_id,
                "status": ExecutionStatus.COMPLETED.value,
                "result": str(result),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "execution_time": execution_time,
                "error": None,
                "delegation_mode": delegation_mode,
                "manager_agent_used": True,
                "objective": objective,
                **delegation_info
            }
            
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            return {
                "execution_id": execution_id,
                "status": ExecutionStatus.FAILED.value,
                "result": None,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "execution_time": execution_time,
                "error": str(e),
                "traceback": traceback.format_exc(),
                "delegation_mode": delegation_mode,
                "manager_agent_used": True,
                "objective": objective
            }
    
    def _extract_delegation_information(self, crew, result, delegation_mode: str) -> Dict[str, Any]:
        """Extract delegation information from crew execution.
        
        Args:
            crew: Executed CrewAI crew
            result: Execution result
            delegation_mode: Delegation mode used
            
        Returns:
            Dictionary with delegation information
        """
        delegation_info = {
            "tasks_executed": len(crew.tasks) if hasattr(crew, 'tasks') else 0,
            "agents_involved": len(crew.agents) if hasattr(crew, 'agents') else 0,
            "delegation_decisions": [],
            "agent_interactions": []
        }
        
        if delegation_mode == "native":
            # For native delegation, try to extract CrewAI's delegation decisions
            # This would depend on CrewAI's internal logging/tracking
            delegation_info["delegation_type"] = "native_crewai"
            delegation_info["process_used"] = "hierarchical"
            
            # Extract manager agent information
            if hasattr(crew, 'manager_agent'):
                manager_agent = crew.manager_agent
                delegation_info["manager_agent_role"] = getattr(manager_agent, 'role', 'Unknown')
                delegation_info["manager_tools_used"] = len(getattr(manager_agent, 'tools', []))
        else:
            # For task-based delegation, extract manual assignment information
            delegation_info["delegation_type"] = "manual_assignment"
            delegation_info["process_used"] = "hierarchical_with_predefined_tasks"
        
        return delegation_info
    
    def execute_crew_from_model(self, 
                               crew_model,
                               agents_models: List,
                               execution_id: Optional[str] = None) -> Dict[str, Any]:
        """Execute a crew from database models.
        
        Args:
            crew_model: CrewModel instance
            agents_models: List of AgentModel instances
            execution_id: Optional execution ID for tracking
            
        Returns:
            Dictionary containing execution results
        """
        if not execution_id:
            execution_id = str(uuid.uuid4())
        
        start_time = datetime.utcnow()
        
        try:
            # Create crew from models
            crew = self.crew_wrapper.create_crew_from_model(crew_model, agents_models)
              # Execute the crew
            result = crew.kickoff()
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            return {
                "execution_id": execution_id,
                "status": ExecutionStatus.COMPLETED.value,
                "result": str(result),
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "execution_time": execution_time,
                "error": None
            }
            
        except Exception as e:
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            return {
                "execution_id": execution_id,
                "status": ExecutionStatus.FAILED.value,
                "result": None,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "execution_time": execution_time,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    def get_execution_status(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a running execution.
        
        Note: For Phase 2, this is a basic implementation.
        Phase 3 will add proper async execution tracking.
        
        Args:
            execution_id: The execution ID to check
            
        Returns:
            Execution status information or None if not found
        """
        # For Phase 2, we only support synchronous execution
        # This method is a placeholder for Phase 3 async capabilities
        return None
    
    def validate_crew_config(self, crew_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate crew configuration before execution (with manager agent support).
        
        Args:
            crew_config: Dictionary containing crew configuration
            
        Returns:
            Dictionary containing validation results
        """
        result = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "manager_agent_detected": False,
            "can_generate_tasks": False
        }
        
        try:
            # Basic validation
            if not crew_config.get("agents"):
                result["errors"].append("Crew must have at least one agent")
            
            # Validate agents and detect manager agents
            agents = crew_config.get("agents", [])
            manager_agent_count = 0
            
            for i, agent in enumerate(agents):
                if not isinstance(agent, dict):
                    result["errors"].append(f"Agent {i} must be a dictionary")
                    continue
                
                required_agent_fields = ["role", "goal", "backstory"]
                for field in required_agent_fields:
                    if not agent.get(field):
                        result["errors"].append(f"Agent {i} missing required field: {field}")
                
                # Check for manager agent
                is_manager = (
                    agent.get("manager_type") is not None or
                    agent.get("can_generate_tasks", False) or
                    agent.get("allow_delegation", False)
                )
                
                if is_manager:
                    manager_agent_count += 1
                    result["manager_agent_detected"] = True
                    
                    if agent.get("can_generate_tasks", False):
                        result["can_generate_tasks"] = True
                    
                    # Validate manager agent specific fields
                    if agent.get("manager_type") and agent.get("manager_type") not in ["hierarchical", "collaborative", "sequential"]:
                        result["errors"].append(f"Agent {i} has invalid manager_type: {agent.get('manager_type')}")
            
            # Check for multiple manager agents
            if manager_agent_count > 1:
                result["errors"].append("Crew can only have one manager agent")
            
            # Validate tasks (with manager agent considerations)
            tasks = crew_config.get("tasks", [])
            
            # If no tasks provided but we have a manager agent that can generate tasks, that's OK
            if not tasks and not result["can_generate_tasks"]:
                result["errors"].append("Crew must have at least one task or a manager agent that can generate tasks")
            elif not tasks and result["can_generate_tasks"]:
                # Check if we have a goal for task generation
                if not crew_config.get("goal"):
                    result["warnings"].append("No tasks provided and no goal for task generation - default tasks will be created")
            
            # Validate existing tasks if provided
            if tasks:
                agent_names = [agent.get("name") for agent in agents if agent.get("name")]
                
                for i, task in enumerate(tasks):
                    if not isinstance(task, dict):
                        result["errors"].append(f"Task {i} must be a dictionary")
                        continue
                    
                    required_task_fields = ["description", "expected_output", "agent"]
                    for field in required_task_fields:
                        if not task.get(field):
                            result["errors"].append(f"Task {i} missing required field: {field}")
                    
                    # Check if agent reference is valid
                    agent_ref = task.get("agent")
                    if agent_ref and agent_ref not in agent_names:
                        result["warnings"].append(f"Task {i} references unknown agent: {agent_ref}")
            
            # Manager agent specific validations
            if result["manager_agent_detected"]:
                # Check if hierarchical process is appropriate
                if crew_config.get("process") == "sequential" and manager_agent_count > 0:
                    result["warnings"].append("Manager agent detected but process is set to sequential - consider using hierarchical process")
            
            result["valid"] = len(result["errors"]) == 0
            
        except Exception as e:
            result["errors"].append(f"Validation failed: {str(e)}")
        
        return result
    
    def create_execution_record(self, 
                              crew_config: Dict[str, Any],
                              execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create an execution record for database storage (with manager agent support).
        
        Args:
            crew_config: The crew configuration that was executed
            execution_result: The result from execute_crew_from_config
            
        Returns:
            Dictionary suitable for creating Execution model
        """
        # Detect manager agent information
        agents = crew_config.get("agents", [])
        manager_agent_info = None
        
        for agent in agents:
            is_manager = (
                agent.get("manager_type") is not None or
                agent.get("can_generate_tasks", False) or
                agent.get("allow_delegation", False)
            )
            if is_manager:
                manager_agent_info = {
                    "role": agent.get("role"),
                    "manager_type": agent.get("manager_type"),
                    "can_generate_tasks": agent.get("can_generate_tasks", False),
                    "allow_delegation": agent.get("allow_delegation", False)
                }
                break
        
        metadata = {
            "agent_count": len(agents),
            "task_count": len(crew_config.get("tasks", [])),
            "has_tools": any(agent.get("tools") for agent in agents),
            "process_type": crew_config.get("process", "sequential"),
            "manager_agent_used": execution_result.get("manager_agent_used", False),
            "manager_agent_info": manager_agent_info,
            "text_input": execution_result.get("text_input"),
            "generated_tasks_count": execution_result.get("generated_tasks_count")
        }
        
        return {
            "id": execution_result["execution_id"],
            "crew_config": json.dumps(crew_config),
            "status": execution_result["status"],
            "result": execution_result["result"],
            "error_message": execution_result.get("error"),
            "start_time": datetime.fromisoformat(execution_result["start_time"]),
            "end_time": datetime.fromisoformat(execution_result["end_time"]) if execution_result.get("end_time") else None,
            "execution_time": execution_result.get("execution_time"),
            "metadata": metadata
        }
