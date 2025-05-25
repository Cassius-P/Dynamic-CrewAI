from typing import List, Optional, Dict, Any, cast
from crewai import Agent
from crewai.tools import BaseTool
from app.models.agent import Agent as AgentModel
from app.models.llm_provider import LLMProvider
from app.core.llm_wrapper import create_llm_from_provider, LLMWrapper
from app.core.tool_registry import ToolRegistry


class AgentWrapper:
    """Wrapper class for managing CrewAI agents."""
    
    def __init__(self, tool_registry: Optional[ToolRegistry] = None):
        """Initialize the agent wrapper.
        
        Args:
            tool_registry: Tool registry instance for tool management
        """
        self.tool_registry = tool_registry or ToolRegistry()
    
    def create_agent_from_model(self, agent_model: AgentModel, llm_provider=None) -> Agent:
        """Create CrewAI Agent from database model.
        
        Args:
            agent_model: Agent model instance from database
            llm_provider: LLM provider model (optional)
            
        Returns:
            Configured CrewAI Agent instance
            
        Raises:
            ValueError: If agent model is invalid
        """
        # Extract required fields
        role = getattr(agent_model, 'role', '')
        goal = getattr(agent_model, 'goal', '')
        backstory = getattr(agent_model, 'backstory', '')
        
        if not role:
            raise ValueError("Agent role is required")
        if not goal:
            raise ValueError("Agent goal is required")
        if not backstory:
            raise ValueError("Agent backstory is required")
          # Build agent kwargs
        agent_kwargs: Dict[str, Any] = {
            "role": role,
            "goal": goal,
            "backstory": backstory,
        }
        
        # Add optional attributes with type conversion
        verbose = getattr(agent_model, 'verbose', None)
        if verbose is not None:
            agent_kwargs["verbose"] = bool(verbose) if not isinstance(verbose, bool) else verbose
        
        allow_delegation = getattr(agent_model, 'allow_delegation', None)
        if allow_delegation is not None:
            agent_kwargs["allow_delegation"] = bool(allow_delegation) if not isinstance(allow_delegation, bool) else allow_delegation
        
        max_iter = getattr(agent_model, 'max_iter', None)
        if max_iter is not None:
            agent_kwargs["max_iter"] = int(max_iter) if not isinstance(max_iter, int) else max_iter
        
        max_execution_time = getattr(agent_model, 'max_execution_time', None)
        if max_execution_time is not None:
            agent_kwargs["max_execution_time"] = int(max_execution_time) if not isinstance(max_execution_time, int) else max_execution_time
        
        # Add LLM if provided (either as parameter or from model)
        llm_to_use = llm_provider or getattr(agent_model, 'llm_provider', None)
        if llm_to_use:
            llm = LLMWrapper().create_llm_from_model(llm_to_use)
            agent_kwargs["llm"] = llm
        
        # Add tools if configured
        tools_config = getattr(agent_model, 'tools', None)
        if tools_config and isinstance(tools_config, list):
            try:                # Check if it's a list of strings or config dicts
                if tools_config and isinstance(tools_config[0], str):
                    tools = self.tool_registry.create_tools(tools_config)
                else:
                    tools = self.tool_registry.create_tools_from_config(tools_config)
                agent_kwargs["tools"] = tools
            except Exception as e:
                raise ValueError(f"Failed to create tools for agent: {str(e)}")
        
        # Add any additional config from the config JSON field
        config = getattr(agent_model, 'config', None)
        if config and isinstance(config, dict):
            # Only add supported parameters that are compatible with Agent constructor
            supported_params = {
                "system_template", "prompt_template", "response_template"
            }
            for key, value in config.items():
                if key in supported_params and value is not None:
                    agent_kwargs[key] = value
        
        return cast(Agent, Agent(**agent_kwargs))
    
    def create_agent_from_dict(self, agent_config: Dict[str, Any], llm_provider=None) -> Agent:
        """Create CrewAI Agent from dictionary configuration.
        
        Args:
            agent_config: Dictionary containing agent configuration
            llm_provider: LLM provider model (optional)
            
        Returns:
            Configured CrewAI Agent instance
            
        Raises:
            ValueError: If agent configuration is invalid
        """
        # Validate required fields
        required_fields = ["role", "goal", "backstory"]
        missing_fields = [field for field in required_fields if field not in agent_config]
        if missing_fields:
            raise ValueError(f"Missing required fields: {missing_fields}")
          # Build agent kwargs
        agent_kwargs: Dict[str, Any] = {
            "role": agent_config["role"],
            "goal": agent_config["goal"],
            "backstory": agent_config["backstory"],
        }# Add optional fields with type conversion
        optional_field_types = {
            "verbose": bool,
            "allow_delegation": bool,
            "max_iter": int,
            "max_execution_time": int,
            "memory": bool,
            "allow_code_execution": bool,
            "max_retry_limit": int,
            "use_system_prompt": bool,
            "respect_context_window": bool
        }
        
        # Handle template fields separately as they should remain strings
        template_fields = ["system_template", "prompt_template", "response_template"]
        
        for field, field_type in optional_field_types.items():
            if field in agent_config:
                value = agent_config[field]
                if value is not None:
                    try:
                        agent_kwargs[field] = field_type(value)
                    except (ValueError, TypeError):
                        raise ValueError(f"Invalid value for {field}: {value}")
        
        # Add template fields as strings
        for field in template_fields:
            if field in agent_config:
                value = agent_config[field]
                if value is not None and isinstance(value, str):
                    agent_kwargs[field] = value
        
        # Add LLM if provided
        if llm_provider:
            if isinstance(llm_provider, dict):
                # Config dict
                llm = LLMWrapper().create_llm_from_config(llm_provider)
            else:
                # Model object
                llm = LLMWrapper().create_llm_from_model(llm_provider)
            agent_kwargs["llm"] = llm
        
        # Add tools if configured
        tools_config = agent_config.get("tools", [])
        if tools_config:
            try:
                tools = self.tool_registry.create_tools(tools_config)
                agent_kwargs["tools"] = tools
            except Exception as e:
                raise ValueError(f"Failed to create tools for agent: {str(e)}")
        
        # Cast known numeric fields to ensure proper types
        for field in ["max_execution_time", "max_iter", "max_retry_limit"]:
            if field in agent_kwargs and isinstance(agent_kwargs[field], str):
                try:
                    agent_kwargs[field] = int(agent_kwargs[field])
                except (ValueError, TypeError):
                    pass  # If conversion fails, let CrewAI handle it
        
        # Cast boolean fields to ensure proper types
        for field in ["verbose", "allow_delegation", "memory", "allow_code_execution", 
                      "use_system_prompt", "respect_context_window"]:
            if field in agent_kwargs and isinstance(agent_kwargs[field], str):
                agent_kwargs[field] = agent_kwargs[field].lower() == "true"
        
        return cast(Agent, Agent(**agent_kwargs))
    
    def validate_agent_config(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """Validate agent configuration.
        
        Args:
            agent_config: Dictionary containing agent configuration
            
        Returns:
            Dict with validation results containing 'valid' bool and 'errors' list
        """
        result = {"valid": False, "errors": []}
        
        # Check for missing required fields first (field not present at all)
        required_fields = ["role", "goal", "backstory"]
        missing_fields = [field for field in required_fields if field not in agent_config]
        if missing_fields:
            result["errors"].append(f"Missing required fields: {missing_fields}")
        
        # Validate string fields are not empty or None
        string_fields = ["name", "role", "goal", "backstory"]
        for field in string_fields:
            if field in agent_config:  # Field is present
                value = agent_config[field]
                if value is None:
                    result["errors"].append(f"Field '{field}' cannot be empty")
                elif not isinstance(value, str):
                    result["errors"].append(f"Field '{field}' must be a string")
                elif len(value.strip()) == 0:
                    result["errors"].append(f"Field '{field}' cannot be empty")
        
        # Validate boolean fields
        boolean_fields = ["verbose", "allow_delegation"]
        for field in boolean_fields:
            value = agent_config.get(field)
            if value is not None and not isinstance(value, bool):
                result["errors"].append(f"Field '{field}' must be a boolean")
        
        # Validate integer fields
        integer_fields = ["max_iter", "max_execution_time"]
        for field in integer_fields:
            value = agent_config.get(field)
            if value is not None:
                if not isinstance(value, int) or value <= 0:
                    result["errors"].append(f"Field '{field}' must be a positive integer")
        
        # Validate tools configuration
        tools_config = agent_config.get("tools", [])
        if tools_config:
            if not isinstance(tools_config, list):
                result["errors"].append("Tools configuration must be a list")
            else:
                for i, tool_config in enumerate(tools_config):
                    if not isinstance(tool_config, dict):
                        result["errors"].append(f"Tool config at index {i} must be a dictionary")
                        continue
                    
                    tool_name = tool_config.get("name")
                    if not tool_name:
                        result["errors"].append(f"Tool config at index {i} missing 'name' field")
                        continue
                    
                    # Validate individual tool config
                    tool_params = tool_config.get("parameters", {})
                    if not isinstance(tool_params, dict):
                        result["errors"].append(f"Tool config at index {i} parameters must be a dictionary")
        
        # Configuration is valid if no errors
        result["valid"] = len(result["errors"]) == 0
        
        return result
    
    def get_supported_fields(self) -> Dict[str, Any]:
        """Get information about supported agent configuration fields.
        
        Returns:
            Dict containing field information with types and descriptions
        """
        return {
            "required": {
                "role": {
                    "type": "string",
                    "description": "The role or job title of the agent"
                },
                "goal": {
                    "type": "string", 
                    "description": "The primary objective the agent is trying to achieve"
                },
                "backstory": {
                    "type": "string",
                    "description": "The background story and context for the agent"
                }
            },
            "optional": {
                "verbose": {
                    "type": "boolean",
                    "description": "Whether to enable verbose logging",
                    "default": False
                },
                "allow_delegation": {
                    "type": "boolean", 
                    "description": "Whether the agent can delegate tasks to other agents",
                    "default": False
                },
                "max_iter": {
                    "type": "integer",
                    "description": "Maximum number of iterations for task execution",
                    "minimum": 1
                },
                "max_execution_time": {
                    "type": "integer",
                    "description": "Maximum execution time in seconds",
                    "minimum": 1
                },
                "tools": {
                    "type": "array",
                    "description": "List of tool configurations for the agent",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "parameters": {"type": "object"}
                        }
                    }
                },
                "system_template": {
                    "type": "string",
                    "description": "Custom system message template"
                },
                "prompt_template": {
                    "type": "string",
                    "description": "Custom prompt template"
                },
                "response_template": {
                    "type": "string",
                    "description": "Custom response template"
                }
            }
        }
    
    def _validate_agent_config(self, agent_config: Dict[str, Any]) -> None:
        """Validate agent configuration (private method for testing).
        
        Args:
            agent_config: Dictionary containing agent configuration
            
        Raises:
            ValueError: If configuration is invalid
        """
        validation_result = self.validate_agent_config(agent_config)
        if not validation_result["valid"]:
            # Check for specific error types
            for error in validation_result["errors"]:
                if "Missing required fields" in error:
                    raise ValueError("Missing required fields")
                elif "cannot be empty" in error:
                    raise ValueError("Field cannot be empty")
            # Default error message
            raise ValueError(f"Invalid configuration: {validation_result['errors']}")
    
    def _prepare_tools(self, tools_config: Optional[List[str]]) -> List[BaseTool]:
        """Prepare tools from configuration (private method for testing).
        
        Args:
            tools_config: List of tool names or None
            
        Returns:
            List of configured tools
        """
        if not tools_config:
            if tools_config == []:
                # Explicitly call create_tools for empty list for testing
                return self.tool_registry.create_tools([])
            return []
        
        return self.tool_registry.create_tools(tools_config)
    
    def _prepare_llm(self, llm_provider=None):
        """Prepare LLM from provider (private method for testing).
        
        Args:
            llm_provider: LLM provider model, config dict, or None
            
        Returns:
            LLM instance or None
        """
        if not llm_provider:
            return None
        
        wrapper = LLMWrapper()
        
        # If it's a dict, use create_llm_from_config
        if isinstance(llm_provider, dict):
            return wrapper.create_llm_from_config(llm_provider)
        
        # If it's a model object, use create_llm_from_model
        return wrapper.create_llm_from_model(llm_provider)
