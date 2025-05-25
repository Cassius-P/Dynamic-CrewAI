from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.llm_provider import LLMProvider
from app.schemas.llm_provider import LLMProviderCreate, LLMProviderUpdate, LLMProviderResponse

router = APIRouter()


@router.post("/", response_model=LLMProviderResponse, status_code=status.HTTP_201_CREATED)
def create_llm_provider(
    provider: LLMProviderCreate,
    db: Session = Depends(get_db)
):
    """Create a new LLM provider."""
    db_provider = LLMProvider(**provider.model_dump())
    db.add(db_provider)
    db.commit()
    db.refresh(db_provider)
    return db_provider


@router.get("/", response_model=List[LLMProviderResponse])
def read_llm_providers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Retrieve LLM providers."""
    providers = db.query(LLMProvider).offset(skip).limit(limit).all()
    return providers


@router.get("/{provider_id}", response_model=LLMProviderResponse)
def read_llm_provider(
    provider_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve a specific LLM provider."""
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM Provider not found"
        )
    return provider


@router.put("/{provider_id}", response_model=LLMProviderResponse)
def update_llm_provider(
    provider_id: int,
    provider_update: LLMProviderUpdate,
    db: Session = Depends(get_db)
):
    """Update an LLM provider."""
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM Provider not found"
        )
    
    update_data = provider_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(provider, field, value)
    
    db.commit()
    db.refresh(provider)
    return provider


@router.delete("/{provider_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_llm_provider(
    provider_id: int,
    db: Session = Depends(get_db)
):
    """Delete an LLM provider."""
    provider = db.query(LLMProvider).filter(LLMProvider.id == provider_id).first()
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM Provider not found"
        )
    
    db.delete(provider)
    db.commit()
    return None
