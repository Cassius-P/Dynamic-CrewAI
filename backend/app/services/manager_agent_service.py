"""Manager agent service for business logic operations."""

import logging
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from sqlalchemy.orm import Session

from app.core.manager_agent_wrapper import ManagerAgentWrapper
from app.core.execution_engine import ExecutionEngine
from app.models.agent import Agent
from app.models.execution import Execution, ExecutionStatus
from app.tools.task_generation import TaskGenerator

logger = logging.getLogger(__name__)


class ManagerAgentService:
    """Service for managing manager agent business logic operations."""
    
    def __init__(self, db_session: Session):
        """Initialize manager agent service."""
        self.db_session = db_session
        self.manager_wrapper = ManagerAgentWrapper()
        self.execution_engine = ExecutionEngine()
        self.task_generator = TaskGenerator()
    
    def get_manager_agents(self, skip: int = 0, limit: int = 100) -> List[Agent]:
        """Get all manager agents from the database."""
        try:
            # Query for agents that are manager agents
            manager_agents = self.db_session.query(Agent).filter(
                Agent.manager_type.isnot(None)
            ).offset(skip).limit(limit).all()
            
            return manager_agents
        
        except Exception as e:
            logger.error(f"Failed to retrieve manager agents: {e}")
            raise
    
    def get_manager_agent_by_id(self, agent_id: int) -> Optional[Agent]:
        """Get a specific manager agent by ID."""
        try:
            agent = self.db_session.query(Agent).filter(
                Agent.id == agent_id,
                Agent.manager_type.isnot(None)
            ).first()
            
            return agent
        
        except Exception as e:
            logger.error(f"Failed to retrieve manager agent {agent_id}: {e}")
            raise
    
    def create_manager_agent(self, agent_data: Dict[str, Any]) -> Agent:
        """Create a new manager agent with validation."""
        try:
            # Ensure it's a manager agent
            if not agent_data.get("manager_type"):
                agent_data["manager_type"] = "hierarchical"
            
            if agent_data.get("allow_delegation") is not True:
                agent_data["allow_delegation"] = True
            
            if agent_data.get("can_generate_tasks") is not True:
                agent_data["can_generate_tasks"] = True
            
            # Validate manager agent configuration
            validation_result = self.validate_manager_agent_config(agent_data)
            if not validation_result["valid"]:
                raise ValueError(f"Invalid manager agent configuration: {validation_result['errors']}")
            
            # Create the agent
            db_agent = Agent(**agent_data)
            self.db_session.add(db_agent)
            self.db_session.commit()
            self.db_session.refresh(db_agent)
            
            logger.info(f"Created manager agent {db_agent.id} with type {db_agent.manager_type}")
            return db_agent
        
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to create manager agent: {e}")
            raise
    
    def update_manager_agent(self, agent_id: int, update_data: Dict[str, Any]) -> Agent:
        """Update a manager agent with validation."""
        try:
            agent = self.get_manager_agent_by_id(agent_id)
            if not agent:
                raise ValueError(f"Manager agent {agent_id} not found")
            
            # Validate update data if it contains manager-specific fields
            if any(key in update_data for key in ["manager_type", "manager_config", "can_generate_tasks"]):
                # Merge current data with updates for validation
                current_data = {
                    "role": agent.role,
                    "goal": agent.goal,
                    "backstory": agent.backstory,
                    "manager_type": agent.manager_type,
                    "can_generate_tasks": agent.can_generate_tasks,
                    "allow_delegation": agent.allow_delegation,
                    "manager_config": agent.manager_config if agent.manager_config is not None else {}
                }
                current_data.update(update_data)
                
                validation_result = self.validate_manager_agent_config(current_data)
                if not validation_result["valid"]:
                    raise ValueError(f"Invalid manager agent update: {validation_result['errors']}")
            
            # Apply updates
            for field, value in update_data.items():
                if hasattr(agent, field):
                    setattr(agent, field, value)
            
            self.db_session.commit()
            self.db_session.refresh(agent)
            
            logger.info(f"Updated manager agent {agent_id}")
            return agent
        
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to update manager agent {agent_id}: {e}")
            raise
    
    def delete_manager_agent(self, agent_id: int) -> bool:
        """Delete a manager agent."""
        try:
            agent = self.get_manager_agent_by_id(agent_id)
            if not agent:
                raise ValueError(f"Manager agent {agent_id} not found")
            
            self.db_session.delete(agent)
            self.db_session.commit()
            
            logger.info(f"Deleted manager agent {agent_id}")
            return True
        
        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Failed to delete manager agent {agent_id}: {e}")
            raise
    
    def validate_manager_agent_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate manager agent configuration."""
        result = {
            "valid": False,
            "errors": [],
            "warnings": []
        }
        
        try:
            # Required fields
            required_fields = ["role", "goal", "backstory"]
            for field in required_fields:
                if not config.get(field):
                    result["errors"].append(f"Missing required field: {field}")
            
            # Manager type validation
            manager_type = config.get("manager_type")
            if manager_type and manager_type not in ["hierarchical", "collaborative", "sequential"]:
                result["errors"].append(f"Invalid manager_type: {manager_type}")
            
            # Manager config validation
            manager_config = config.get("manager_config", {})
            if manager_config and not isinstance(manager_config, dict):
                result["errors"].append("manager_config must be a dictionary")
            
            # Delegation validation
            if config.get("can_generate_tasks", False) == True and config.get("allow_delegation", False) != True:
                result["warnings"].append("Manager agents that can generate tasks should typically allow delegation")
            
            result["valid"] = len(result["errors"]) == 0
        
        except Exception as e:
            result["errors"].append(f"Validation failed: {str(e)}")
        
        return result
    
    def generate_tasks_from_text(self, agent_id: int, text_input: str, max_tasks: int = 5) -> List[Dict[str, Any]]:
        """Generate tasks from text input using a manager agent."""
        try:
            manager_agent = self.get_manager_agent_by_id(agent_id)
            if not manager_agent:
                raise ValueError(f"Manager agent {agent_id} not found")
            
            if not (manager_agent.can_generate_tasks is True):
                raise ValueError(f"Manager agent {agent_id} cannot generate tasks")
            
            # Generate tasks using the manager agent wrapper
            generated_tasks = self.manager_wrapper.generate_tasks_from_text(
                manager_agent, text_input
            )
            
            # Limit the number of tasks
            limited_tasks = generated_tasks[:max_tasks]
            
            # Convert to dictionary format for API response
            task_dicts = []
            for task in limited_tasks:
                task_dict = {
                    "description": task.description,
                    "expected_output": task.expected_output,
                    "generated_at": datetime.utcnow().isoformat(),
                    "source_text": text_input
                }
                task_dicts.append(task_dict)
            
            logger.info(f"Generated {len(task_dicts)} tasks for manager agent {agent_id}")
            return task_dicts
        
        except Exception as e:
            logger.error(f"Failed to generate tasks for manager agent {agent_id}: {e}")
            raise
    
    def execute_crew_with_manager_tasks(
        self,
        agent_ids: List[int],
        text_input: str,
        crew_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute a crew with manager agent generating tasks from text."""
        try:
            # Get agent models
            agents = []
            manager_agent = None
            
            for agent_id in agent_ids:
                agent = self.db_session.query(Agent).filter(Agent.id == agent_id).first()
                if not agent:
                    raise ValueError(f"Agent {agent_id} not found")
                
                agents.append(agent)
                
                # Check if this is a manager agent
                if self.manager_wrapper.is_manager_agent(agent):
                    if manager_agent is not None:
                        raise ValueError("Multiple manager agents not allowed")
                    manager_agent = agent
            
            if not manager_agent:
                raise ValueError("No manager agent found in the provided agents")
            
            # Execute using the execution engine
            execution_result = self.execution_engine.execute_crew_with_manager_tasks(
                agents, text_input, **(crew_config or {})
            )
            
            # Store execution record
            if execution_result["status"] == ExecutionStatus.COMPLETED:
                execution_record = Execution(
                    id=execution_result["execution_id"],
                    crew_config=str({"agents": [agent.id for agent in agents], "text_input": text_input}),
                    status=execution_result["status"],
                    result=execution_result["result"],
                    start_time=datetime.fromisoformat(execution_result["start_time"]),
                    end_time=datetime.fromisoformat(execution_result["end_time"]),
                    execution_time=execution_result["execution_time"],
                    metadata={
                        "manager_agent_used": True,
                        "manager_agent_id": manager_agent.id,
                        "text_input": text_input,
                        "generated_tasks_count": execution_result.get("generated_tasks_count", 0)
                    }
                )
                self.db_session.add(execution_record)
                self.db_session.commit()
            
            logger.info(f"Executed crew with manager agent {manager_agent.id}, status: {execution_result['status']}")
            return execution_result
        
        except Exception as e:
            logger.error(f"Failed to execute crew with manager tasks: {e}")
            raise
    
    def get_manager_agent_capabilities(self, agent_id: int) -> Dict[str, Any]:
        """Get capabilities and configuration of a manager agent."""
        try:
            manager_agent = self.get_manager_agent_by_id(agent_id)
            if not manager_agent:
                raise ValueError(f"Manager agent {agent_id} not found")
            
            capabilities = {
                "agent_id": manager_agent.id,
                "role": manager_agent.role,
                "manager_type": manager_agent.manager_type,
                "can_generate_tasks": manager_agent.can_generate_tasks,
                "allow_delegation": manager_agent.allow_delegation,
                "manager_config": manager_agent.manager_config if manager_agent.manager_config is not None else {},
                "delegation_strategies": ["round_robin", "random", "sequential"],
                "supported_manager_types": ["hierarchical", "collaborative", "sequential"],
                "capabilities": {
                    "task_generation": manager_agent.can_generate_tasks,
                    "delegation": manager_agent.allow_delegation,
                    "hierarchical_management": manager_agent.manager_type == "hierarchical",
                    "collaborative_management": manager_agent.manager_type == "collaborative",
                    "sequential_management": manager_agent.manager_type == "sequential"
                }
            }
            
            return capabilities
        
        except Exception as e:
            logger.error(f"Failed to get capabilities for manager agent {agent_id}: {e}")
            raise
    
    def get_manager_agent_executions(
        self,
        agent_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Execution]:
        """Get execution history for a manager agent."""
        try:
            manager_agent = self.get_manager_agent_by_id(agent_id)
            if not manager_agent:
                raise ValueError(f"Manager agent {agent_id} not found")
            
            # Query executions where this manager agent was used
            executions = self.db_session.query(Execution).filter(
                Execution.metadata["manager_agent_id"].astext == str(agent_id)
            ).order_by(Execution.start_time.desc()).offset(skip).limit(limit).all()
            
            return executions
        
        except Exception as e:
            logger.error(f"Failed to get executions for manager agent {agent_id}: {e}")
            raise
    
    def get_manager_agent_statistics(self, agent_id: int) -> Dict[str, Any]:
        """Get statistics for a manager agent."""
        try:
            manager_agent = self.get_manager_agent_by_id(agent_id)
            if not manager_agent:
                raise ValueError(f"Manager agent {agent_id} not found")
            
            # Get execution statistics
            total_executions = self.db_session.query(Execution).filter(
                Execution.metadata["manager_agent_id"].astext == str(agent_id)
            ).count()
            
            successful_executions = self.db_session.query(Execution).filter(
                Execution.metadata["manager_agent_id"].astext == str(agent_id),
                Execution.status == ExecutionStatus.COMPLETED
            ).count()
            
            failed_executions = self.db_session.query(Execution).filter(
                Execution.metadata["manager_agent_id"].astext == str(agent_id),
                Execution.status == ExecutionStatus.FAILED
            ).count()
            
            # Calculate success rate
            success_rate = (successful_executions / total_executions * 100) if total_executions > 0 else 0
            
            statistics = {
                "agent_id": agent_id,
                "total_executions": total_executions,
                "successful_executions": successful_executions,
                "failed_executions": failed_executions,
                "success_rate": round(success_rate, 2),
                "manager_type": manager_agent.manager_type,
                "can_generate_tasks": manager_agent.can_generate_tasks,
                "created_at": manager_agent.created_at.isoformat() if hasattr(manager_agent, 'created_at') else None
            }
            
            return statistics
        
        except Exception as e:
            logger.error(f"Failed to get statistics for manager agent {agent_id}: {e}")
            raise


def get_manager_agent_service(db_session: Session) -> ManagerAgentService:
    """Get manager agent service instance."""
    return ManagerAgentService(db_session) 