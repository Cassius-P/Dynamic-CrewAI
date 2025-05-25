from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.models.crew import Crew
from app.schemas.crew import CrewCreate, CrewUpdate, CrewResponse

router = APIRouter()


@router.post("/", response_model=CrewResponse, status_code=status.HTTP_201_CREATED)
def create_crew(
    crew: CrewCreate,
    db: Session = Depends(get_db)
):
    """Create a new crew."""
    db_crew = Crew(**crew.model_dump())
    db.add(db_crew)
    db.commit()
    db.refresh(db_crew)
    return db_crew


@router.get("/", response_model=List[CrewResponse])
def read_crews(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Retrieve crews."""
    crews = db.query(Crew).offset(skip).limit(limit).all()
    return crews


@router.get("/{crew_id}", response_model=CrewResponse)
def read_crew(
    crew_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve a specific crew."""
    crew = db.query(Crew).filter(Crew.id == crew_id).first()
    if crew is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crew not found"
        )
    return crew


@router.put("/{crew_id}", response_model=CrewResponse)
def update_crew(
    crew_id: int,
    crew_update: CrewUpdate,
    db: Session = Depends(get_db)
):
    """Update a crew."""
    crew = db.query(Crew).filter(Crew.id == crew_id).first()
    if crew is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crew not found"
        )
    
    update_data = crew_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(crew, field, value)
    
    db.commit()
    db.refresh(crew)
    return crew


@router.delete("/{crew_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_crew(
    crew_id: int,
    db: Session = Depends(get_db)
):
    """Delete a crew."""
    crew = db.query(Crew).filter(Crew.id == crew_id).first()
    if crew is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Crew not found"
        )
    
    db.delete(crew)
    db.commit()
    return None
