"""LLM wrapper for managing different LLM providers."""
from typing import List, Optional
from crewai import LLM
from app.models.llm_provider import LLMProvider


class LLMWrapper:
    """Wrapper class for managing LLM providers."""

    def get_available_providers(self) -> List[str]:
        """Get list of available LLM providers."""
        return ["openai", "anthropic", "ollama"]
    
    def create_llm(self, provider: LLMProvider) -> LLM:
        """Create LLM instance from provider configuration."""
        return create_llm_from_provider(provider)
    
    def create_llm_from_model(self, provider: LLMProvider) -> LLM:
        """Create LLM instance from provider model (alias for create_llm)."""
        return self.create_llm(provider)
    
    def create_llm_from_config(self, config: dict) -> LLM:
        """Create LLM instance from configuration dictionary.
        
        Args:
            config: Dictionary containing LLM configuration
            
        Returns:
            Configured CrewAI LLM instance
        """
        # Extract configuration parameters
        provider = config.get("provider", "openai")
        model = config.get("model", "gpt-3.5-turbo")
        temperature = config.get("temperature", 0.7)
        
        model_string = f"{provider}/{model}"
        
        kwargs = {
            "model": model_string,
            "temperature": temperature,
        }
        
        # Add optional parameters
        for key in ["max_tokens", "api_key", "base_url", "api_version"]:
            if key in config and config[key] is not None:
                kwargs[key] = config[key]
        
        return LLM(**kwargs)


def create_llm_from_provider(provider: LLMProvider) -> LLM:
    """Create LLM instance from provider configuration.
    
    Args:
        provider: LLMProvider instance with configuration
        
    Returns:
        Configured CrewAI LLM instance
        
    Raises:
        ValueError: If provider is inactive
    """
    # Check if provider is active
    is_active = getattr(provider, 'is_active', False)
    if not is_active:
        provider_name = getattr(provider, 'name', 'Unknown')
        raise ValueError(f"Provider {provider_name} is not active")
    
    # Convert temperature to float, default to 0.7 if None or empty
    temperature = 0.7
    temp_value = getattr(provider, 'temperature', None)
    if temp_value is not None and temp_value != "":
        try:
            temperature = float(temp_value)
        except (ValueError, TypeError):
            temperature = 0.7
    
    # Build model string in provider/model_name format
    provider_type = getattr(provider, 'provider_type', '')
    model_name = getattr(provider, 'model_name', '')
    model_string = f"{provider_type}/{model_name}"
    
    # Build LLM kwargs
    kwargs = {
        "model": model_string,
        "temperature": temperature,
    }
    
    # Add optional parameters if they exist and are not None/empty
    max_tokens = getattr(provider, 'max_tokens', None)
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    
    api_key = getattr(provider, 'api_key', None)
    if api_key is not None and api_key != "":
        kwargs["api_key"] = api_key
    
    api_base = getattr(provider, 'api_base', None)
    if api_base is not None and api_base != "":
        kwargs["base_url"] = api_base
    
    api_version = getattr(provider, 'api_version', None)
    if api_version is not None and api_version != "":
        kwargs["api_version"] = api_version
    
    # Add any additional config from the config JSON field
    config = getattr(provider, 'config', None)
    if config is not None and isinstance(config, dict):
        # Only add supported parameters
        supported_params = {
            "top_p", "frequency_penalty", "presence_penalty", 
            "stop", "seed", "timeout", "max_retries"
        }
        for key, value in config.items():
            if key in supported_params:
                kwargs[key] = value
    
    return LLM(**kwargs)
