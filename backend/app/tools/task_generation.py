"""Task generation tools for converting text input into CrewAI Task objects."""

import re
from typing import List, Dict, Any, Optional
from crewai import Task

from app.models.agent import Agent as AgentModel


class TaskGenerator:
    """Generates CrewAI tasks from text input using NLP-based parsing."""
    
    def __init__(self):
        """Initialize the task generator."""
        self.task_patterns = [
            # Pattern for explicit task descriptions
            r"(?:create|build|develop|implement|write|design|test|analyze|review|document)\s+(.+?)(?:\.|$|;)",
            # Pattern for action-oriented tasks
            r"(?:need to|should|must|have to)\s+(.+?)(?:\.|$|;)",
            # Pattern for goal-oriented tasks
            r"(?:goal is to|objective is to|aim to|want to)\s+(.+?)(?:\.|$|;)",
            # Pattern for numbered/bulleted lists
            r"(?:\d+\.|\-|\*)\s*(.+?)(?:\n|$)",
        ]
    
    def generate_tasks(self, text_input: str, manager_agent: AgentModel) -> List[Task]:
        """Generate CrewAI tasks from text input.
        
        Args:
            text_input: Text description of work to be done
            manager_agent: Manager agent model with task generation capability
            
        Returns:
            List of CrewAI Task objects
            
        Raises:
            ValueError: If text input is invalid or no tasks can be generated
        """
        if not text_input or not text_input.strip():
            raise ValueError("Text input cannot be empty")
        
        if manager_agent.can_generate_tasks is not True:
            raise ValueError("Agent cannot generate tasks")
        
        # Parse tasks from text
        task_descriptions = self._parse_task_descriptions(text_input)
        
        if not task_descriptions:
            # Fallback: treat entire input as single task
            task_descriptions = [text_input.strip()]
        
        # Convert to CrewAI Task objects
        tasks = []
        for i, description in enumerate(task_descriptions):
            task = self._create_task_from_description(
                description=description,
                task_index=i,
                manager_agent=manager_agent
            )
            tasks.append(task)
        
        return tasks
    
    def _parse_task_descriptions(self, text_input: str) -> List[str]:
        """Parse task descriptions from text input.
        
        Args:
            text_input: Raw text input
            
        Returns:
            List of task description strings
        """
        task_descriptions = []
        text_input = text_input.strip()
        
        # Try each pattern to extract tasks
        for pattern in self.task_patterns:
            matches = re.findall(pattern, text_input, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                cleaned_task = match.strip()
                if cleaned_task and len(cleaned_task) > 5:  # Minimum task length
                    task_descriptions.append(cleaned_task)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_tasks = []
        for task in task_descriptions:
            if task.lower() not in seen:
                seen.add(task.lower())
                unique_tasks.append(task)
        
        return unique_tasks
    
    def _create_task_from_description(self, description: str, task_index: int, 
                                    manager_agent: AgentModel) -> Task:
        """Create a CrewAI Task from a description.
        
        Args:
            description: Task description
            task_index: Index of the task in the sequence
            manager_agent: Manager agent model
            
        Returns:
            CrewAI Task object
        """
        # Generate expected output based on task description
        expected_output = self._generate_expected_output(description)
        
        # Create task without agent assignment (will be assigned later)
        task = Task(
            description=description,
            expected_output=expected_output
        )
        
        return task
    
    def _generate_expected_output(self, description: str) -> str:
        """Generate expected output description based on task description.
        
        Args:
            description: Task description
            
        Returns:
            Expected output description
        """
        # Simple heuristics for generating expected output
        description_lower = description.lower()
        
        if any(word in description_lower for word in ['create', 'build', 'develop', 'implement']):
            return f"A completed implementation of: {description}"
        elif any(word in description_lower for word in ['test', 'verify', 'validate']):
            return f"Test results and validation report for: {description}"
        elif any(word in description_lower for word in ['analyze', 'review', 'evaluate']):
            return f"Analysis report and recommendations for: {description}"
        elif any(word in description_lower for word in ['document', 'write', 'draft']):
            return f"Documentation or written content for: {description}"
        elif any(word in description_lower for word in ['design', 'plan', 'architect']):
            return f"Design specifications and plans for: {description}"
        else:
            return f"Completed work and deliverables for: {description}"
    
    def validate_task_generation_input(self, text_input: str, 
                                     manager_agent: AgentModel) -> Dict[str, Any]:
        """Validate input for task generation.
        
        Args:
            text_input: Text input to validate
            manager_agent: Manager agent model to validate
            
        Returns:
            Dict with validation results containing 'valid' bool and 'errors' list
        """
        errors = []
        
        # Validate text input
        if not text_input or not text_input.strip():
            errors.append("Text input cannot be empty")
        elif len(text_input.strip()) < 10:
            errors.append("Text input too short (minimum 10 characters)")
        elif len(text_input) > 5000:
            errors.append("Text input too long (maximum 5000 characters)")
        
        # Validate manager agent
        if not manager_agent:
            errors.append("Manager agent is required")
        elif manager_agent.can_generate_tasks is not True:
            errors.append("Agent cannot generate tasks")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
    
    def get_task_generation_config(self, manager_agent: AgentModel) -> Dict[str, Any]:
        """Get task generation configuration from manager agent.
        
        Args:
            manager_agent: Manager agent model
            
        Returns:
            Task generation configuration
        """
        config = manager_agent.manager_config if manager_agent.manager_config is not None else {}
        
        return {
            "max_tasks_per_request": config.get("max_tasks_per_request", 10),
            "task_validation_enabled": config.get("task_validation_enabled", True),
            "auto_assign_agents": config.get("auto_assign_agents", True),
            "task_generation_llm": config.get("task_generation_llm", "gpt-4"),
            "min_task_length": config.get("min_task_length", 5),
            "max_task_length": config.get("max_task_length", 500)
        }
    
    def create_task_with_agent(self, description: str, expected_output: str, 
                             agent=None) -> Task:
        """Create a CrewAI Task with optional agent assignment.
        
        Args:
            description: Task description
            expected_output: Expected output description
            agent: Optional CrewAI Agent to assign to the task
            
        Returns:
            CrewAI Task object
        """
        task_kwargs = {
            "description": description,
            "expected_output": expected_output
        }
        
        if agent is not None:
            task_kwargs["agent"] = agent
        
        return Task(**task_kwargs)
    
    def enhance_task_descriptions(self, task_descriptions: List[str], 
                                context: str = "") -> List[str]:
        """Enhance task descriptions with additional context.
        
        Args:
            task_descriptions: List of basic task descriptions
            context: Additional context to enhance descriptions
            
        Returns:
            List of enhanced task descriptions
        """
        enhanced_descriptions = []
        
        for description in task_descriptions:
            enhanced = description
            
            # Add context if provided
            if context and context.strip():
                enhanced = f"{description} (Context: {context.strip()})"
            
            # Ensure proper capitalization and punctuation
            enhanced = enhanced.strip()
            if enhanced and not enhanced[0].isupper():
                enhanced = enhanced[0].upper() + enhanced[1:]
            
            if enhanced and not enhanced.endswith('.'):
                enhanced += '.'
            
            enhanced_descriptions.append(enhanced)
        
        return enhanced_descriptions 