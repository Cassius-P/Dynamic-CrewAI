"""Manager Agent wrapper for specialized CrewAI manager agent functionality."""

from typing import List, Optional, Dict, Any
from crewai import Agent as CrewAIAgent, Task

from app.models.agent import Agent as AgentModel
from app.core.agent_wrapper import AgentWrapper
from app.tools.task_generation import TaskGenerator
from app.tools.delegation_tools import TaskDecompositionTool, AgentCoordinationTool, DelegationValidationTool


class ManagerAgentWrapper:
    """Wrapper class for managing CrewAI manager agents with specialized functionality."""
    
    def __init__(self, agent_wrapper: Optional[AgentWrapper] = None):
        """Initialize the manager agent wrapper.
        
        Args:
            agent_wrapper: Base agent wrapper instance for agent management
        """
        self.agent_wrapper = agent_wrapper or AgentWrapper()
        self.task_generator = TaskGenerator()
    
    def is_manager_agent(self, agent_model: AgentModel) -> bool:
        """Check if an agent model represents a manager agent.
        
        Args:
            agent_model: Agent model to check
            
        Returns:
            True if the agent is a manager agent, False otherwise
        """
        return (
            agent_model.manager_type is not None or
            agent_model.can_generate_tasks is True or
            (agent_model.allow_delegation is True and agent_model.manager_config is not None)
        )
    
    def create_manager_agent_from_model(self, agent_model: AgentModel, 
                                      llm_provider=None) -> CrewAIAgent:
        """Create CrewAI manager agent from database model.
        
        Args:
            agent_model: Manager agent model instance from database
            llm_provider: LLM provider model (optional)
            
        Returns:
            Configured CrewAI Agent instance with manager capabilities
            
        Raises:
            ValueError: If agent model is not a manager agent
        """
        if not self.is_manager_agent(agent_model):
            raise ValueError("Agent is not a manager agent")
        
        # Use base agent wrapper to create the agent
        crewai_agent = self.agent_wrapper.create_agent_from_model(
            agent_model, llm_provider
        )
        
        # Ensure delegation is enabled for manager agents
        if hasattr(crewai_agent, 'allow_delegation'):
            crewai_agent.allow_delegation = True
        
        return crewai_agent
    
    def create_manager_agent_with_delegation_tools(self, agent_model: AgentModel, 
                                                  llm_provider=None) -> CrewAIAgent:
        """Create manager agent optimized for CrewAI native delegation.
        
        Args:
            agent_model: Manager agent model instance from database
            llm_provider: LLM provider model (optional)
            
        Returns:
            Configured CrewAI Agent instance with delegation tools and capabilities
            
        Raises:
            ValueError: If agent model is not a manager agent
        """
        if not self.is_manager_agent(agent_model):
            raise ValueError("Agent is not a manager agent")
        
        # Use base agent wrapper to create the agent
        crewai_agent = self.agent_wrapper.create_agent_from_model(
            agent_model, llm_provider
        )
        
        # Enhanced configuration for delegation
        crewai_agent.allow_delegation = True  # REQUIRED for CrewAI delegation
        crewai_agent.verbose = True
        
        # Add delegation-specific tools
        delegation_tools = [
            TaskDecompositionTool(),
            AgentCoordinationTool(),
            DelegationValidationTool()
        ]
        
        # Combine existing tools with delegation tools
        existing_tools = getattr(crewai_agent, 'tools', []) or []
        crewai_agent.tools = existing_tools + delegation_tools
        
        # Enhanced system message for delegation behavior
        enhanced_backstory = self._build_delegation_system_message(agent_model)
        crewai_agent.backstory = enhanced_backstory
        
        return crewai_agent
    
    def _build_delegation_system_message(self, manager_data: AgentModel) -> str:
        """Build enhanced system message for delegation-capable manager agents.
        
        Args:
            manager_data: Manager agent model
            
        Returns:
            Enhanced backstory/system message for delegation
        """
        base_backstory = getattr(manager_data, 'backstory', '')
        
        delegation_enhancement = f"""
        
        DELEGATION CAPABILITIES:
        You are {manager_data.role}, a manager agent responsible for coordinating a team through intelligent delegation.
        
        Your core capabilities:
        - Analyze high-level objectives and break them into specific tasks
        - Assign tasks to team members based on their roles and capabilities  
        - Monitor progress and provide guidance
        - Make autonomous delegation decisions using CrewAI's hierarchical process
        
        When given an objective:
        1. Analyze the requirements and decompose into actionable tasks
        2. Consider each team member's role and expertise
        3. Create optimal task assignments with clear dependencies
        4. Delegate tasks using CrewAI's built-in delegation system
        5. Coordinate execution and ensure quality outcomes
        
        Use your delegation tools and CrewAI's hierarchical process to achieve objectives efficiently.
        """
        
        return base_backstory + delegation_enhancement
    
    def generate_tasks_from_text(self, manager_agent: AgentModel, 
                               text_input: str) -> List[Task]:
        """Generate CrewAI tasks from text input using manager agent.
        
        Args:
            manager_agent: Manager agent model with task generation capability
            text_input: Text description of work to be done
            
        Returns:
            List of CrewAI Task objects
            
        Raises:
            ValueError: If agent cannot generate tasks
        """
        if manager_agent.can_generate_tasks is not True:
            raise ValueError("Agent cannot generate tasks")
        
        return self.task_generator.generate_tasks(text_input, manager_agent)
    
    def get_manager_config(self, agent_model: AgentModel) -> Dict[str, Any]:
        """Get manager configuration with defaults.
        
        Args:
            agent_model: Manager agent model
            
        Returns:
            Manager configuration dictionary
        """
        manager_config = getattr(agent_model, 'manager_config', None)
        if manager_config is not None:
            return manager_config
        
        # Return default configuration
        return {
            "task_generation_llm": "gpt-4",
            "max_tasks_per_request": 10,
            "delegation_strategy": "sequential",
            "task_validation_enabled": True,
            "auto_assign_agents": True
        }
    
    def validate_manager_agent(self, agent_model: AgentModel) -> Dict[str, Any]:
        """Validate manager agent configuration.
        
        Args:
            agent_model: Manager agent model to validate
            
        Returns:
            Dict with validation results containing 'valid' bool and 'errors' list
        """
        errors = []
        
        # Check manager type
        valid_types = ["hierarchical", "collaborative", "sequential"]
        if agent_model.manager_type is not None and agent_model.manager_type not in valid_types:
            errors.append(f"Invalid manager_type: {agent_model.manager_type}")
        
        # Check delegation capability
        manager_type = getattr(agent_model, 'manager_type', None)
        allow_delegation = getattr(agent_model, 'allow_delegation', None)
        if manager_type is not None and allow_delegation is not True:
            errors.append("Manager agents should have allow_delegation=True")
        
        # Check required fields
        role = getattr(agent_model, 'role', None)
        if role is None or role == "":
            errors.append("Manager agent must have a role")
        
        goal = getattr(agent_model, 'goal', None)
        if goal is None or goal == "":
            errors.append("Manager agent must have a goal")
        
        backstory = getattr(agent_model, 'backstory', None)
        if backstory is None or backstory == "":
            errors.append("Manager agent must have a backstory")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def assign_tasks_to_agents(self, manager_agent: AgentModel, 
                             tasks: List[Dict[str, Any]], 
                             available_agents: List[CrewAIAgent]) -> List[Dict[str, Any]]:
        """Assign generated tasks to available agents based on delegation strategy.
        
        Args:
            manager_agent: Manager agent model
            tasks: List of task dictionaries
            available_agents: List of available CrewAI agents
            
        Returns:
            List of tasks with assigned agents
        """
        if not available_agents:
            return tasks
        
        strategy = self.get_delegation_strategy(manager_agent)
        assigned_tasks = []
        
        for i, task in enumerate(tasks):
            if strategy == "round_robin":
                agent_index = i % len(available_agents)
                assigned_agent = available_agents[agent_index]
            elif strategy == "random":
                import random
                assigned_agent = random.choice(available_agents)
            else:  # sequential (default)
                assigned_agent = available_agents[0] if available_agents else None
            
            task_copy = task.copy()
            task_copy["agent"] = assigned_agent
            assigned_tasks.append(task_copy)
        
        return assigned_tasks
    
    def get_delegation_strategy(self, agent_model: AgentModel) -> str:
        """Get delegation strategy from manager configuration.
        
        Args:
            agent_model: Manager agent model
            
        Returns:
            Delegation strategy string
        """
        config = self.get_manager_config(agent_model)
        return config.get("delegation_strategy", "sequential")
    
    def create_manager_agent_from_dict(self, agent_config: Dict[str, Any], 
                                     llm_provider=None) -> CrewAIAgent:
        """Create CrewAI manager agent from dictionary configuration.
        
        Args:
            agent_config: Dictionary containing manager agent configuration
            llm_provider: LLM provider model (optional)
            
        Returns:
            Configured CrewAI Agent instance with manager capabilities
            
        Raises:
            ValueError: If agent configuration is invalid for manager
        """
        # Validate manager-specific fields
        if not agent_config.get("allow_delegation", False):
            agent_config["allow_delegation"] = True
        
        # Use base agent wrapper to create the agent
        crewai_agent = self.agent_wrapper.create_agent_from_dict(
            agent_config, llm_provider
        )
        
        return crewai_agent
    
    def get_manager_tools(self, agent_model: AgentModel) -> List[str]:
        """Get specialized tools for manager agents.
        
        Args:
            agent_model: Manager agent model
            
        Returns:
            List of tool names for manager functionality
        """
        base_tools = getattr(agent_model, 'tools', None) or []
        manager_tools = []
        
        # Add task generation tools if capable
        can_generate_tasks = getattr(agent_model, 'can_generate_tasks', None)
        if can_generate_tasks is True:
            manager_tools.extend([
                "task_generator",
                "task_validator"
            ])
        
        # Add coordination tools for hierarchical managers
        manager_type = getattr(agent_model, 'manager_type', None)
        if manager_type == "hierarchical":
            manager_tools.extend([
                "agent_coordinator",
                "progress_tracker",
                "delegation_manager"
            ])
        
        # Add collaboration tools for collaborative managers
        if manager_type == "collaborative":
            manager_tools.extend([
                "consensus_builder",
                "conflict_resolver",
                "team_facilitator"
            ])
        
        return list(set(base_tools + manager_tools))
    
    def create_task_from_description(self, description: str, 
                                   assigned_agent: Optional[CrewAIAgent] = None,
                                   expected_output: Optional[str] = None) -> Task:
        """Create a CrewAI Task from description.
        
        Args:
            description: Task description
            assigned_agent: Agent assigned to the task (optional)
            expected_output: Expected output description (optional)
            
        Returns:
            CrewAI Task instance
        """
        # Only pass required parameters to avoid constructor issues
        if expected_output is None:
            expected_output = f"Completion of: {description}"
        
        if assigned_agent:
            return Task(
                description=description,
                expected_output=expected_output,
                agent=assigned_agent
            )
        else:
            return Task(
                description=description,
                expected_output=expected_output
            )
    
    def get_supported_manager_types(self) -> List[str]:
        """Get list of supported manager types.
        
        Returns:
            List of supported manager type strings
        """
        return ["hierarchical", "collaborative", "sequential"]
    
    def get_default_manager_config(self, manager_type: str) -> Dict[str, Any]:
        """Get default configuration for a specific manager type.
        
        Args:
            manager_type: Type of manager agent
            
        Returns:
            Default configuration dictionary for the manager type
        """
        base_config = {
            "task_generation_llm": "gpt-4",
            "max_tasks_per_request": 10,
            "task_validation_enabled": True,
            "auto_assign_agents": True
        }
        
        if manager_type == "hierarchical":
            base_config.update({
                "delegation_strategy": "hierarchical",
                "max_delegation_depth": 3,
                "approval_required": False,
                "escalation_enabled": True
            })
        elif manager_type == "collaborative":
            base_config.update({
                "delegation_strategy": "consensus",
                "decision_threshold": 0.7,
                "collaboration_style": "democratic",
                "conflict_resolution": "voting"
            })
        elif manager_type == "sequential":
            base_config.update({
                "delegation_strategy": "sequential",
                "task_ordering": "priority",
                "parallel_execution": False
            })
        
        return base_config 