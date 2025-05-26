"""Manager Agent API endpoints."""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from app.api.deps import get_db
from app.services.manager_agent_service import get_manager_agent_service, ManagerAgentService
from app.models.agent import Agent
from app.models.execution import Execution
from app.schemas.agent import AgentCreate, AgentUpdate, AgentResponse

router = APIRouter()


# Pydantic models for manager agent specific operations
class ManagerAgentCreate(BaseModel):
    """Schema for creating a manager agent."""
    role: str = Field(..., description="Role of the manager agent")
    goal: str = Field(..., description="Goal of the manager agent")
    backstory: str = Field(..., description="Backstory of the manager agent")
    manager_type: str = Field(default="hierarchical", description="Type of manager agent")
    can_generate_tasks: bool = Field(default=True, description="Whether the agent can generate tasks")
    allow_delegation: bool = Field(default=True, description="Whether the agent allows delegation")
    manager_config: Optional[Dict[str, Any]] = Field(default=None, description="Manager-specific configuration")
    tools: Optional[List[str]] = Field(default=None, description="List of tools available to the agent")
    llm_provider_id: Optional[int] = Field(default=None, description="LLM provider ID")


class ManagerAgentUpdate(BaseModel):
    """Schema for updating a manager agent."""
    role: Optional[str] = Field(None, description="Role of the manager agent")
    goal: Optional[str] = Field(None, description="Goal of the manager agent")
    backstory: Optional[str] = Field(None, description="Backstory of the manager agent")
    manager_type: Optional[str] = Field(None, description="Type of manager agent")
    can_generate_tasks: Optional[bool] = Field(None, description="Whether the agent can generate tasks")
    allow_delegation: Optional[bool] = Field(None, description="Whether the agent allows delegation")
    manager_config: Optional[Dict[str, Any]] = Field(None, description="Manager-specific configuration")
    tools: Optional[List[str]] = Field(None, description="List of tools available to the agent")
    llm_provider_id: Optional[int] = Field(None, description="LLM provider ID")


class TaskGenerationRequest(BaseModel):
    """Schema for task generation request."""
    text_input: str = Field(..., description="Text input to generate tasks from")
    max_tasks: int = Field(default=5, description="Maximum number of tasks to generate")


class TaskGenerationResponse(BaseModel):
    """Schema for task generation response."""
    tasks: List[Dict[str, Any]] = Field(..., description="Generated tasks")
    agent_id: int = Field(..., description="Manager agent ID")
    text_input: str = Field(..., description="Original text input")
    generated_at: str = Field(..., description="Generation timestamp")


class CrewExecutionRequest(BaseModel):
    """Schema for crew execution with manager agent."""
    agent_ids: List[int] = Field(..., description="List of agent IDs to include in the crew")
    text_input: str = Field(..., description="Text input to generate tasks from")
    crew_config: Optional[Dict[str, Any]] = Field(default=None, description="Additional crew configuration")


class ManagerAgentCapabilities(BaseModel):
    """Schema for manager agent capabilities."""
    agent_id: int
    role: str
    manager_type: str
    can_generate_tasks: bool
    allow_delegation: bool
    manager_config: Dict[str, Any]
    delegation_strategies: List[str]
    supported_manager_types: List[str]
    capabilities: Dict[str, bool]


class ManagerAgentStatistics(BaseModel):
    """Schema for manager agent statistics."""
    agent_id: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    manager_type: str
    can_generate_tasks: bool
    created_at: Optional[str]


# API Endpoints

@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_manager_agent(
    agent: ManagerAgentCreate,
    db: Session = Depends(get_db)
):
    """Create a new manager agent."""
    try:
        manager_service = get_manager_agent_service(db)
        agent_data = agent.model_dump()
        
        db_agent = manager_service.create_manager_agent(agent_data)
        return db_agent
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create manager agent: {str(e)}"
        )


@router.get("/", response_model=List[AgentResponse])
def list_manager_agents(
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """List all manager agents."""
    try:
        manager_service = get_manager_agent_service(db)
        manager_agents = manager_service.get_manager_agents(skip, limit)
        return manager_agents
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve manager agents: {str(e)}"
        )


@router.get("/{agent_id}", response_model=AgentResponse)
def get_manager_agent(
    agent_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific manager agent by ID."""
    try:
        manager_service = get_manager_agent_service(db)
        manager_agent = manager_service.get_manager_agent_by_id(agent_id)
        
        if manager_agent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Manager agent {agent_id} not found"
            )
        
        return manager_agent
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve manager agent: {str(e)}"
        )


@router.put("/{agent_id}", response_model=AgentResponse)
def update_manager_agent(
    agent_id: int,
    agent_update: ManagerAgentUpdate,
    db: Session = Depends(get_db)
):
    """Update a manager agent."""
    try:
        manager_service = get_manager_agent_service(db)
        update_data = agent_update.model_dump(exclude_unset=True)
        
        updated_agent = manager_service.update_manager_agent(agent_id, update_data)
        return updated_agent
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update manager agent: {str(e)}"
        )


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_manager_agent(
    agent_id: int,
    db: Session = Depends(get_db)
):
    """Delete a manager agent."""
    try:
        manager_service = get_manager_agent_service(db)
        manager_service.delete_manager_agent(agent_id)
        return None
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete manager agent: {str(e)}"
        )


@router.post("/{agent_id}/generate-tasks", response_model=TaskGenerationResponse)
def generate_tasks(
    agent_id: int,
    request: TaskGenerationRequest,
    db: Session = Depends(get_db)
):
    """Generate tasks from text input using a manager agent."""
    try:
        manager_service = get_manager_agent_service(db)
        
        generated_tasks = manager_service.generate_tasks_from_text(
            agent_id, request.text_input, request.max_tasks
        )
        
        response = TaskGenerationResponse(
            tasks=generated_tasks,
            agent_id=agent_id,
            text_input=request.text_input,
            generated_at=generated_tasks[0]["generated_at"] if generated_tasks else ""
        )
        
        return response
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate tasks: {str(e)}"
        )


@router.post("/execute-crew", response_model=Dict[str, Any])
def execute_crew_with_manager(
    request: CrewExecutionRequest,
    db: Session = Depends(get_db)
):
    """Execute a crew with manager agent generating tasks from text."""
    try:
        manager_service = get_manager_agent_service(db)
        
        execution_result = manager_service.execute_crew_with_manager_tasks(
            request.agent_ids, request.text_input, request.crew_config
        )
        
        return execution_result
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute crew: {str(e)}"
        )


@router.get("/{agent_id}/capabilities", response_model=ManagerAgentCapabilities)
def get_manager_agent_capabilities(
    agent_id: int,
    db: Session = Depends(get_db)
):
    """Get capabilities and configuration of a manager agent."""
    try:
        manager_service = get_manager_agent_service(db)
        capabilities = manager_service.get_manager_agent_capabilities(agent_id)
        
        return ManagerAgentCapabilities(**capabilities)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get capabilities: {str(e)}"
        )


@router.get("/{agent_id}/executions", response_model=List[Dict[str, Any]])
def get_manager_agent_executions(
    agent_id: int,
    skip: int = Query(0, description="Number of records to skip"),
    limit: int = Query(100, description="Maximum number of records to return"),
    db: Session = Depends(get_db)
):
    """Get execution history for a manager agent."""
    try:
        manager_service = get_manager_agent_service(db)
        executions = manager_service.get_manager_agent_executions(agent_id, skip, limit)
        
        # Convert executions to dict format
        execution_dicts = []
        for execution in executions:
            execution_dict = {
                "execution_id": execution.id,
                "status": execution.status.value if execution.status is not None else None,
                "result": execution.outputs,
                "start_time": execution.started_at.isoformat() if execution.started_at is not None else None,
                "end_time": execution.completed_at.isoformat() if execution.completed_at is not None else None,
                "execution_time": execution.execution_time,
                "error_message": execution.error_message,
                "metadata": getattr(execution, 'metadata', {})
            }
            execution_dicts.append(execution_dict)
        
        return execution_dicts
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get executions: {str(e)}"
        )


@router.get("/{agent_id}/statistics", response_model=ManagerAgentStatistics)
def get_manager_agent_statistics(
    agent_id: int,
    db: Session = Depends(get_db)
):
    """Get statistics for a manager agent."""
    try:
        manager_service = get_manager_agent_service(db)
        statistics = manager_service.get_manager_agent_statistics(agent_id)
        
        return ManagerAgentStatistics(**statistics)
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


@router.post("/{agent_id}/validate", response_model=Dict[str, Any])
def validate_manager_agent_config(
    agent_id: int,
    config: Dict[str, Any] = Body(..., description="Configuration to validate"),
    db: Session = Depends(get_db)
):
    """Validate manager agent configuration."""
    try:
        manager_service = get_manager_agent_service(db)
        
        # Get existing agent to merge with new config
        existing_agent = manager_service.get_manager_agent_by_id(agent_id)
        if existing_agent is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Manager agent {agent_id} not found"
            )
        
        # Merge existing config with new config for validation
        full_config = {
            "role": existing_agent.role,
            "goal": existing_agent.goal,
            "backstory": existing_agent.backstory,
            "manager_type": existing_agent.manager_type,
            "can_generate_tasks": existing_agent.can_generate_tasks,
            "allow_delegation": existing_agent.allow_delegation,
            "manager_config": existing_agent.manager_config if existing_agent.manager_config is not None else {}
        }
        full_config.update(config)
        
        validation_result = manager_service.validate_manager_agent_config(full_config)
        return validation_result
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate configuration: {str(e)}"
        ) 