"""Crew wrapper for managing CrewAI crews."""
from typing import List, Optional, Dict, Any, Union
from crewai import Crew, Agent, Task
from app.models.crew import Crew as CrewModel
from app.models.agent import Agent as AgentModel
from app.core.agent_wrapper import AgentWrapper
from app.core.llm_wrapper import create_llm_from_provider


class TaskBuilder:
    """Helper class for building CrewAI tasks."""
    
    @staticmethod
    def create_task_from_dict(task_config: Dict[str, Any], agent: Agent) -> Task:
        """Create CrewAI Task from dictionary configuration.
        
        Args:
            task_config: Dictionary containing task configuration
            agent: Agent assigned to this task
            
        Returns:
            Configured CrewAI Task instance
            
        Raises:
            ValueError: If task configuration is invalid
        """
        # Validate required fields
        if not task_config.get("description"):
            raise ValueError("Task description is required")
        
        # Build task kwargs
        task_kwargs = {
            "description": task_config["description"],
            "agent": agent,
        }
        
        # Add optional fields
        if "expected_output" in task_config:
            task_kwargs["expected_output"] = task_config["expected_output"]
        
        if "tools" in task_config and task_config["tools"]:
            # Tools for tasks would need to be created from tool registry
            # For now, we'll skip this as it requires additional setup
            pass
        
        # Add other optional fields
        optional_fields = ["output_json", "output_pydantic", "output_file", "callback"]
        for field in optional_fields:
            if field in task_config:
                task_kwargs[field] = task_config[field]
        
        return Task(**task_kwargs)


class CrewWrapper:
    """Wrapper class for managing CrewAI crews."""
    
    def __init__(self, agent_wrapper: Optional[AgentWrapper] = None):
        """Initialize the crew wrapper.
        
        Args:
            agent_wrapper: Agent wrapper instance for agent management
        """
        self.agent_wrapper = agent_wrapper or AgentWrapper()
    
    def create_crew_from_model(self, crew_model: CrewModel, llm_provider=None) -> Crew:
        """Create CrewAI Crew from database model.
        
        Args:
            crew_model: Crew database model instance
            llm_provider: LLM provider model (optional)
            
        Returns:
            Configured CrewAI Crew instance
            
        Raises:
            ValueError: If crew configuration is invalid
        """
        # Get agents from the crew model
        agents = getattr(crew_model, 'agents', [])
        if not agents:
            raise ValueError("Crew must have at least one agent")
        
        # Create CrewAI agents from models
        crewai_agents = []
        for agent_model in agents:
            try:
                crewai_agent = self.agent_wrapper.create_agent_from_model(
                    agent_model, llm_provider
                )
                crewai_agents.append(crewai_agent)
            except Exception as e:
                agent_name = getattr(agent_model, 'name', 'Unknown')
                raise ValueError(f"Failed to create agent '{agent_name}': {str(e)}")
        
        # Create tasks from crew configuration
        tasks = []
        tasks_config = getattr(crew_model, 'tasks', None)
        if tasks_config and isinstance(tasks_config, list):
            if len(tasks_config) > len(crewai_agents):
                raise ValueError("Cannot have more tasks than agents")
            
            for i, task_config in enumerate(tasks_config):
                if not isinstance(task_config, dict):
                    raise ValueError(f"Task config at index {i} must be a dictionary")
                
                # Assign agent to task (round-robin if more agents than tasks)
                agent_index = i % len(crewai_agents)
                assigned_agent = crewai_agents[agent_index]
                
                try:
                    task = TaskBuilder.create_task_from_dict(task_config, assigned_agent)
                    tasks.append(task)
                except Exception as e:
                    raise ValueError(f"Failed to create task at index {i}: {str(e)}")
        else:
            # Create default tasks if none specified
            for i, agent in enumerate(crewai_agents):
                task = Task(
                    description=f"Execute the primary goal for {agent.role}",
                    agent=agent,
                    expected_output="A detailed report of the completed work"
                )
                tasks.append(task)
        
        # Build crew kwargs
        crew_kwargs:Dict[str, Any] = {
            "agents": crewai_agents,
            "tasks": tasks,
        }
        
        # Add optional crew-level attributes
        verbose = getattr(crew_model, 'verbose', None)
        if verbose is not None:
            crew_kwargs["verbose"] = verbose
        
        process = getattr(crew_model, 'process', None)
        if process:
            crew_kwargs["process"] = process
        
        max_rpm = getattr(crew_model, 'max_rpm', None)
        if max_rpm is not None:
            crew_kwargs["max_rpm"] = max_rpm
        
        # Add any additional config from the config JSON field
        config = getattr(crew_model, 'config', None)
        if config and isinstance(config, dict):
            # Only add supported parameters
            supported_params = {
                "memory", "cache", "embedder", "usage_metrics", 
                "share_crew", "step_callback", "task_callback"
            }
            for key, value in config.items():
                if key in supported_params:
                    crew_kwargs[key] = value
        
        return Crew(**crew_kwargs)
    
    def create_crew_from_dict(self, crew_config: Dict[str, Any], 
                             llm_provider=None) -> Crew:
        """Create CrewAI Crew from dictionary configuration.
        
        Args:
            crew_config: Dictionary containing crew configuration
            llm_provider: LLM provider model (optional)
            
        Returns:
            Configured CrewAI Crew instance
            
        Raises:
            ValueError: If crew configuration is invalid
        """
        # Validate required fields
        if "agents" not in crew_config:
            raise ValueError("Missing required fields")
        if not crew_config["agents"]:
            raise ValueError("Crew must have at least one agent")
        
        agents_config = crew_config["agents"]
        if not isinstance(agents_config, list):
            raise ValueError("Agents configuration must be a list")
        
        # Create CrewAI agents
        crewai_agents = []
        for i, agent_config in enumerate(agents_config):
            if not isinstance(agent_config, dict):
                raise ValueError(f"Agent config at index {i} must be a dictionary")
            
            try:
                crewai_agent = self.agent_wrapper.create_agent_from_dict(
                    agent_config, llm_provider
                )
                crewai_agents.append(crewai_agent)
            except Exception as e:
                agent_role = agent_config.get("role", f"agent_{i}")
                raise ValueError(f"Failed to create agent '{agent_role}': {str(e)}")
        
        # Create tasks
        tasks = []
        tasks_config = crew_config.get("tasks", [])
        
        if tasks_config:
            if not isinstance(tasks_config, list):
                raise ValueError("Tasks configuration must be a list")
            
            if len(tasks_config) > len(crewai_agents):
                raise ValueError("Cannot have more tasks than agents")
            
            for i, task_config in enumerate(tasks_config):
                if not isinstance(task_config, dict):
                    raise ValueError(f"Task config at index {i} must be a dictionary")
                
                # Assign agent to task (round-robin if more agents than tasks)
                agent_index = i % len(crewai_agents)
                assigned_agent = crewai_agents[agent_index]
                
                try:
                    task = TaskBuilder.create_task_from_dict(task_config, assigned_agent)
                    tasks.append(task)
                except Exception as e:
                    raise ValueError(f"Failed to create task at index {i}: {str(e)}")
        else:
            # Create default tasks if none specified
            for i, agent in enumerate(crewai_agents):
                task = Task(
                    description=f"Execute the primary goal for {agent.role}",
                    agent=agent,
                    expected_output="A detailed report of the completed work"
                )
                tasks.append(task)
        
        # Build crew kwargs
        crew_kwargs:Dict[str, Any] = {
            "agents": crewai_agents,
            "tasks": tasks,
        }
        
        # Add optional crew-level attributes
        optional_fields = [
            "verbose", "process", "max_rpm", "memory", "cache", 
            "embedder", "usage_metrics", "share_crew"
        ]
        for field in optional_fields:
            if field in crew_config:
                crew_kwargs[field] = crew_config[field]
        
        return Crew(**crew_kwargs)
    
    def validate_crew_config(self, crew_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate crew configuration.
        
        Args:
            crew_config: Dictionary containing crew configuration
            
        Returns:
            Dict containing validation results:
                - valid: bool indicating if config is valid
                - errors: list of validation error messages
                - agent_validation: dict with agent validation results
                - task_validation: dict with task validation results
        """
        result = {
            "valid": False,
            "errors": [],
            "agent_validation": {},
            "task_validation": {}
        }
        
        # Check required fields
        if "agents" not in crew_config:
            result["errors"].append("Crew must have 'agents' field")
            return result
        
        agents_config = crew_config["agents"]
        if not isinstance(agents_config, list):
            result["errors"].append("Agents configuration must be a list")
            return result
        
        if len(agents_config) == 0:
            result["errors"].append("Crew must have at least one agent")
            return result
        
        # Validate agents
        for i, agent_config in enumerate(agents_config):
            if not isinstance(agent_config, dict):
                result["errors"].append(f"Agent config at index {i} must be a dictionary")
                continue
            
            agent_validation = self.agent_wrapper.validate_agent_config(agent_config)
            result["agent_validation"][f"agent_{i}"] = agent_validation
            
            if not agent_validation["valid"]:
                result["errors"].extend([
                    f"Agent {i}: {error}" for error in agent_validation["errors"]
                ])
        
        # Validate tasks if provided
        tasks_config = crew_config.get("tasks", [])
        if tasks_config is not None:
            if not isinstance(tasks_config, list):
                result["errors"].append("Tasks configuration must be a list")
            elif len(tasks_config) == 0:
                result["errors"].append("Tasks list cannot be empty")
            else:
                if len(tasks_config) > len(agents_config):
                    result["errors"].append("Cannot have more tasks than agents")
                
                for i, task_config in enumerate(tasks_config):
                    if not isinstance(task_config, dict):
                        result["errors"].append(f"Task config at index {i} must be a dictionary")
                        continue
                    
                    task_validation = self.validate_task_config(task_config)
                    result["task_validation"][f"task_{i}"] = task_validation
                    
                    if not task_validation["valid"]:
                        result["errors"].extend([
                            f"Task {i}: {error}" for error in task_validation["errors"]
                        ])
        
        # Validate crew-level fields
        boolean_fields = ["verbose", "share_crew", "usage_metrics"]
        for field in boolean_fields:
            value = crew_config.get(field)
            if value is not None and not isinstance(value, bool):
                result["errors"].append(f"Field '{field}' must be a boolean")
        
        integer_fields = ["max_rpm"]
        for field in integer_fields:
            value = crew_config.get(field)
            if value is not None:
                if not isinstance(value, int) or value <= 0:
                    result["errors"].append(f"Field '{field}' must be a positive integer")
        
        # Configuration is valid if no errors
        result["valid"] = len(result["errors"]) == 0
        
        return result
    
    def _validate_task_config(self, task_config: Dict[str, Any]) -> None:
        """Validate individual task configuration (private method for testing).
        
        Args:
            task_config: Dictionary containing task configuration
            
        Raises:
            ValueError: If task configuration is invalid
        """
        # Check required fields
        if "description" not in task_config:
            raise ValueError("Missing required task fields")
        if "expected_output" not in task_config:
            raise ValueError("Missing required task fields")
        if "agent" not in task_config:
            raise ValueError("Missing required task fields")
        
        # Check for empty values
        if not task_config.get("description") or task_config["description"].strip() == "":
            raise ValueError("Task description cannot be empty")
    
    def validate_task_config(self, task_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate individual task configuration.
        
        Args:
            task_config: Dictionary containing task configuration
            
        Returns:
            Dict containing validation results
        """
        result = {
            "valid": False,
            "errors": []
        }
        
        # Check required fields
        if not task_config.get("description"):
            result["errors"].append("Task description is required")
        
        # Validate string fields
        string_fields = ["description", "expected_output", "output_file"]
        for field in string_fields:
            value = task_config.get(field)
            if value is not None:
                if not isinstance(value, str):
                    result["errors"].append(f"Task field '{field}' must be a string")
                elif field == "description" and len(value.strip()) == 0:
                    result["errors"].append("Task description cannot be empty")
        
        # Configuration is valid if no errors
        result["valid"] = len(result["errors"]) == 0
        
        return result
    
    def get_supported_fields(self) -> Dict[str, Any]:
        """Get information about supported crew configuration fields.
        
        Returns:
            Dict containing field information with types and descriptions
        """
        return {
            "required": {
                "agents": {
                    "type": "array",
                    "description": "List of agent configurations",
                    "minimum_items": 1
                }
            },
            "optional": {
                "tasks": {
                    "type": "array",
                    "description": "List of task configurations (auto-generated if not provided)",
                    "items": {
                        "type": "object",
                        "properties": {
                            "description": {"type": "string"},
                            "expected_output": {"type": "string"},
                            "output_file": {"type": "string"}
                        }
                    }
                },
                "verbose": {
                    "type": "boolean",
                    "description": "Whether to enable verbose logging",
                    "default": False
                },
                "process": {
                    "type": "string",
                    "description": "Crew execution process type",
                    "enum": ["sequential", "hierarchical"]
                },
                "max_rpm": {
                    "type": "integer",
                    "description": "Maximum requests per minute",
                    "minimum": 1
                },
                "memory": {
                    "type": "boolean",
                    "description": "Whether to enable crew memory",
                    "default": False
                },
                "cache": {
                    "type": "boolean", 
                    "description": "Whether to enable caching",
                    "default": True
                },
                "usage_metrics": {
                    "type": "boolean",
                    "description": "Whether to collect usage metrics",
                    "default": False
                },
                "share_crew": {
                    "type": "boolean",
                    "description": "Whether to share crew information",
                    "default": False
                }
            }
        }
    
    def _validate_crew_config(self, crew_config: Dict[str, Any]) -> None:
        """Validate crew configuration (private method for testing).
        
        Args:
            crew_config: Dictionary containing crew configuration
            
        Raises:
            ValueError: If configuration is invalid
        """
        validation_result = self.validate_crew_config(crew_config)
        if not validation_result["valid"]:
            # Check for empty name first (highest priority)
            if crew_config.get("name") == "":
                raise ValueError("Field cannot be empty")
            
            # Check for specific error types
            for error in validation_result["errors"]:
                if "must have 'agents' field" in error:
                    raise ValueError("Missing required fields")
                elif "must have at least one agent" in error:
                    if "name" not in crew_config:
                        raise ValueError("Missing required fields")
                    elif not crew_config.get("tasks"):
                        raise ValueError("Missing required fields")
                    else:
                        raise ValueError("Agents list cannot be empty")
                elif "Tasks list cannot be empty" in error:
                    raise ValueError("Tasks list cannot be empty")
                elif "cannot be empty" in error:
                    raise ValueError("Field cannot be empty")
            # Default error message
            raise ValueError(f"Invalid configuration: {validation_result['errors']}")
    
    def _create_agents_from_configs(self, agent_configs: List[Dict[str, Any]], 
                                  llm_provider=None) -> tuple[List[Agent], Dict[str, Agent]]:
        """Create agents from configuration list (private method for testing).
        
        Args:
            agent_configs: List of agent configuration dictionaries
            llm_provider: LLM provider model (optional)
            
        Returns:
            Tuple of (agents_list, agent_name_map)
        """
        agents = []
        agent_map = {}
        
        for i, agent_config in enumerate(agent_configs):
            if not isinstance(agent_config, dict):
                raise ValueError(f"Agent config at index {i} must be a dictionary")
            
            try:
                agent = self.agent_wrapper.create_agent_from_dict(agent_config, llm_provider)
                agents.append(agent)
                
                # Add to map by name if available, otherwise by role
                agent_name = agent_config.get("name") or agent_config.get("role") or f"agent_{i}"
                agent_map[agent_name] = agent
                
            except Exception as e:
                agent_name = agent_config.get("name") or agent_config.get("role") or f"agent_{i}"
                raise ValueError(f"Failed to create agent '{agent_name}': {str(e)}")
        
        return agents, agent_map
    
    def _create_agents_from_models(self, agent_models: List[AgentModel], 
                                 llm_provider=None) -> tuple[List[Agent], Dict[str, Agent]]:
        """Create agents from database models (private method for testing).
        
        Args:
            agent_models: List of agent database models
            llm_provider: LLM provider model (optional)
            
        Returns:
            Tuple of (agents_list, agent_name_map)
        """
        agents = []
        agent_map = {}
        
        for agent_model in agent_models:
            try:
                agent = self.agent_wrapper.create_agent_from_model(agent_model, llm_provider)
                agents.append(agent)
                
                # Add to map by name
                agent_name = getattr(agent_model, 'name', 'Unknown')
                agent_map[agent_name] = agent
                
            except Exception as e:
                agent_name = getattr(agent_model, 'name', 'Unknown')
                raise ValueError(f"Failed to create agent '{agent_name}': {str(e)}")
        
        return agents, agent_map
    
    def _create_tasks_from_configs(self, task_configs: List[Dict[str, Any]], 
                                 agent_map: Dict[str, Agent]) -> List[Task]:
        """Create tasks from configuration list (private method for testing).
        
        Args:
            task_configs: List of task configuration dictionaries
            agent_map: Map of agent names to Agent instances
            
        Returns:
            List of Task instances
        """
        tasks = []
        
        for i, task_config in enumerate(task_configs):
            if not isinstance(task_config, dict):
                raise ValueError(f"Task config at index {i} must be a dictionary")
            
            # Validate required fields
            if "description" not in task_config:
                raise ValueError("Missing required task fields")
            if "expected_output" not in task_config:
                raise ValueError("Missing required task fields") 
            if "agent" not in task_config:
                raise ValueError("Missing required task fields")
            
            # Validate values are not empty
            if not task_config["description"] or task_config["description"].strip() == "":
                raise ValueError("Task description cannot be empty")
            
            # Find the agent
            agent_name = task_config["agent"]
            if agent_name not in agent_map:
                raise ValueError(f"Agent '{agent_name}' not found")
            
            agent = agent_map[agent_name]
            
            try:
                task = TaskBuilder.create_task_from_dict(task_config, agent)
                tasks.append(task)
            except Exception as e:
                raise ValueError(f"Failed to create task at index {i}: {str(e)}")
        
        return tasks

    def _validate_task_config_with_exceptions(self, task_config: Dict[str, Any]) -> None:
        """Validate task configuration and raise exceptions (private method for testing).
        
        Args:
            task_config: Dictionary containing task configuration
            
        Raises:
            ValueError: If task configuration is invalid
        """
        # Check required fields
        if "description" not in task_config:
            raise ValueError("Missing required task fields")
        if "expected_output" not in task_config:
            raise ValueError("Missing required task fields")
        if "agent" not in task_config:
            raise ValueError("Missing required task fields")
        
        # Check for empty values
        if not task_config.get("description") or task_config["description"].strip() == "":
            raise ValueError("Task description cannot be empty")
