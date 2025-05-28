"""Dynamic crew generator for AI-powered crew composition."""

import json
import time
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
import structlog
from crewai import LLM

from app.core.llm_wrapper import LLMWrapper
from app.core.tool_registry import ToolRegistry
from app.core.crew_wrapper import CrewWrapper
from app.core.agent_wrapper import AgentWrapper
from app.models.generation import (
    DynamicCrewTemplate, GenerationRequest, AgentCapability,
    TaskRequirement, CrewOptimization
)
from app.models.crew import Crew
from app.models.agent import Agent
from app.schemas.generation import (
    GenerationResult, TaskAnalysisResponse, CrewCompositionSuggestion,
    CrewValidationResponse
)

logger = structlog.get_logger()


class DynamicCrewGenerator:
    """AI-powered dynamic crew generation system."""
    
    def __init__(self, db: Session, llm_wrapper: LLMWrapper, tool_registry: ToolRegistry):
        """Initialize the dynamic crew generator.
        
        Args:
            db: Database session
            llm_wrapper: LLM wrapper for AI generation
            tool_registry: Tool registry for available tools
        """
        self.db = db
        self.llm_wrapper = llm_wrapper
        self.tool_registry = tool_registry
        self.logger = logger.bind(component="dynamic_crew_generator")
        
        # Default LLM configuration for generation
        self.default_llm_config = {
            "provider": "openai",
            "model": "gpt-4",
            "temperature": 0.7,
            "max_tokens": 2000
        }
        
        # Generation templates
        self.generation_prompts = {
            "task_analysis": self._get_task_analysis_prompt(),
            "crew_composition": self._get_crew_composition_prompt(),
            "agent_generation": self._get_agent_generation_prompt(),
            "tool_selection": self._get_tool_selection_prompt(),
            "validation": self._get_validation_prompt()
        }
    
    async def generate_response_with_llm(self, prompt: str, llm_config: Optional[Dict[str, Any]] = None) -> str:
        """Generate response using LLM with fallback handling.
        
        Args:
            prompt: Prompt to send to LLM
            llm_config: Optional LLM configuration
            
        Returns:
            Generated response string
        """
        try:
            config = llm_config or self.default_llm_config
            llm = self.llm_wrapper.create_llm_from_config(config)
            
            # Use CrewAI LLM's call method
            if hasattr(llm, 'call'):
                response = llm.call([{"role": "user", "content": prompt}])
            else:
                # Fallback for different LLM interfaces
                response = str(llm)  # Simple fallback
                
            return response if isinstance(response, str) else str(response)
            
        except Exception as e:
            self.logger.warning("LLM generation failed, using fallback", error=str(e))
            return self._get_fallback_response(prompt)
    
    def _get_fallback_response(self, prompt: str) -> str:
        """Generate fallback response when LLM fails."""
        if "task_analysis" in prompt.lower():
            return json.dumps({
                "complexity_score": 5.0,
                "estimated_duration_hours": 8.0,
                "required_skills": ["analysis", "problem_solving"],
                "required_tools": ["basic_tools"],
                "domain_category": "general",
                "risk_factors": ["time_constraints"]
            })
        elif "crew_composition" in prompt.lower():
            return json.dumps({
                "agents": [
                    {
                        "role": "Analyst",
                        "description": "Analyzes requirements and provides insights",
                        "required_skills": ["analysis", "research"],
                        "suggested_tools": ["research_tools"],
                        "priority": 5
                    },
                    {
                        "role": "Executor", 
                        "description": "Executes tasks and delivers results",
                        "required_skills": ["execution", "implementation"],
                        "suggested_tools": ["execution_tools"],
                        "priority": 4
                    }
                ]
            })
        else:
            return "{}"
    
    async def generate_crew(self, objective: str, requirements: Optional[Dict[str, Any]] = None,
                          template_id: Optional[int] = None) -> GenerationResult:
        """Generate a dynamic crew based on objective and requirements.
        
        Args:
            objective: High-level objective for the crew
            requirements: Specific requirements and constraints
            template_id: Optional template to use for generation
            
        Returns:
            GenerationResult with complete crew configuration
            
        Raises:
            ValueError: If objective is invalid or generation fails
        """
        start_time = time.time()
        self.logger.info("Starting dynamic crew generation", objective=objective[:100])
        
        try:
            # Validate inputs
            if not objective or len(objective.strip()) < 10:
                raise ValueError("Objective must be at least 10 characters")
            
            # Load template if specified
            template = None
            if template_id:
                template = self.db.query(DynamicCrewTemplate).filter(
                    DynamicCrewTemplate.id == template_id,
                    DynamicCrewTemplate.is_active == True
                ).first()
                if not template:
                    raise ValueError(f"Template {template_id} not found or inactive")
            
            # Step 1: Analyze task requirements
            task_analysis = await self._analyze_task_requirements(objective, requirements)
            self.logger.info("Task analysis completed", complexity=task_analysis.complexity_score)
            
            # Step 2: Generate crew composition suggestions
            crew_suggestions = await self._generate_crew_composition(task_analysis, template)
            self.logger.info("Crew composition generated", agent_count=len(crew_suggestions))
            
            # Step 3: Generate individual agent configurations
            agent_configs = await self._generate_agent_configurations(crew_suggestions, task_analysis)
            
            # Step 4: Select and assign tools
            tool_assignments = await self._select_and_assign_tools(agent_configs, task_analysis)
            
            # Step 5: Generate manager agent configuration
            manager_config = await self._generate_manager_configuration(
                agent_configs, task_analysis, tool_assignments
            )
            
            # Step 6: Generate task configurations
            task_configs = await self._generate_task_configurations(task_analysis, agent_configs)
            
            # Step 7: Create crew configuration
            crew_config = self._create_crew_configuration(
                objective, agent_configs, manager_config, requirements
            )
            
            # Step 8: Estimate performance
            estimated_performance = await self._estimate_crew_performance(
                crew_config, agent_configs, task_configs, task_analysis
            )
            
            generation_time = time.time() - start_time
            self.logger.info("Crew generation completed", generation_time=generation_time)
            
            return GenerationResult(
                crew_config=crew_config,
                agent_configs=agent_configs,
                task_configs=task_configs,
                manager_config=manager_config,
                tool_assignments=tool_assignments,
                estimated_performance=estimated_performance
            )
            
        except Exception as e:
            self.logger.error("Crew generation failed", error=str(e))
            raise
    
    async def _analyze_task_requirements(self, objective: str, 
                                       requirements: Optional[Dict[str, Any]] = None) -> TaskAnalysisResponse:
        """Analyze task requirements using LLM.
        
        Args:
            objective: Task objective to analyze
            requirements: Additional requirements
            
        Returns:
            TaskAnalysisResponse with detailed analysis
        """
        prompt = self.generation_prompts["task_analysis"].format(
            objective=objective,
            requirements=json.dumps(requirements or {}, indent=2)
        )
        
        response = await self.generate_response_with_llm(prompt)
        
        try:
            analysis_data = json.loads(response)
            
            # Convert to TaskAnalysisResponse
            return TaskAnalysisResponse(
                objective=objective,
                complexity_score=float(analysis_data.get("complexity_score", 5.0)),
                estimated_duration_hours=float(analysis_data.get("estimated_duration_hours", 8.0)),
                required_skills=analysis_data.get("required_skills", []),
                required_tools=analysis_data.get("required_tools", []),
                task_requirements=[],  # Will be populated separately
                domain_category=analysis_data.get("domain_category", "general"),
                risk_factors=analysis_data.get("risk_factors", [])
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.warning("Failed to parse LLM response, using fallback", error=str(e))
            return self._create_fallback_task_analysis(objective)
    
    async def _generate_crew_composition(self, task_analysis: TaskAnalysisResponse,
                                       template: Optional[DynamicCrewTemplate] = None) -> List[CrewCompositionSuggestion]:
        """Generate crew composition suggestions based on task analysis.
        
        Args:
            task_analysis: Task analysis results
            template: Optional template to guide composition
            
        Returns:
            List of crew composition suggestions
        """
        template_config = template.template_config if template else {}
        
        prompt = self.generation_prompts["crew_composition"].format(
            objective=task_analysis.objective,
            complexity_score=task_analysis.complexity_score,
            required_skills=json.dumps(task_analysis.required_skills),
            required_tools=json.dumps(task_analysis.required_tools),
            domain_category=task_analysis.domain_category,
            template_config=json.dumps(template_config, indent=2)
        )
        
        response = await self.generate_response_with_llm(prompt)
        
        try:
            composition_data = json.loads(response)
            suggestions = []
            
            for agent_data in composition_data.get("agents", []):
                suggestion = CrewCompositionSuggestion(
                    agent_role=agent_data.get("role", "Assistant"),
                    agent_description=agent_data.get("description", ""),
                    required_skills=agent_data.get("required_skills", []),
                    suggested_tools=agent_data.get("suggested_tools", []),
                    priority=int(agent_data.get("priority", 3))
                )
                suggestions.append(suggestion)
            
            return suggestions
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.warning("Failed to parse crew composition, using fallback", error=str(e))
            return self._create_fallback_crew_composition(task_analysis)
    
    async def _generate_agent_configurations(self, crew_suggestions: List[CrewCompositionSuggestion],
                                           task_analysis: TaskAnalysisResponse) -> List[Dict[str, Any]]:
        """Generate detailed agent configurations.
        
        Args:
            crew_suggestions: Crew composition suggestions
            task_analysis: Task analysis results
            
        Returns:
            List of agent configuration dictionaries
        """
        agent_configs = []
        
        for suggestion in crew_suggestions:
            prompt = self.generation_prompts["agent_generation"].format(
                agent_role=suggestion.agent_role,
                agent_description=suggestion.agent_description,
                required_skills=json.dumps(suggestion.required_skills),
                objective=task_analysis.objective,
                domain_category=task_analysis.domain_category
            )
            
            response = await self.generate_response_with_llm(prompt)
            
            try:
                agent_data = json.loads(response)
                
                config = {
                    "role": suggestion.agent_role,
                    "goal": agent_data.get("goal", f"Assist with {suggestion.agent_role.lower()} tasks"),
                    "backstory": agent_data.get("backstory", "An experienced professional"),
                    "verbose": False,
                    "allow_delegation": agent_data.get("allow_delegation", False),
                    "max_iter": agent_data.get("max_iter", 10),
                    "memory": True,
                    "skills": suggestion.required_skills,
                    "suggested_tools": suggestion.suggested_tools,
                    "priority": suggestion.priority
                }
                
                agent_configs.append(config)
                
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                self.logger.warning("Failed to parse agent config, using fallback", 
                                  error=str(e), role=suggestion.agent_role)
                agent_configs.append(self._create_fallback_agent_config(suggestion))
        
        return agent_configs
    
    async def _select_and_assign_tools(self, agent_configs: List[Dict[str, Any]],
                                     task_analysis: TaskAnalysisResponse) -> Dict[str, List[str]]:
        """Select and assign tools to agents.
        
        Args:
            agent_configs: Agent configurations
            task_analysis: Task analysis results
            
        Returns:
            Dictionary mapping agent roles to tool lists
        """
        available_tools = self.tool_registry.get_available_tools()
        tool_assignments = {}
        
        for agent_config in agent_configs:
            role = agent_config["role"]
            suggested_tools = agent_config.get("suggested_tools", [])
            
            # Use LLM to select optimal tools
            prompt = self.generation_prompts["tool_selection"].format(
                agent_role=role,
                agent_skills=json.dumps(agent_config.get("skills", [])),
                suggested_tools=json.dumps(suggested_tools),
                available_tools=json.dumps([tool["name"] for tool in available_tools]),
                required_tools=json.dumps(task_analysis.required_tools)
            )
            
            response = await self.generate_response_with_llm(prompt)
            
            try:
                tool_data = json.loads(response)
                selected_tools = tool_data.get("selected_tools", [])
                
                # Validate tools exist
                valid_tools = []
                for tool_name in selected_tools:
                    if any(tool["name"] == tool_name for tool in available_tools):
                        valid_tools.append(tool_name)
                
                tool_assignments[role] = valid_tools
                
            except (json.JSONDecodeError, KeyError, ValueError):
                # Fallback to suggested tools
                tool_assignments[role] = suggested_tools[:3]  # Limit to 3 tools
        
        return tool_assignments
    
    async def _generate_manager_configuration(self, agent_configs: List[Dict[str, Any]],
                                            task_analysis: TaskAnalysisResponse,
                                            tool_assignments: Dict[str, List[str]]) -> Dict[str, Any]:
        """Generate manager agent configuration for coordinating the crew.
        
        Args:
            agent_configs: List of agent configurations
            task_analysis: Task analysis results
            tool_assignments: Tool assignments for agents
            
        Returns:
            Manager agent configuration
        """
        agent_summary = [
            {
                "role": config["role"],
                "skills": config.get("skills", []),
                "tools": tool_assignments.get(config["role"], [])
            }
            for config in agent_configs
        ]
        
        manager_config = {
            "role": "Manager",
            "goal": f"Coordinate the crew to successfully accomplish: {task_analysis.objective}",
            "backstory": (
                "An experienced project manager with expertise in coordinating "
                "diverse teams and ensuring successful task completion. Skilled "
                "in delegation, resource optimization, and quality assurance."
            ),
            "verbose": True,
            "allow_delegation": True,
            "max_iter": 15,
            "memory": True,
            "delegation_tools": ["TaskDecompositionTool", "AgentCoordinationTool", "DelegationValidationTool"],
            "coordination_style": "hierarchical",
            "oversight_level": "moderate",
            "managed_agents": [config["role"] for config in agent_configs]
        }
        
        return manager_config
    
    async def _generate_task_configurations(self, task_analysis: TaskAnalysisResponse,
                                          agent_configs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate task configurations based on analysis and agent capabilities.
        
        Args:
            task_analysis: Task analysis results
            agent_configs: Agent configurations
            
        Returns:
            List of task configuration dictionaries
        """
        # For Phase 7, create a high-level goal-based task for the manager
        # The manager will use delegation tools to decompose into specific tasks
        
        main_task = {
            "description": task_analysis.objective,
            "expected_output": (
                f"Successful completion of the objective: {task_analysis.objective}. "
                "Provide a comprehensive summary of all work completed, results achieved, "
                "and any recommendations for future improvements."
            ),
            "agent": "Manager",  # Assigned to manager for delegation
            "task_type": "goal_based",
            "complexity_score": task_analysis.complexity_score,
            "estimated_duration_hours": task_analysis.estimated_duration_hours
        }
        
        return [main_task]
    
    def _create_crew_configuration(self, objective: str, agent_configs: List[Dict[str, Any]],
                                 manager_config: Dict[str, Any],
                                 requirements: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create crew configuration from individual components.
        
        Args:
            objective: Crew objective
            agent_configs: Agent configurations
            manager_config: Manager configuration
            requirements: Additional requirements
            
        Returns:
            Complete crew configuration
        """
        return {
            "name": f"Dynamic Crew for: {objective[:50]}...",
            "description": f"Dynamically generated crew to accomplish: {objective}",
            "process": "hierarchical",  # Always use hierarchical for dynamic crews
            "verbose": True,
            "memory": True,
            "max_rpm": requirements.get("max_rpm") if requirements else None,
            "max_execution_time": requirements.get("max_execution_time") if requirements else None,
            "manager_agent": manager_config,
            "agents": agent_configs,
            "config": {
                "dynamic_generation": True,
                "generation_timestamp": time.time(),
                "objective": objective,
                "requirements": requirements or {}
            }
        }
    
    async def _estimate_crew_performance(self, crew_config: Dict[str, Any],
                                       agent_configs: List[Dict[str, Any]],
                                       task_configs: List[Dict[str, Any]],
                                       task_analysis: TaskAnalysisResponse) -> Dict[str, float]:
        """Estimate crew performance metrics.
        
        Args:
            crew_config: Crew configuration
            agent_configs: Agent configurations
            task_configs: Task configurations
            task_analysis: Task analysis results
            
        Returns:
            Dictionary of performance estimates
        """
        # Simple heuristic-based performance estimation
        # In a real system, this could use historical data and ML models
        
        base_score = 0.7  # Base performance score
        
        # Adjust based on agent count and task complexity
        agent_count = len(agent_configs)
        complexity = task_analysis.complexity_score
        
        # Optimal agent count heuristic
        optimal_agents = min(max(int(complexity / 2), 1), 5)
        agent_score_adjustment = 1.0 - abs(agent_count - optimal_agents) * 0.1
        
        # Tool coverage adjustment
        required_tools = set(task_analysis.required_tools)
        available_tools = set()
        for config in agent_configs:
            available_tools.update(config.get("suggested_tools", []))
        
        tool_coverage = len(required_tools.intersection(available_tools)) / max(len(required_tools), 1)
        
        # Calculate final scores
        success_rate = min(base_score * agent_score_adjustment * (0.5 + 0.5 * tool_coverage), 1.0)
        efficiency_score = min(0.8 - (complexity - 5) * 0.05, 1.0)
        cost_score = max(0.9 - agent_count * 0.1, 0.3)
        
        return {
            "estimated_success_rate": round(success_rate, 3),
            "efficiency_score": round(max(efficiency_score, 0.1), 3),
            "cost_score": round(cost_score, 3),
            "overall_score": round((success_rate + efficiency_score + cost_score) / 3, 3),
            "complexity_handled": round(min(complexity / 10, 1.0), 3),
            "tool_coverage": round(tool_coverage, 3)
        }
    
    async def validate_crew_configuration(self, crew_config: Dict[str, Any], 
                                        objective: str) -> CrewValidationResponse:
        """Validate a crew configuration for the given objective.
        
        Args:
            crew_config: Crew configuration to validate
            objective: Objective the crew should accomplish
            
        Returns:
            CrewValidationResponse with validation results
        """
        prompt = self.generation_prompts["validation"].format(
            crew_config=json.dumps(crew_config, indent=2),
            objective=objective
        )
        
        response = await self.generate_response_with_llm(prompt)
        
        try:
            validation_data = json.loads(response)
            
            return CrewValidationResponse(
                valid=validation_data.get("valid", False),
                validation_score=float(validation_data.get("validation_score", 5.0)),
                issues=validation_data.get("issues", []),
                warnings=validation_data.get("warnings", []),
                recommendations=validation_data.get("recommendations", []),
                capability_coverage=validation_data.get("capability_coverage", {}),
                estimated_success_rate=float(validation_data.get("estimated_success_rate", 0.5))
            )
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.warning("Failed to parse validation response, using fallback", error=str(e))
            return self._create_fallback_validation_response()
    
    def _create_fallback_task_analysis(self, objective: str) -> TaskAnalysisResponse:
        """Create fallback task analysis when LLM parsing fails."""
        return TaskAnalysisResponse(
            objective=objective,
            complexity_score=5.0,
            estimated_duration_hours=8.0,
            required_skills=["analysis", "communication"],
            required_tools=["basic_tools"],
            task_requirements=[],
            domain_category="general",
            risk_factors=["time_constraints"]
        )
    
    def _create_fallback_crew_composition(self, task_analysis: TaskAnalysisResponse) -> List[CrewCompositionSuggestion]:
        """Create fallback crew composition when LLM parsing fails."""
        return [
            CrewCompositionSuggestion(
                agent_role="Analyst",
                agent_description="Analyzes requirements and provides insights",
                required_skills=task_analysis.required_skills[:3],
                suggested_tools=task_analysis.required_tools[:2],
                priority=5
            ),
            CrewCompositionSuggestion(
                agent_role="Executor",
                agent_description="Executes tasks and delivers results",
                required_skills=["execution", "problem_solving"],
                suggested_tools=task_analysis.required_tools,
                priority=4
            )
        ]
    
    def _create_fallback_agent_config(self, suggestion: CrewCompositionSuggestion) -> Dict[str, Any]:
        """Create fallback agent configuration when LLM parsing fails."""
        return {
            "role": suggestion.agent_role,
            "goal": f"Assist with {suggestion.agent_role.lower()} tasks",
            "backstory": f"An experienced {suggestion.agent_role.lower()}",
            "verbose": False,
            "allow_delegation": False,
            "max_iter": 10,
            "memory": True,
            "skills": suggestion.required_skills,
            "suggested_tools": suggestion.suggested_tools,
            "priority": suggestion.priority
        }
    
    def _create_fallback_validation_response(self) -> CrewValidationResponse:
        """Create fallback validation response when LLM parsing fails."""
        return CrewValidationResponse(
            valid=True,
            validation_score=6.0,
            issues=[],
            warnings=["Unable to perform detailed validation"],
            recommendations=["Manual review recommended"],
            capability_coverage={"general": 0.7},
            estimated_success_rate=0.7
        )
    
    def _get_task_analysis_prompt(self) -> str:
        """Get the LLM prompt for task analysis."""
        return """
Analyze the following task objective and requirements. Provide a detailed analysis in JSON format.

OBJECTIVE: {objective}
REQUIREMENTS: {requirements}

Please provide your analysis in the following JSON format:
{{
    "complexity_score": <float 1-10>,
    "estimated_duration_hours": <float>,
    "required_skills": [<list of required skills>],
    "required_tools": [<list of required tools>],
    "domain_category": "<domain category>",
    "risk_factors": [<list of potential risks>]
}}

Consider:
- Task complexity and scope
- Skills needed to complete the task
- Tools that would be helpful
- Time estimation based on complexity
- Potential challenges or risks

Respond only with valid JSON.
"""
    
    def _get_crew_composition_prompt(self) -> str:
        """Get the LLM prompt for crew composition."""
        return """
Design an optimal crew composition for the following task. Consider the complexity, required skills, and available tools.

OBJECTIVE: {objective}
COMPLEXITY SCORE: {complexity_score}
REQUIRED SKILLS: {required_skills}
REQUIRED TOOLS: {required_tools}
DOMAIN: {domain_category}
TEMPLATE CONFIG: {template_config}

Create a crew with 2-5 agents. Provide your recommendations in JSON format:
{{
    "agents": [
        {{
            "role": "<agent role>",
            "description": "<agent description>",
            "required_skills": [<list of skills>],
            "suggested_tools": [<list of tools>],
            "priority": <int 1-5>
        }}
    ]
}}

Guidelines:
- Choose complementary roles that cover all required skills
- Avoid unnecessary duplication
- Consider task complexity for agent count
- Assign tools relevant to each agent's role
- Higher priority for critical roles

Respond only with valid JSON.
"""
    
    def _get_agent_generation_prompt(self) -> str:
        """Get the LLM prompt for agent generation."""
        return """
Generate a detailed configuration for an agent with the specified role and skills.

AGENT ROLE: {agent_role}
DESCRIPTION: {agent_description}
REQUIRED SKILLS: {required_skills}
OBJECTIVE CONTEXT: {objective}
DOMAIN: {domain_category}

Create a detailed agent configuration in JSON format:
{{
    "goal": "<specific goal for this agent>",
    "backstory": "<professional backstory>",
    "allow_delegation": <boolean>,
    "max_iter": <integer 5-15>
}}

Guidelines:
- Goal should be specific and actionable
- Backstory should reflect expertise in required skills
- Consider if agent should be able to delegate
- Set max_iter based on role complexity

Respond only with valid JSON.
"""
    
    def _get_tool_selection_prompt(self) -> str:
        """Get the LLM prompt for tool selection."""
        return """
Select the most appropriate tools for an agent based on their role and the task requirements.

AGENT ROLE: {agent_role}
AGENT SKILLS: {agent_skills}
SUGGESTED TOOLS: {suggested_tools}
AVAILABLE TOOLS: {available_tools}
REQUIRED TOOLS: {required_tools}

Select tools and provide response in JSON format:
{{
    "selected_tools": [<list of selected tool names>]
}}

Guidelines:
- Select 1-4 tools maximum per agent
- Prioritize required tools for the task
- Choose tools that match agent skills
- Avoid tool conflicts or redundancy

Respond only with valid JSON containing tool names from the available tools list.
"""
    
    def _get_validation_prompt(self) -> str:
        """Get the LLM prompt for crew validation."""
        return """
Validate the crew configuration for the given objective and identify any issues.

CREW CONFIG: {crew_config}
OBJECTIVE: {objective}

Analyze the crew and provide validation results in JSON format:
{{
    "valid": <boolean>,
    "validation_score": <float 1-10>,
    "issues": [<list of critical issues>],
    "warnings": [<list of warnings>],
    "recommendations": [<list of recommendations>],
    "capability_coverage": {{
        "<skill>": <coverage_percentage>
    }},
    "estimated_success_rate": <float 0-1>
}}

Check for:
- Skill coverage for objective
- Tool availability and appropriateness  
- Agent role compatibility
- Resource allocation
- Potential bottlenecks

Respond only with valid JSON.
""" 