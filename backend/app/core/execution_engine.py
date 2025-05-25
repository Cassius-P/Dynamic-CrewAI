"""Execution engine for running CrewAI crews with stored configurations."""

from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import json
import traceback

from app.core.crew_wrapper import CrewWrapper
from app.models.execution import Execution, ExecutionStatus


class ExecutionEngine:
    """Engine for executing CrewAI crews from stored configurations."""
    
    def __init__(self):
        """Initialize the execution engine."""
        self.crew_wrapper = CrewWrapper()
    
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
        
        try:
            # Create crew from configuration
            crew = self.crew_wrapper.create_crew_from_dict(crew_config)
            
            # Execute the crew
            result = crew.kickoff()
            
            end_time = datetime.utcnow()
            execution_time = (end_time - start_time).total_seconds()
            
            return {
                "execution_id": execution_id,
                "status": ExecutionStatus.COMPLETED,
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
                "status": ExecutionStatus.FAILED,
                "result": None,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "execution_time": execution_time,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
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
                "status": ExecutionStatus.COMPLETED,
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
                "status": ExecutionStatus.FAILED,
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
        """Validate crew configuration before execution.
        
        Args:
            crew_config: Dictionary containing crew configuration
            
        Returns:
            Dictionary containing validation results
        """
        result = {
            "valid": False,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Basic validation
            if not crew_config.get("agents"):
                result["errors"].append("Crew must have at least one agent")
            
            if not crew_config.get("tasks"):
                result["errors"].append("Crew must have at least one task")
            
            # Validate agents
            agents = crew_config.get("agents", [])
            for i, agent in enumerate(agents):
                if not isinstance(agent, dict):
                    result["errors"].append(f"Agent {i} must be a dictionary")
                    continue
                
                required_agent_fields = ["role", "goal", "backstory"]
                for field in required_agent_fields:
                    if not agent.get(field):
                        result["errors"].append(f"Agent {i} missing required field: {field}")
            
            # Validate tasks
            tasks = crew_config.get("tasks", [])
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
            
            result["valid"] = len(result["errors"]) == 0
            
        except Exception as e:
            result["errors"].append(f"Validation failed: {str(e)}")
        
        return result
    
    def create_execution_record(self, 
                              crew_config: Dict[str, Any],
                              execution_result: Dict[str, Any]) -> Dict[str, Any]:
        """Create an execution record for database storage.
        
        Args:
            crew_config: The crew configuration that was executed
            execution_result: The result from execute_crew_from_config
            
        Returns:
            Dictionary suitable for creating Execution model
        """
        return {
            "id": execution_result["execution_id"],
            "crew_config": json.dumps(crew_config),
            "status": execution_result["status"],
            "result": execution_result["result"],
            "error_message": execution_result.get("error"),
            "start_time": datetime.fromisoformat(execution_result["start_time"]),
            "end_time": datetime.fromisoformat(execution_result["end_time"]) if execution_result.get("end_time") else None,
            "execution_time": execution_result.get("execution_time"),
            "metadata": {
                "agent_count": len(crew_config.get("agents", [])),
                "task_count": len(crew_config.get("tasks", [])),
                "has_tools": any(agent.get("tools") for agent in crew_config.get("agents", [])),
                "process_type": crew_config.get("process", "sequential")
            }
        }
