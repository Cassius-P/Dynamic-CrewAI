"""Tests for generation API endpoints."""

import pytest
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient
from fastapi import status

from app.main import app
from app.schemas.generation import (
    GenerationRequestResponse, TaskAnalysisResponse, CrewValidationResponse,
    CrewOptimizationResponse, DynamicCrewTemplateResponse, BulkGenerationResponse
)
from datetime import datetime


class TestGenerationEndpoints:
    """Test cases for generation API endpoints."""
    
    def test_create_generation_request_success(self, client):
        """Test successful generation request creation."""
        mock_response = GenerationRequestResponse(
            id=1,
            objective="Test objective",
            requirements={"budget": "moderate"},
            generated_crew_id=123,
            template_id=None,
            llm_provider="openai",
            generation_status="completed",
            generation_result=None,
            validation_result=None,
            optimization_applied=False,
            generation_time_seconds=5.5,
            created_at=datetime.utcnow(),
            completed_at=datetime.utcnow()
        )
        
        with patch('app.services.generation_service.GenerationService.create_generation_request') as mock_create:
            mock_create.return_value = mock_response
            
            request_data = {
                "objective": "Create a comprehensive marketing strategy for launching a new product",
                "requirements": {"budget": "moderate", "timeline": "4 weeks"},
                "llm_provider": "openai",
                "optimization_enabled": True
            }
            
            response = client.post("/api/v1/generation/generate", json=request_data)
            
            assert response.status_code == status.HTTP_201_CREATED
            mock_create.assert_called_once()
    
    def test_create_generation_request_validation_error(self, client):
        """Test generation request with validation error."""
        with patch('app.services.generation_service.GenerationService.create_generation_request') as mock_create:
            mock_create.side_effect = ValueError("Invalid template")
            
            request_data = {
                "objective": "Create a comprehensive marketing strategy for launching a new product",
                "template_id": 999
            }
            
            response = client.post("/api/v1/generation/generate", json=request_data)
            
            assert response.status_code == status.HTTP_400_BAD_REQUEST
            assert "Invalid template" in response.json()["detail"]
    
    def test_create_generation_request_server_error(self, client):
        """Test generation request with server error."""
        with patch('app.services.generation_service.GenerationService.create_generation_request') as mock_create:
            mock_create.side_effect = Exception("Database error")
            
            request_data = {
                "objective": "Valid objective for testing server error handling"
            }
            
            response = client.post("/api/v1/generation/generate", json=request_data)
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to create generation request" in response.json()["detail"]
    
    def test_get_generation_request_found(self, client):
        """Test retrieving existing generation request."""
        mock_response = GenerationRequestResponse(
            id=1,
            objective="Test objective",
            requirements=None,
            generated_crew_id=None,
            template_id=None,
            llm_provider="openai",
            generation_status="completed",
            generation_result=None,
            validation_result=None,
            optimization_applied=False,
            generation_time_seconds=None,
            created_at=datetime.utcnow(),
            completed_at=None
        )
        
        with patch('app.services.generation_service.GenerationService.get_generation_request') as mock_get:
            mock_get.return_value = mock_response
            
            response = client.get("/api/v1/generation/requests/1")
            
            assert response.status_code == status.HTTP_200_OK
            mock_get.assert_called_with(1)
    
    def test_get_generation_request_not_found(self, client):
        """Test retrieving non-existent generation request."""
        with patch('app.services.generation_service.GenerationService.get_generation_request') as mock_get:
            mock_get.return_value = None
            
            response = client.get("/api/v1/generation/requests/999")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Generation request 999 not found" in response.json()["detail"]
    
    def test_list_generation_requests(self, client):
        """Test listing generation requests."""
        mock_requests = [
            GenerationRequestResponse(
                id=i + 1,
                objective=f"Objective {i + 1}",
                requirements=None,
                generated_crew_id=None,
                template_id=None,
                llm_provider="openai",
                generation_status="completed",
                generation_result=None,
                validation_result=None,
                optimization_applied=False,
                generation_time_seconds=None,
                created_at=datetime.utcnow(),
                completed_at=None
            ) for i in range(3)
        ]
        
        with patch('app.services.generation_service.GenerationService.list_generation_requests') as mock_list:
            mock_list.return_value = mock_requests
            
            response = client.get("/api/v1/generation/requests?skip=0&limit=10")
            
            assert response.status_code == status.HTTP_200_OK
            mock_list.assert_called_with(skip=0, limit=10)
    
    def test_list_generation_requests_limit_exceeded(self, client):
        """Test listing with limit exceeded."""
        response = client.get("/api/v1/generation/requests?limit=1001")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Limit cannot exceed 1000" in response.json()["detail"]
    
    def test_analyze_task_success(self, client):
        """Test successful task analysis."""
        mock_response = TaskAnalysisResponse(
            objective="Build web app",
            complexity_score=7.5,
            estimated_duration_hours=40,
            required_skills=["programming", "design"],
            required_tools=["development_tools"],
            task_requirements=[],
            domain_category="web_development",
            risk_factors=[]
        )
        
        with patch('app.services.generation_service.GenerationService.analyze_task') as mock_analyze:
            mock_analyze.return_value = mock_response
            
            request_data = {
                "objective": "Build a web application for e-commerce",
                "context": "Small business needs online store",
                "domain": "web_development"
            }
            
            response = client.post("/api/v1/generation/analyze", json=request_data)
            
            assert response.status_code == status.HTTP_200_OK
            mock_analyze.assert_called_once()
    
    def test_analyze_task_error(self, client):
        """Test task analysis with error."""
        with patch('app.services.generation_service.GenerationService.analyze_task') as mock_analyze:
            mock_analyze.side_effect = Exception("Analysis failed")
            
            request_data = {
                "objective": "Test objective for analysis error"
            }
            
            response = client.post("/api/v1/generation/analyze", json=request_data)
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to analyze task" in response.json()["detail"]
    
    def test_validate_crew_configuration_success(self, client):
        """Test successful crew validation."""
        mock_response = CrewValidationResponse(
            valid=True,
            validation_score=8.5,
            issues=[],
            warnings=["Consider adding specialist"],
            recommendations=[],
            capability_coverage={},
            estimated_success_rate=0.85
        )
        
        with patch('app.services.generation_service.GenerationService.validate_crew_configuration') as mock_validate:
            mock_validate.return_value = mock_response
            
            request_data = {
                "crew_config": {
                    "name": "Test Crew",
                    "agents": [{"role": "Developer"}],
                    "process": "hierarchical"
                },
                "objective": "Build software application"
            }
            
            response = client.post("/api/v1/generation/validate", json=request_data)
            
            assert response.status_code == status.HTTP_200_OK
            mock_validate.assert_called_once()
    
    def test_validate_crew_configuration_error(self, client):
        """Test crew validation with error."""
        with patch('app.services.generation_service.GenerationService.validate_crew_configuration') as mock_validate:
            mock_validate.side_effect = Exception("Validation failed")
            
            request_data = {
                "crew_config": {"invalid": "config"},
                "objective": "Test objective"
            }
            
            response = client.post("/api/v1/generation/validate", json=request_data)
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to validate crew configuration" in response.json()["detail"]
    
    def test_optimize_crew_success(self, client):
        """Test successful crew optimization."""
        mock_response = CrewOptimizationResponse(
            id=1,
            crew_id=123,
            optimization_type="performance",
            optimization_score=7.8,
            optimization_metrics={},
            applied=False,
            created_at=datetime.utcnow(),
            applied_at=None
        )
        
        with patch('app.services.generation_service.GenerationService.optimize_crew') as mock_optimize:
            mock_optimize.return_value = mock_response
            
            request_data = {
                "crew_id": 123,
                "optimization_type": "performance",
                "target_metrics": {"efficiency": 0.8, "cost": 0.7}
            }
            
            response = client.post("/api/v1/generation/optimize", json=request_data)
            
            assert response.status_code == status.HTTP_200_OK
            mock_optimize.assert_called_once()
    
    def test_optimize_crew_not_found(self, client):
        """Test crew optimization with non-existent crew."""
        with patch('app.services.generation_service.GenerationService.optimize_crew') as mock_optimize:
            mock_optimize.side_effect = ValueError("Crew 999 not found")
            
            request_data = {
                "crew_id": 999,
                "optimization_type": "performance"
            }
            
            response = client.post("/api/v1/generation/optimize", json=request_data)
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Crew 999 not found" in response.json()["detail"]
    
    def test_optimize_crew_server_error(self, client):
        """Test crew optimization with server error."""
        with patch('app.services.generation_service.GenerationService.optimize_crew') as mock_optimize:
            mock_optimize.side_effect = Exception("Optimization failed")
            
            request_data = {
                "crew_id": 123,
                "optimization_type": "performance"
            }
            
            response = client.post("/api/v1/generation/optimize", json=request_data)
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to optimize crew" in response.json()["detail"]
    
    def test_bulk_generate_success(self, client):
        """Test successful bulk generation."""
        mock_response = BulkGenerationResponse(
            total_requests=3,
            successful_generations=2,
            failed_generations=1,
            generation_requests=[],
            errors=["One objective failed"]
        )
        
        with patch('app.services.generation_service.GenerationService.bulk_generate') as mock_bulk:
            mock_bulk.return_value = mock_response
            
            request_data = {
                "objectives": [
                    "Create marketing campaign",
                    "Analyze customer data", 
                    "Develop mobile app"
                ],
                "shared_requirements": {"budget": "moderate"},
                "llm_provider": "openai"
            }
            
            response = client.post("/api/v1/generation/bulk-generate", json=request_data)
            
            assert response.status_code == status.HTTP_200_OK
            mock_bulk.assert_called_once()
    
    def test_bulk_generate_too_many_objectives(self, client):
        """Test bulk generation with too many objectives."""
        request_data = {
            "objectives": [f"Objective {i}" for i in range(11)]  # 11 objectives
        }
        
        response = client.post("/api/v1/generation/bulk-generate", json=request_data)
        
        # This should fail at the FastAPI validation level
        assert response.status_code in [status.HTTP_422_UNPROCESSABLE_ENTITY, status.HTTP_400_BAD_REQUEST]
    
    def test_bulk_generate_error(self, client):
        """Test bulk generation with error."""
        with patch('app.services.generation_service.GenerationService.bulk_generate') as mock_bulk:
            mock_bulk.side_effect = Exception("Bulk generation failed")
            
            request_data = {
                "objectives": ["Test objective 1", "Test objective 2"]
            }
            
            response = client.post("/api/v1/generation/bulk-generate", json=request_data)
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to bulk generate crews" in response.json()["detail"]
    
    # Template management endpoint tests
    def test_create_template_success(self, client):
        """Test successful template creation."""
        mock_response = DynamicCrewTemplateResponse(
            id=1,
            name="Analytics Template",
            description="Template for data analysis teams",
            template_type="analytics",
            template_config={"preferred_tools": ["analysis_tool"]},
            success_rate=0.0,
            usage_count=0,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=None
        )
        
        with patch('app.services.generation_service.GenerationService.create_template') as mock_create:
            mock_create.return_value = mock_response
            
            request_data = {
                "name": "Analytics Team Template",
                "description": "Template for data analysis teams",
                "template_type": "analytics",
                "template_config": {"preferred_tools": ["analysis_tool"]}
            }
            
            response = client.post("/api/v1/generation/templates", json=request_data)
            
            assert response.status_code == status.HTTP_201_CREATED
            mock_create.assert_called_once()
    
    def test_create_template_error(self, client):
        """Test template creation with error."""
        with patch('app.services.generation_service.GenerationService.create_template') as mock_create:
            mock_create.side_effect = Exception("Template creation failed")
            
            request_data = {
                "name": "Test Template",
                "template_type": "test",
                "template_config": {}
            }
            
            response = client.post("/api/v1/generation/templates", json=request_data)
            
            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
            assert "Failed to create template" in response.json()["detail"]
    
    def test_get_template_found(self, client):
        """Test retrieving existing template."""
        mock_response = DynamicCrewTemplateResponse(
            id=1,
            name="Test Template",
            description=None,
            template_type="test",
            template_config={},
            success_rate=0.0,
            usage_count=0,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=None
        )
        
        with patch('app.services.generation_service.GenerationService.get_template') as mock_get:
            mock_get.return_value = mock_response
            
            response = client.get("/api/v1/generation/templates/1")
            
            assert response.status_code == status.HTTP_200_OK
            mock_get.assert_called_with(1)
    
    def test_get_template_not_found(self, client):
        """Test retrieving non-existent template."""
        with patch('app.services.generation_service.GenerationService.get_template') as mock_get:
            mock_get.return_value = None
            
            response = client.get("/api/v1/generation/templates/999")
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Template 999 not found" in response.json()["detail"]
    
    def test_list_templates(self, client):
        """Test listing templates."""
        mock_templates = [
            DynamicCrewTemplateResponse(
                id=i + 1,
                name=f"Template {i + 1}",
                description=None,
                template_type="test",
                template_config={},
                success_rate=0.0,
                usage_count=0,
                is_active=True,
                created_at=datetime.utcnow(),
                updated_at=None
            ) for i in range(2)
        ]
        
        with patch('app.services.generation_service.GenerationService.list_templates') as mock_list:
            mock_list.return_value = mock_templates
            
            response = client.get("/api/v1/generation/templates?skip=0&limit=10")
            
            assert response.status_code == status.HTTP_200_OK
            mock_list.assert_called_with(skip=0, limit=10)
    
    def test_list_templates_limit_exceeded(self, client):
        """Test listing templates with limit exceeded."""
        response = client.get("/api/v1/generation/templates?limit=1001")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Limit cannot exceed 1000" in response.json()["detail"]
    
    def test_update_template_success(self, client):
        """Test successful template update."""
        mock_response = DynamicCrewTemplateResponse(
            id=1,
            name="Updated Template",
            description=None,
            template_type="test",
            template_config={},
            success_rate=0.0,
            usage_count=0,
            is_active=False,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        with patch('app.services.generation_service.GenerationService.update_template') as mock_update:
            mock_update.return_value = mock_response
            
            request_data = {
                "name": "Updated Template Name",
                "is_active": False
            }
            
            response = client.put("/api/v1/generation/templates/1", json=request_data)
            
            assert response.status_code == status.HTTP_200_OK
            mock_update.assert_called_once()
    
    def test_update_template_not_found(self, client):
        """Test updating non-existent template."""
        with patch('app.services.generation_service.GenerationService.update_template') as mock_update:
            mock_update.return_value = None
            
            request_data = {
                "name": "Updated Name"
            }
            
            response = client.put("/api/v1/generation/templates/999", json=request_data)
            
            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "Template 999 not found" in response.json()["detail"] 