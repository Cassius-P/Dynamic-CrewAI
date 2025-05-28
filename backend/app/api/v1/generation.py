"""API endpoints for dynamic crew generation."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.generation_service import GenerationService
from app.schemas.generation import (
    GenerationRequestCreate, GenerationRequestResponse, TaskAnalysisRequest,
    TaskAnalysisResponse, CrewValidationRequest, CrewValidationResponse,
    CrewOptimizationRequest, CrewOptimizationResponse, DynamicCrewTemplateCreate,
    DynamicCrewTemplateResponse, DynamicCrewTemplateUpdate, BulkGenerationRequest,
    BulkGenerationResponse
)

router = APIRouter()


def get_generation_service(db: Session = Depends(get_db)) -> GenerationService:
    """Get generation service instance."""
    return GenerationService(db)


@router.post("/generate", response_model=GenerationRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_generation_request(
    request: GenerationRequestCreate,
    background_tasks: BackgroundTasks,
    service: GenerationService = Depends(get_generation_service)
) -> GenerationRequestResponse:
    """Create a new dynamic crew generation request.
    
    This endpoint creates a crew generation request and processes it asynchronously.
    The crew will be generated based on the provided objective and requirements.
    
    Args:
        request: Generation request data
        background_tasks: FastAPI background tasks
        service: Generation service instance
        
    Returns:
        GenerationRequestResponse with request details and status
        
    Raises:
        HTTPException: If request validation fails or template not found
    """
    try:
        return await service.create_generation_request(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create generation request: {str(e)}"
        )


@router.get("/requests/{request_id}", response_model=GenerationRequestResponse)
async def get_generation_request(
    request_id: int,
    service: GenerationService = Depends(get_generation_service)
) -> GenerationRequestResponse:
    """Get generation request by ID.
    
    Args:
        request_id: ID of the generation request
        service: Generation service instance
        
    Returns:
        GenerationRequestResponse with request details
        
    Raises:
        HTTPException: If request not found
    """
    request = await service.get_generation_request(request_id)
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Generation request {request_id} not found"
        )
    return request


@router.get("/requests", response_model=List[GenerationRequestResponse])
async def list_generation_requests(
    skip: int = 0,
    limit: int = 100,
    service: GenerationService = Depends(get_generation_service)
) -> List[GenerationRequestResponse]:
    """List generation requests with pagination.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        service: Generation service instance
        
    Returns:
        List of GenerationRequestResponse
    """
    if limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit cannot exceed 1000"
        )
    
    return await service.list_generation_requests(skip=skip, limit=limit)


@router.post("/analyze", response_model=TaskAnalysisResponse)
async def analyze_task(
    request: TaskAnalysisRequest,
    service: GenerationService = Depends(get_generation_service)
) -> TaskAnalysisResponse:
    """Analyze task requirements without generating a crew.
    
    This endpoint analyzes the provided objective and context to determine
    complexity, required skills, tools, and other task characteristics.
    
    Args:
        request: Task analysis request
        service: Generation service instance
        
    Returns:
        TaskAnalysisResponse with analysis results
    """
    try:
        return await service.analyze_task(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze task: {str(e)}"
        )


@router.post("/validate", response_model=CrewValidationResponse)
async def validate_crew_configuration(
    request: CrewValidationRequest,
    service: GenerationService = Depends(get_generation_service)
) -> CrewValidationResponse:
    """Validate a crew configuration.
    
    This endpoint validates whether a crew configuration is suitable
    for accomplishing the specified objective.
    
    Args:
        request: Crew validation request
        service: Generation service instance
        
    Returns:
        CrewValidationResponse with validation results
    """
    try:
        return await service.validate_crew_configuration(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate crew configuration: {str(e)}"
        )


@router.post("/optimize", response_model=CrewOptimizationResponse)
async def optimize_crew(
    request: CrewOptimizationRequest,
    service: GenerationService = Depends(get_generation_service)
) -> CrewOptimizationResponse:
    """Optimize an existing crew configuration.
    
    This endpoint applies optimization techniques to improve crew performance,
    cost efficiency, or execution speed based on the specified optimization type.
    
    Args:
        request: Crew optimization request
        service: Generation service instance
        
    Returns:
        CrewOptimizationResponse with optimization results
        
    Raises:
        HTTPException: If crew not found or optimization fails
    """
    try:
        return await service.optimize_crew(request)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to optimize crew: {str(e)}"
        )


@router.post("/bulk-generate", response_model=BulkGenerationResponse)
async def bulk_generate_crews(
    request: BulkGenerationRequest,
    service: GenerationService = Depends(get_generation_service)
) -> BulkGenerationResponse:
    """Generate multiple crews in bulk.
    
    This endpoint allows generating multiple crews at once with shared
    requirements and configuration.
    
    Args:
        request: Bulk generation request
        service: Generation service instance
        
    Returns:
        BulkGenerationResponse with results for all generations
    """
    if len(request.objectives) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot generate more than 10 crews at once"
        )
    
    try:
        return await service.bulk_generate(request)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to bulk generate crews: {str(e)}"
        )


# Template management endpoints
@router.post("/templates", response_model=DynamicCrewTemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    template_data: DynamicCrewTemplateCreate,
    service: GenerationService = Depends(get_generation_service)
) -> DynamicCrewTemplateResponse:
    """Create a new dynamic crew template.
    
    Templates allow reusing successful crew configurations for similar tasks.
    
    Args:
        template_data: Template creation data
        service: Generation service instance
        
    Returns:
        DynamicCrewTemplateResponse with created template
    """
    try:
        return await service.create_template(template_data)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create template: {str(e)}"
        )


@router.get("/templates/{template_id}", response_model=DynamicCrewTemplateResponse)
async def get_template(
    template_id: int,
    service: GenerationService = Depends(get_generation_service)
) -> DynamicCrewTemplateResponse:
    """Get template by ID.
    
    Args:
        template_id: ID of the template
        service: Generation service instance
        
    Returns:
        DynamicCrewTemplateResponse with template details
        
    Raises:
        HTTPException: If template not found
    """
    template = await service.get_template(template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found"
        )
    return template


@router.get("/templates", response_model=List[DynamicCrewTemplateResponse])
async def list_templates(
    skip: int = 0,
    limit: int = 100,
    service: GenerationService = Depends(get_generation_service)
) -> List[DynamicCrewTemplateResponse]:
    """List templates with pagination.
    
    Args:
        skip: Number of records to skip
        limit: Maximum number of records to return
        service: Generation service instance
        
    Returns:
        List of DynamicCrewTemplateResponse
    """
    if limit > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit cannot exceed 1000"
        )
    
    return await service.list_templates(skip=skip, limit=limit)


@router.put("/templates/{template_id}", response_model=DynamicCrewTemplateResponse)
async def update_template(
    template_id: int,
    update_data: DynamicCrewTemplateUpdate,
    service: GenerationService = Depends(get_generation_service)
) -> DynamicCrewTemplateResponse:
    """Update an existing template.
    
    Args:
        template_id: ID of the template to update
        update_data: Template update data
        service: Generation service instance
        
    Returns:
        DynamicCrewTemplateResponse with updated template
        
    Raises:
        HTTPException: If template not found
    """
    template = await service.update_template(template_id, update_data)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template {template_id} not found"
        )
    return template 