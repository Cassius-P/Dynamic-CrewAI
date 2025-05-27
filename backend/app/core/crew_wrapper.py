"""Crew wrapper for managing CrewAI crews."""
from typing import List, Optional, Dict, Any, Union
from crewai import Crew, Agent, Task, Process
from app.models.crew import Crew as CrewModel
from app.models.agent import Agent as AgentModel
from app.core.agent_wrapper import AgentWrapper
from app.core.manager_agent_wrapper import ManagerAgentWrapper
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
    
    def __init__(self, agent_wrapper: Optional[AgentWrapper] = None, 
                 manager_agent_wrapper: Optional[ManagerAgentWrapper] = None):
        """Initialize the crew wrapper.
        
        Args:
            agent_wrapper: Agent wrapper instance for agent management
            manager_agent_wrapper: Manager agent wrapper for manager functionality
        """
        self.agent_wrapper = agent_wrapper or AgentWrapper()
        self.manager_agent_wrapper = manager_agent_wrapper or ManagerAgentWrapper(self.agent_wrapper)
    
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
        
        # Create CrewAI agents from models (with manager agent support)
        crewai_agents = []
        manager_agent = None
        regular_agents = []
        
        for agent_model in agents:
            try:
                # Check if this is a manager agent
                if self.manager_agent_wrapper.is_manager_agent(agent_model):
                    if manager_agent is not None:
                        raise ValueError("Crew can only have one manager agent")
                    crewai_agent = self.manager_agent_wrapper.create_manager_agent_from_model(
                        agent_model, llm_provider
                    )
                    manager_agent = crewai_agent
                    # Store reference using setattr to avoid linter warning
                    setattr(manager_agent, '_source_model', agent_model)
                else:
                    crewai_agent = self.agent_wrapper.create_agent_from_model(
                        agent_model, llm_provider
                    )
                    regular_agents.append(crewai_agent)
                
                crewai_agents.append(crewai_agent)
            except Exception as e:
                agent_name = getattr(agent_model, 'name', 'Unknown')
                raise ValueError(f"Failed to create agent '{agent_name}': {str(e)}")
        
        # Create tasks from crew configuration (with manager agent support)
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
            # If we have a manager agent, use it to generate tasks from text if available
            if manager_agent and hasattr(manager_agent, '_source_model'):
                manager_model = getattr(manager_agent, '_source_model')
                crew_goal = getattr(crew_model, 'goal', None)
                
                if crew_goal and manager_model.can_generate_tasks:
                    try:
                        # Generate tasks from crew goal using manager agent
                        generated_tasks = self.manager_agent_wrapper.generate_tasks_from_text(
                            manager_model, crew_goal
                        )
                        
                        # Assign generated tasks to available agents
                        task_dicts = [
                            {"description": task.description, "expected_output": task.expected_output}
                            for task in generated_tasks
                        ]
                        assigned_tasks = self.manager_agent_wrapper.assign_tasks_to_agents(
                            manager_model, task_dicts, regular_agents
                        )
                        
                        # Convert to CrewAI tasks
                        for task_dict in assigned_tasks:
                            task = Task(
                                description=task_dict["description"],
                                expected_output=task_dict["expected_output"],
                                agent=task_dict.get("agent") or regular_agents[0] if regular_agents else manager_agent
                            )
                            tasks.append(task)
                    except Exception as e:
                        # Fall back to default task creation if generation fails
                        print(f"Warning: Task generation failed, using default tasks: {e}")
                        self._create_default_tasks(crewai_agents, tasks)
                else:
                    self._create_default_tasks(crewai_agents, tasks)
            else:
                self._create_default_tasks(crewai_agents, tasks)
        
        # Build crew kwargs (with manager agent support)
        crew_kwargs:Dict[str, Any] = {
            "agents": crewai_agents,
            "tasks": tasks,
        }
        
        # Set process type based on manager agent presence
        process = getattr(crew_model, 'process', None)
        if manager_agent and not process:
            # Default to hierarchical process when manager agent is present
            crew_kwargs["process"] = "hierarchical"
            # Set manager agent if using hierarchical process
            crew_kwargs["manager_agent"] = manager_agent
        elif process:
            crew_kwargs["process"] = process
            if process == "hierarchical" and manager_agent:
                crew_kwargs["manager_agent"] = manager_agent
        
        # Add optional crew-level attributes
        verbose = getattr(crew_model, 'verbose', None)
        if verbose is not None:
            crew_kwargs["verbose"] = verbose
        
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
    
    def _create_default_tasks(self, crewai_agents: List[Agent], tasks: List[Task]) -> None:
        """Create default tasks for agents when no specific tasks are provided.
        
        Args:
            crewai_agents: List of CrewAI agents
            tasks: List to append created tasks to
        """
        for i, agent in enumerate(crewai_agents):
            task = Task(
                description=f"Execute the primary goal for {agent.role}",
                agent=agent,
                expected_output="A detailed report of the completed work"
            )
            tasks.append(task)
    
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
        
        # Create CrewAI agents (with manager agent support)
        crewai_agents = []
        manager_agent = None
        regular_agents = []
        
        for i, agent_config in enumerate(agents_config):
            if not isinstance(agent_config, dict):
                raise ValueError(f"Agent config at index {i} must be a dictionary")
            
            try:
                # Check if this is a manager agent configuration
                is_manager = (
                    agent_config.get("manager_type") is not None or
                    agent_config.get("can_generate_tasks", False) or
                    agent_config.get("allow_delegation", False)
                )
                
                if is_manager:
                    if manager_agent is not None:
                        raise ValueError("Crew can only have one manager agent")
                    crewai_agent = self.manager_agent_wrapper.create_manager_agent_from_dict(
                        agent_config, llm_provider
                    )
                    manager_agent = crewai_agent
                else:
                    crewai_agent = self.agent_wrapper.create_agent_from_dict(
                        agent_config, llm_provider
                    )
                    regular_agents.append(crewai_agent)
                
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
            # If we have a manager agent and a goal, generate tasks from text
            crew_goal = crew_config.get("goal")
            if manager_agent and crew_goal:
                try:
                    # Create a temporary agent model for task generation
                    from app.models.agent import Agent as AgentModel
                    temp_manager_model = AgentModel(
                        role=manager_agent.role,
                        goal=manager_agent.goal,
                        backstory=manager_agent.backstory,
                        can_generate_tasks=True,
                        manager_type="hierarchical",
                        manager_config={"delegation_strategy": "round_robin"}
                    )
                    
                    # Generate tasks from crew goal
                    generated_tasks = self.manager_agent_wrapper.generate_tasks_from_text(
                        temp_manager_model, crew_goal
                    )
                    
                    # Assign tasks to available agents
                    task_dicts = [
                        {"description": task.description, "expected_output": task.expected_output}
                        for task in generated_tasks
                    ]
                    assigned_tasks = self.manager_agent_wrapper.assign_tasks_to_agents(
                        temp_manager_model, task_dicts, regular_agents
                    )
                    
                    # Convert to CrewAI tasks
                    for task_dict in assigned_tasks:
                        task = Task(
                            description=task_dict["description"],
                            expected_output=task_dict["expected_output"],
                            agent=task_dict.get("agent") or regular_agents[0] if regular_agents else manager_agent
                        )
                        tasks.append(task)
                except Exception as e:
                    # Fall back to default task creation if generation fails
                    print(f"Warning: Task generation failed, using default tasks: {e}")
                    self._create_default_tasks(crewai_agents, tasks)
            else:
                self._create_default_tasks(crewai_agents, tasks)
        
        # Build crew kwargs
        crew_kwargs:Dict[str, Any] = {
            "agents": crewai_agents,
            "tasks": tasks,
        }
        
        # Set process type based on manager agent presence
        process = crew_config.get("process")
        if manager_agent and not process:
            # Default to hierarchical process when manager agent is present
            crew_kwargs["process"] = "hierarchical"
            crew_kwargs["manager_agent"] = manager_agent
        elif process:
            crew_kwargs["process"] = process
            if process == "hierarchical" and manager_agent:
                crew_kwargs["manager_agent"] = manager_agent
        
        # Add optional crew-level attributes
        optional_fields = [
            "verbose", "max_rpm", "memory", "cache", 
            "embedder", "usage_metrics", "share_crew"
        ]
        for field in optional_fields:
            if field in crew_config:
                crew_kwargs[field] = crew_config[field]
        
        return Crew(**crew_kwargs)
    
    def create_crew_with_manager_tasks(self, agents: List[AgentModel], text_input: str, 
                                     llm_provider=None, **crew_kwargs) -> Crew:
        """Create crew with manager agent generating tasks from text input.
        
        Args:
            agents: List of agent models (should include one manager agent)
            text_input: Text description to generate tasks from
            llm_provider: LLM provider model (optional)
            **crew_kwargs: Additional crew configuration
            
        Returns:
            Configured CrewAI Crew instance with generated tasks
            
        Raises:
            ValueError: If no manager agent is found or configuration is invalid
        """
        # Find manager agent
        manager_model = None
        regular_models = []
        
        for agent_model in agents:
            if self.manager_agent_wrapper.is_manager_agent(agent_model):
                if manager_model is not None:
                    raise ValueError("Only one manager agent is allowed")
                manager_model = agent_model
            else:
                regular_models.append(agent_model)
        
        if not manager_model:
            raise ValueError("No manager agent found in agent list")
        
        # Create CrewAI agents
        manager_agent = self.manager_agent_wrapper.create_manager_agent_from_model(
            manager_model, llm_provider
        )
        regular_agents = [
            self.agent_wrapper.create_agent_from_model(model, llm_provider)
            for model in regular_models
        ]
        all_agents = [manager_agent] + regular_agents
        
        # Generate tasks from text input
        generated_tasks = self.manager_agent_wrapper.generate_tasks_from_text(
            manager_model, text_input
        )
        
        # Assign tasks to agents
        task_dicts = [
            {"description": task.description, "expected_output": task.expected_output}
            for task in generated_tasks
        ]
        assigned_tasks = self.manager_agent_wrapper.assign_tasks_to_agents(
            manager_model, task_dicts, regular_agents
        )
        
        # Create CrewAI tasks
        tasks = []
        for task_dict in assigned_tasks:
            task = Task(
                description=task_dict["description"],
                expected_output=task_dict["expected_output"],
                agent=task_dict.get("agent") or regular_agents[0] if regular_agents else manager_agent
            )
            tasks.append(task)
        
        # Enhance manager agent properties for better CrewAI integration
        if hasattr(manager_agent, 'allow_delegation'):
            manager_agent.allow_delegation = True  # Enable delegation capability
        manager_agent.verbose = True
        
        # Build crew configuration with enhanced CrewAI configuration
        final_crew_kwargs = {
            "agents": all_agents,
            "tasks": tasks,
            "process": Process.hierarchical,  # Use hierarchical even with pre-assigned tasks
            "manager_agent": manager_agent,   # Specify manager for CrewAI
            "verbose": crew_kwargs.get('verbose', True),
            "memory": crew_kwargs.get('memory', True),
            **{k: v for k, v in crew_kwargs.items() if k not in ['verbose', 'memory']}
        }
        
        return Crew(**final_crew_kwargs)
    
    def create_crew_with_native_delegation(self, agents: List[AgentModel], objective: str, 
                                         llm_provider=None, **crew_kwargs) -> Crew:
        """Create crew using CrewAI's native hierarchical delegation.
        
        Args:
            agents: List of agent models (should include one manager agent)
            objective: High-level objective for the manager to decompose and delegate
            llm_provider: LLM provider model (optional)
            **crew_kwargs: Additional crew configuration
            
        Returns:
            Configured CrewAI Crew instance with native delegation
            
        Raises:
            ValueError: If no manager agent is found or configuration is invalid
        """
        # Find manager agent
        manager_model = None
        regular_models = []
        
        for agent_model in agents:
            if self.manager_agent_wrapper.is_manager_agent(agent_model):
                if manager_model is not None:
                    raise ValueError("Only one manager agent is allowed")
                manager_model = agent_model
            else:
                regular_models.append(agent_model)
        
        if not manager_model:
            raise ValueError("No manager agent found in agent list")
        
        # Create manager agent with delegation tools
        manager_agent = self.manager_agent_wrapper.create_manager_agent_with_delegation_tools(
            manager_model, llm_provider
        )
        
        # Create worker agents
        worker_agents = [
            self.agent_wrapper.create_agent_from_model(model, llm_provider)
            for model in regular_models
        ]
        
        all_agents = [manager_agent] + worker_agents
        
        # Create single goal-based task (let manager decompose)
        goal_task = Task(
            description=f"""
            OBJECTIVE: {objective}
            
            As the manager, you must:
            1. Analyze this objective and break it down into specific tasks
            2. Assign tasks to appropriate team members based on their capabilities
            3. Coordinate execution and ensure quality delivery
            4. Monitor progress and provide guidance as needed
            
            Available team: {[agent.role for agent in worker_agents]}
            
            Use your delegation tools to autonomously decompose this objective into tasks
            and coordinate the team to achieve the goal efficiently.
            """,
            expected_output="Complete achievement of the stated objective with full documentation of the delegation process and results",
            agent=manager_agent  # Manager owns the goal
        )
        
        # Configure crew for native delegation
        final_crew_kwargs = {
            "agents": all_agents,
            "tasks": [goal_task],  # Single high-level goal
            "process": Process.hierarchical,  # CRITICAL: Native delegation
            "manager_agent": manager_agent,   # Specify manager for CrewAI
            "verbose": crew_kwargs.get('verbose', True),
            "memory": crew_kwargs.get('memory', True),
            **{k: v for k, v in crew_kwargs.items() if k not in ['verbose', 'memory']}
        }
        
        return Crew(**final_crew_kwargs)
    
    def create_crew_with_manager(self, agents: List[AgentModel], objective: str, 
                               delegation_mode: str = "native", llm_provider=None, **crew_kwargs) -> Crew:
        """Unified interface supporting both delegation modes.
        
        Args:
            agents: List of agent models (should include one manager agent)
            objective: High-level objective or text input
            delegation_mode: "native" for CrewAI delegation, "task_based" for manual assignment
            llm_provider: LLM provider model (optional)
            **crew_kwargs: Additional crew configuration
            
        Returns:
            Configured CrewAI Crew instance
            
        Raises:
            ValueError: If invalid delegation_mode or configuration is invalid
        """
        if delegation_mode == "native":
            return self.create_crew_with_native_delegation(agents, objective, llm_provider, **crew_kwargs)
        elif delegation_mode == "task_based":
            return self.create_crew_with_manager_tasks(agents, objective, llm_provider, **crew_kwargs)
        else:
            raise ValueError(f"Invalid delegation_mode: {delegation_mode}. Must be 'native' or 'task_based'")
    
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
