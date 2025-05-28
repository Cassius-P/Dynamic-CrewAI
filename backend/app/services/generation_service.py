"""Service layer for dynamic crew generation functionality."""

import time
from datetime import datetime
from typing import Optional, List, Dict, Any, cast
from sqlalchemy.orm import Session
from sqlalchemy import desc, update
import structlog

from app.core.dynamic_crew_generator import DynamicCrewGenerator
from app.core.llm_wrapper import LLMWrapper
from app.core.tool_registry import ToolRegistry
from app.core.crew_wrapper import CrewWrapper
from app.core.agent_wrapper import AgentWrapper
from app.models.generation import (
    DynamicCrewTemplate, GenerationRequest, CrewOptimization,
    AgentCapability, TaskRequirement, GenerationMetrics
)
from app.models.crew import Crew
from app.models.agent import Agent
from app.schemas.generation import (
    GenerationRequestCreate, GenerationRequestResponse, GenerationResult,
    TaskAnalysisRequest, TaskAnalysisResponse, CrewValidationRequest, CrewValidationResponse,
    CrewOptimizationRequest, CrewOptimizationResponse, DynamicCrewTemplateCreate,
    DynamicCrewTemplateResponse, DynamicCrewTemplateUpdate, BulkGenerationRequest,
    BulkGenerationResponse
)

logger = structlog.get_logger()


class GenerationService:
    """Service for managing dynamic crew generation operations."""
    
    def __init__(self, db: Session):
        """Initialize the generation service.
        
        Args:
            db: Database session
        """
        self.db = db
        self.logger = logger.bind(component="generation_service")
        
        # Initialize dependencies
        self.llm_wrapper = LLMWrapper()
        self.tool_registry = ToolRegistry()
        self.generator = DynamicCrewGenerator(db, self.llm_wrapper, self.tool_registry)
        
        # Initialize crew wrapper with agent wrapper
        agent_wrapper = AgentWrapper()
        self.crew_wrapper = CrewWrapper(agent_wrapper)
    
    async def create_generation_request(self, request: GenerationRequestCreate) -> GenerationRequestResponse:
        """Create a new crew generation request.
        
        Args:
            request: Generation request data
            
        Returns:
            GenerationRequestResponse with created request
            
        Raises:
            ValueError: If request validation fails
        """
        self.logger.info("Creating generation request", objective=request.objective[:100])
        
        try:
            # Validate template if specified
            template = None
            if request.template_id:
                template = self.db.query(DynamicCrewTemplate).filter(
                    DynamicCrewTemplate.id == request.template_id,
                    DynamicCrewTemplate.is_active == True
                ).first()
                if not template:
                    raise ValueError(f"Template {request.template_id} not found or inactive")
            
            # Create generation request record
            generation_request = GenerationRequest(
                objective=request.objective,
                requirements=request.requirements,
                template_id=request.template_id,
                llm_provider=request.llm_provider,
                generation_status="pending"
            )
            
            self.db.add(generation_request)
            self.db.commit()
            self.db.refresh(generation_request)
            
            # Get the ID as an integer
            request_id = cast(int, generation_request.id)
            
            # Generate crew asynchronously
            start_time = time.time()
            
            # Update status to generating
            self.db.execute(
                update(GenerationRequest)
                .where(GenerationRequest.id == request_id)
                .values(generation_status="generating")
            )
            self.db.commit()
            
            try:
                # Generate crew configuration
                generation_result = await self.generator.generate_crew(
                    objective=request.objective,
                    requirements=request.requirements,
                    template_id=request.template_id
                )
                
                # Create crew from generated configuration
                crew_id = None
                if generation_result.crew_config:
                    crew_id = await self._create_crew_from_config(
                        generation_result, request_id
                    )
                
                # Update generation request with results
                generation_time = time.time() - start_time
                update_data = {
                    "generation_status": "completed",
                    "generated_crew_id": crew_id,
                    "generation_result": generation_result.model_dump(),
                    "generation_time_seconds": generation_time,
                    "completed_at": datetime.utcnow()
                }
                
                # Apply optimization if enabled
                if request.optimization_enabled and crew_id:
                    await self._apply_crew_optimization(request_id, crew_id)
                    update_data["optimization_applied"] = True
                
                # Update the generation request
                self.db.execute(
                    update(GenerationRequest)
                    .where(GenerationRequest.id == request_id)
                    .values(**update_data)
                )
                self.db.commit()
                
                # Record generation metrics
                await self._record_generation_metrics(request_id, generation_result, generation_time)
                
                # Update template success rate if used
                if template:
                    template_id = cast(int, template.id)
                    await self._update_template_usage(template_id, True)
                
                self.logger.info("Generation request completed", 
                               request_id=request_id, 
                               crew_id=crew_id,
                               generation_time=generation_time)
                
            except Exception as e:
                # Update status to failed
                self.db.execute(
                    update(GenerationRequest)
                    .where(GenerationRequest.id == request_id)
                    .values(
                        generation_status="failed",
                        completed_at=datetime.utcnow()
                    )
                )
                self.db.commit()
                
                if template:
                    template_id = cast(int, template.id)
                    await self._update_template_usage(template_id, False)
                
                self.logger.error("Generation request failed", 
                                request_id=request_id, 
                                error=str(e))
                raise
            
            # Refresh to get updated data
            self.db.refresh(generation_request)
            return self._to_generation_response(generation_request)
            
        except Exception as e:
            self.logger.error("Failed to create generation request", error=str(e))
            raise
    
    async def get_generation_request(self, request_id: int) -> Optional[GenerationRequestResponse]:
        """Get generation request by ID.
        
        Args:
            request_id: ID of the generation request
            
        Returns:
            GenerationRequestResponse or None if not found
        """
        generation_request = self.db.query(GenerationRequest).filter(
            GenerationRequest.id == request_id
        ).first()
        
        if not generation_request:
            return None
        
        return self._to_generation_response(generation_request)
    
    async def list_generation_requests(self, skip: int = 0, limit: int = 100) -> List[GenerationRequestResponse]:
        """List generation requests with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of GenerationRequestResponse
        """
        requests = self.db.query(GenerationRequest)\
            .order_by(desc(GenerationRequest.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()
        
        return [self._to_generation_response(req) for req in requests]
    
    async def analyze_task(self, request: TaskAnalysisRequest) -> TaskAnalysisResponse:
        """Analyze task requirements without generating a crew.
        
        Args:
            request: Task analysis request
            
        Returns:
            TaskAnalysisResponse with analysis results
        """
        requirements = {"context": request.context, "domain": request.domain} if request.context or request.domain else None
        
        return await self.generator._analyze_task_requirements(
            objective=request.objective,
            requirements=requirements
        )
    
    async def validate_crew_configuration(self, request: CrewValidationRequest) -> CrewValidationResponse:
        """Validate a crew configuration.
        
        Args:
            request: Crew validation request
            
        Returns:
            CrewValidationResponse with validation results
        """
        return await self.generator.validate_crew_configuration(
            crew_config=request.crew_config,
            objective=request.objective
        )
    
    async def optimize_crew(self, request: CrewOptimizationRequest) -> CrewOptimizationResponse:
        """Optimize an existing crew configuration.
        
        Args:
            request: Crew optimization request
            
        Returns:
            CrewOptimizationResponse with optimization results
        """
        # Get existing crew
        crew = self.db.query(Crew).filter(Crew.id == request.crew_id).first()
        if not crew:
            raise ValueError(f"Crew {request.crew_id} not found")
        
        # Get crew config safely
        crew_config = cast(Optional[Dict[str, Any]], crew.config)
        
        # Create optimization record
        optimization = CrewOptimization(
            crew_id=request.crew_id,
            optimization_type=request.optimization_type,
            original_config={"crew": crew_config or {}},
            applied=False
        )
        
        self.db.add(optimization)
        self.db.commit()
        self.db.refresh(optimization)
        
        # Get optimization ID as integer
        optimization_id = cast(int, optimization.id)
        
        # Apply optimization logic based on type
        optimized_config = await self._apply_optimization_logic(
            crew, request.optimization_type, request.target_metrics
        )
        
        # Get original config properly
        original_config = cast(Dict[str, Any], optimization.original_config) or {}
        
        # Calculate optimization score
        optimization_score = await self._calculate_optimization_score(
            original_config=original_config,
            optimized_config=optimized_config,
            optimization_type=request.optimization_type
        )
        
        # Calculate improvements
        improvements = await self._calculate_improvements(original_config, optimized_config)
        
        # Update optimization record using update statement
        self.db.execute(
            update(CrewOptimization)
            .where(CrewOptimization.id == optimization_id)
            .values(
                optimized_config=optimized_config,
                optimization_score=optimization_score,
                optimization_metrics={
                    "type": request.optimization_type,
                    "improvements": improvements
                }
            )
        )
        self.db.commit()
        
        # Refresh to get updated data
        self.db.refresh(optimization)
        
        return self._to_optimization_response(optimization)
    
    async def bulk_generate(self, request: BulkGenerationRequest) -> BulkGenerationResponse:
        """Generate multiple crews from a list of objectives.
        
        Args:
            request: Bulk generation request
            
        Returns:
            BulkGenerationResponse with all generation results
        """
        generation_requests = []
        successful_generations = 0
        failed_generations = 0
        errors = []
        
        for objective in request.objectives:
            try:
                gen_request = GenerationRequestCreate(
                    objective=objective,
                    requirements=request.shared_requirements,
                    template_id=request.template_id,
                    llm_provider=request.llm_provider
                )
                
                result = await self.create_generation_request(gen_request)
                generation_requests.append(result)
                
                if result.generation_status == "completed":
                    successful_generations += 1
                else:
                    failed_generations += 1
                    
            except Exception as e:
                failed_generations += 1
                errors.append(f"Failed to generate crew for '{objective[:50]}...': {str(e)}")
        
        return BulkGenerationResponse(
            total_requests=len(request.objectives),
            successful_generations=successful_generations,
            failed_generations=failed_generations,
            generation_requests=generation_requests,
            errors=errors
        )
    
    # Template management methods
    async def create_template(self, template_data: DynamicCrewTemplateCreate) -> DynamicCrewTemplateResponse:
        """Create a new dynamic crew template.
        
        Args:
            template_data: Template creation data
            
        Returns:
            DynamicCrewTemplateResponse with created template
        """
        template = DynamicCrewTemplate(
            name=template_data.name,
            description=template_data.description,
            template_type=template_data.template_type,
            template_config=template_data.template_config
        )
        
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        
        return self._to_template_response(template)
    
    async def get_template(self, template_id: int) -> Optional[DynamicCrewTemplateResponse]:
        """Get template by ID.
        
        Args:
            template_id: ID of the template
            
        Returns:
            DynamicCrewTemplateResponse or None if not found
        """
        template = self.db.query(DynamicCrewTemplate).filter(
            DynamicCrewTemplate.id == template_id
        ).first()
        
        if not template:
            return None
        
        return self._to_template_response(template)
    
    async def list_templates(self, skip: int = 0, limit: int = 100) -> List[DynamicCrewTemplateResponse]:
        """List templates with pagination.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of DynamicCrewTemplateResponse
        """
        templates = self.db.query(DynamicCrewTemplate)\
            .filter(DynamicCrewTemplate.is_active == True)\
            .order_by(desc(DynamicCrewTemplate.created_at))\
            .offset(skip)\
            .limit(limit)\
            .all()
        
        return [self._to_template_response(template) for template in templates]
    
    async def update_template(self, template_id: int, 
                            update_data: DynamicCrewTemplateUpdate) -> Optional[DynamicCrewTemplateResponse]:
        """Update an existing template.
        
        Args:
            template_id: Template ID to update
            update_data: Update data
            
        Returns:
            Updated DynamicCrewTemplateResponse or None if not found
        """
        template = self.db.query(DynamicCrewTemplate).filter(
            DynamicCrewTemplate.id == template_id
        ).first()
        
        if not template:
            return None
        
        # Prepare update values
        update_values = {}
        if update_data.name is not None:
            update_values["name"] = update_data.name
        if update_data.description is not None:
            update_values["description"] = update_data.description
        if update_data.template_type is not None:
            update_values["template_type"] = update_data.template_type
        if update_data.template_config is not None:
            update_values["template_config"] = update_data.template_config
        if update_data.is_active is not None:
            update_values["is_active"] = update_data.is_active
        
        # Add updated timestamp
        update_values["updated_at"] = datetime.utcnow()
        
        # Update using SQLAlchemy update statement
        self.db.execute(
            update(DynamicCrewTemplate)
            .where(DynamicCrewTemplate.id == template_id)
            .values(**update_values)
        )
        self.db.commit()
        
        # Refresh to get updated data
        self.db.refresh(template)
        return self._to_template_response(template)
    
    # Private helper methods
    async def _create_crew_from_config(self, generation_result: GenerationResult, 
                                     generation_request_id: int) -> int:
        """Create a crew from generation result configuration.
        
        Args:
            generation_result: Generation result with crew configuration
            generation_request_id: ID of the generation request
            
        Returns:
            Created crew ID
        """
        # Create crew using crew wrapper
        crew_config = generation_result.crew_config
        crew_name = crew_config.get("name", f"Generated Crew {generation_request_id}")
        crew_description = crew_config.get("description", "Dynamically generated crew")
        
        # Create crew record
        crew = Crew(
            name=crew_name,
            description=crew_description,
            config=crew_config
        )
        
        self.db.add(crew)
        self.db.commit()
        self.db.refresh(crew)
        
        crew_id = cast(int, crew.id)
        
        # Create agents from configuration
        for agent_config in generation_result.agent_configs:
            agent = Agent(
                role=agent_config.get("role", "Assistant"),
                goal=agent_config.get("goal", "Complete assigned tasks"),
                backstory=agent_config.get("backstory", "AI assistant"),
                crew_id=crew_id
            )
            self.db.add(agent)
        
        self.db.commit()
        return crew_id
    
    async def _apply_crew_optimization(self, request_id: int, crew_id: int):
        """Apply optimization to a generated crew.
        
        Args:
            request_id: Generation request ID
            crew_id: Crew ID to optimize
        """
        optimization_request = CrewOptimizationRequest(
            crew_id=crew_id,
            optimization_type="performance",
            target_metrics={"efficiency": 0.8, "cost": 0.7}
        )
        
        await self.optimize_crew(optimization_request)
    
    async def _record_generation_metrics(self, request_id: int, generation_result: GenerationResult, 
                                       generation_time: float):
        """Record metrics for a generation request.
        
        Args:
            request_id: Generation request ID
            generation_result: Generation results
            generation_time: Time taken for generation
        """
        metrics = [
            GenerationMetrics(
                generation_request_id=request_id,
                metric_name="generation_time",
                metric_value=generation_time,
                metric_unit="seconds",
                metric_category="performance"
            ),
            GenerationMetrics(
                generation_request_id=request_id,
                metric_name="agent_count",
                metric_value=len(generation_result.agent_configs),
                metric_unit="count",
                metric_category="composition"
            ),
            GenerationMetrics(
                generation_request_id=request_id,
                metric_name="estimated_success_rate",
                metric_value=generation_result.estimated_performance.get("estimated_success_rate", 0.0),
                metric_unit="percentage",
                metric_category="quality"
            )
        ]
        
        for metric in metrics:
            self.db.add(metric)
        
        self.db.commit()
    
    async def _update_template_usage(self, template_id: int, success: bool):
        """Update template usage statistics.
        
        Args:
            template_id: Template ID
            success: Whether the generation was successful
        """
        template = self.db.query(DynamicCrewTemplate).filter(
            DynamicCrewTemplate.id == template_id
        ).first()
        
        if template:
            # Get current values
            current_usage_count = cast(int, template.usage_count) or 0
            current_success_rate = cast(float, template.success_rate) or 0.0
            
            # Calculate new values
            new_usage_count = current_usage_count + 1
            alpha = 0.1  # Learning rate
            if success:
                new_success_rate = (1 - alpha) * current_success_rate + alpha * 1.0
            else:
                new_success_rate = (1 - alpha) * current_success_rate + alpha * 0.0
            
            # Update using SQLAlchemy update statement
            self.db.execute(
                update(DynamicCrewTemplate)
                .where(DynamicCrewTemplate.id == template_id)
                .values(
                    usage_count=new_usage_count,
                    success_rate=new_success_rate
                )
            )
            self.db.commit()
    
    async def _apply_optimization_logic(self, crew: Crew, optimization_type: str, 
                                      target_metrics: Optional[Dict[str, float]]) -> Dict[str, Any]:
        """Apply optimization logic to a crew configuration.
        
        Args:
            crew: Crew to optimize
            optimization_type: Type of optimization to apply
            target_metrics: Target metrics for optimization
            
        Returns:
            Optimized crew configuration
        """
        # Simple optimization logic - in practice this would be more sophisticated
        original_config = cast(Dict[str, Any], crew.config) or {}
        optimized_config = original_config.copy()
        
        if optimization_type == "performance":
            optimized_config["max_rpm"] = original_config.get("max_rpm", 10) + 5
            optimized_config["memory"] = True
        elif optimization_type == "cost":
            optimized_config["max_rpm"] = max(original_config.get("max_rpm", 10) - 2, 1)
        elif optimization_type == "speed":
            optimized_config["max_execution_time"] = original_config.get("max_execution_time", 3600) * 0.8
        
        return optimized_config
    
    async def _calculate_optimization_score(self, original_config: Dict[str, Any], 
                                          optimized_config: Dict[str, Any], 
                                          optimization_type: str) -> float:
        """Calculate optimization improvement score.
        
        Args:
            original_config: Original configuration
            optimized_config: Optimized configuration
            optimization_type: Type of optimization
            
        Returns:
            Optimization score (0.0-10.0)
        """
        # Simple scoring logic - could be enhanced with actual performance metrics
        base_score = 5.0
        
        if optimization_type == "performance":
            if optimized_config.get("max_rpm", 0) > original_config.get("max_rpm", 0):
                base_score += 2.0
        elif optimization_type == "cost":
            if optimized_config.get("max_rpm", 0) < original_config.get("max_rpm", 0):
                base_score += 1.5
        elif optimization_type == "speed":
            if optimized_config.get("max_execution_time", 0) < original_config.get("max_execution_time", 0):
                base_score += 1.8
        
        return min(base_score, 10.0)
    
    async def _calculate_improvements(self, original_config: Dict[str, Any], 
                                    optimized_config: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate improvement metrics between configurations.
        
        Args:
            original_config: Original configuration
            optimized_config: Optimized configuration
            
        Returns:
            Dictionary of improvement metrics
        """
        improvements = {}
        
        # Compare configurations and calculate improvements
        for key in optimized_config:
            if key in original_config:
                original_val = original_config[key]
                optimized_val = optimized_config[key]
                
                if isinstance(original_val, (int, float)) and isinstance(optimized_val, (int, float)):
                    if original_val != 0:
                        improvement_pct = ((optimized_val - original_val) / original_val) * 100
                        improvements[f"{key}_improvement_percent"] = improvement_pct
        
        return improvements
    
    def _to_generation_response(self, generation_request: GenerationRequest) -> GenerationRequestResponse:
        """Convert GenerationRequest model to response schema.
        
        Args:
            generation_request: GenerationRequest model instance
            
        Returns:
            GenerationRequestResponse
        """
        generation_result = None
        generation_result_data = cast(Optional[Dict[str, Any]], generation_request.generation_result)
        if generation_result_data:
            generation_result = GenerationResult(**generation_result_data)
        
        return GenerationRequestResponse(
            id=cast(int, generation_request.id),
            objective=cast(str, generation_request.objective),
            requirements=cast(Optional[Dict[str, Any]], generation_request.requirements),
            generated_crew_id=cast(Optional[int], generation_request.generated_crew_id),
            template_id=cast(Optional[int], generation_request.template_id),
            llm_provider=cast(str, generation_request.llm_provider),
            generation_status=cast(str, generation_request.generation_status),
            generation_result=generation_result,
            validation_result=cast(Optional[Dict[str, Any]], generation_request.validation_result),
            optimization_applied=cast(bool, generation_request.optimization_applied) or False,
            generation_time_seconds=cast(Optional[float], generation_request.generation_time_seconds),
            created_at=cast(datetime, generation_request.created_at),
            completed_at=cast(Optional[datetime], generation_request.completed_at)
        )
    
    def _to_template_response(self, template: DynamicCrewTemplate) -> DynamicCrewTemplateResponse:
        """Convert DynamicCrewTemplate model to response schema.
        
        Args:
            template: DynamicCrewTemplate model instance
            
        Returns:
            DynamicCrewTemplateResponse schema
        """
        return DynamicCrewTemplateResponse(
            id=cast(int, template.id),
            name=cast(str, template.name),
            description=cast(str, template.description) if template.description is not None else None,
            template_type=cast(str, template.template_type),
            template_config=cast(Dict[str, Any], template.template_config) if template.template_config is not None else {},
            success_rate=cast(float, template.success_rate) if template.success_rate is not None else 0.0,
            usage_count=cast(int, template.usage_count) if template.usage_count is not None else 0,
            is_active=cast(bool, template.is_active) if template.is_active is not None else True,
            created_at=cast(datetime, template.created_at),
            updated_at=cast(datetime, template.updated_at) if template.updated_at is not None else None
        )

    def _to_optimization_response(self, optimization: CrewOptimization) -> CrewOptimizationResponse:
        """Convert CrewOptimization model to response schema.
        
        Args:
            optimization: CrewOptimization model instance
            
        Returns:
            CrewOptimizationResponse schema
        """
        return CrewOptimizationResponse(
            id=cast(int, optimization.id),
            crew_id=cast(int, optimization.crew_id),
            optimization_type=cast(str, optimization.optimization_type),
            optimization_score=cast(float, optimization.optimization_score),
            optimization_metrics=cast(Dict[str, Any], optimization.optimization_metrics) if optimization.optimization_metrics is not None else {},
            applied=cast(bool, optimization.applied),
            created_at=cast(datetime, optimization.created_at),
            applied_at=cast(datetime, optimization.applied_at) if optimization.applied_at is not None else None
        ) 