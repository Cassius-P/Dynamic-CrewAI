#!/usr/bin/env python3
"""
Phase 7: Dynamic Crew Generation Demo

This demo showcases the AI-powered dynamic crew generation capabilities including:
- Automatic crew composition based on objectives
- LLM-powered task analysis
- Intelligent agent and tool selection
- Manager agent coordination
- Crew optimization and validation
- Template-based generation
- Bulk generation capabilities

Requirements:
- Run: pip install -r requirements.txt
- Ensure database is set up and migrated
- Set appropriate environment variables for LLM providers
"""

import asyncio
import json
import sys
import os
from datetime import datetime
from typing import Dict, Any, List

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.database import get_db, engine
from app.models import generation
from app.core.dynamic_crew_generator import DynamicCrewGenerator
from app.core.llm_wrapper import LLMWrapper
from app.core.tool_registry import ToolRegistry
from app.services.generation_service import GenerationService
from app.schemas.generation import (
    GenerationRequestCreate, TaskAnalysisRequest, CrewValidationRequest,
    CrewOptimizationRequest, DynamicCrewTemplateCreate, BulkGenerationRequest
)

# Demo configuration
DEMO_CONFIG = {
    "llm_provider": "openai",  # Change to your preferred provider
    "verbose": True,
    "use_fallback": False  # Set to True if you don't have LLM API keys
}

class Phase7Demo:
    """Demo class for Phase 7: Dynamic Crew Generation."""
    
    def __init__(self):
        """Initialize demo components."""
        print("🚀 Initializing Phase 7: Dynamic Crew Generation Demo")
        print("=" * 60)
        
        # Initialize database session
        self.db_session = next(get_db())
        
        # Initialize services
        self.generation_service = GenerationService(self.db_session)
        
        # Demo scenarios
        self.scenarios = [
            {
                "name": "Marketing Campaign Generation",
                "objective": "Create a comprehensive marketing strategy for launching a new sustainable fashion brand targeting Gen Z consumers",
                "requirements": {
                    "budget": "moderate",
                    "timeline": "6 weeks",
                    "target_audience": "Gen Z",
                    "industry": "fashion",
                    "focus": "sustainability"
                }
            },
            {
                "name": "Software Development Project",
                "objective": "Build a mobile application for real-time collaborative project management with AI-powered task prioritization",
                "requirements": {
                    "platform": "cross-platform",
                    "technology": "React Native",
                    "features": ["real-time collaboration", "AI prioritization", "mobile-first"],
                    "timeline": "12 weeks",
                    "complexity": "high"
                }
            },
            {
                "name": "Data Analytics Initiative",
                "objective": "Analyze customer behavior data to identify patterns and recommend personalization strategies for an e-commerce platform",
                "requirements": {
                    "data_sources": ["web analytics", "purchase history", "customer support"],
                    "deliverables": ["insights report", "ML models", "dashboard"],
                    "timeline": "8 weeks",
                    "compliance": "GDPR"
                }
            },
            {
                "name": "Content Creation Campaign",
                "objective": "Develop a multi-channel content strategy for a B2B SaaS company to increase thought leadership and lead generation",
                "requirements": {
                    "channels": ["blog", "LinkedIn", "webinars", "podcasts"],
                    "content_types": ["articles", "videos", "infographics"],
                    "target": "B2B decision makers",
                    "timeline": "4 weeks"
                }
            }
        ]
    
    async def run_complete_demo(self):
        """Run the complete Phase 7 demo."""
        try:
            print(f"📅 Demo started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            
            # 1. Task Analysis Demo
            await self.demo_task_analysis()
            
            # 2. Basic Crew Generation Demo  
            await self.demo_basic_crew_generation()
            
            # 3. Template Creation and Usage Demo
            await self.demo_template_management()
            
            # 4. Crew Optimization Demo
            await self.demo_crew_optimization()
            
            # 5. Crew Validation Demo
            await self.demo_crew_validation()
            
            # 6. Bulk Generation Demo
            await self.demo_bulk_generation()
            
            # 7. Advanced Features Demo
            await self.demo_advanced_features()
            
            print("\n🎉 Phase 7 Demo completed successfully!")
            print("=" * 60)
            
        except Exception as e:
            print(f"❌ Demo failed: {str(e)}")
            raise
        finally:
            self.db_session.close()
    
    async def demo_task_analysis(self):
        """Demo the task analysis capabilities."""
        print("🔍 DEMO 1: Task Analysis")
        print("-" * 40)
        
        scenario = self.scenarios[0]  # Marketing campaign
        
        print(f"📋 Analyzing task: {scenario['name']}")
        print(f"🎯 Objective: {scenario['objective']}")
        print()
        
        # Create task analysis request
        analysis_request = TaskAnalysisRequest(
            objective=scenario['objective'],
            context=f"Budget: {scenario['requirements']['budget']}, Timeline: {scenario['requirements']['timeline']}",
            domain=scenario['requirements'].get('industry', 'general')
        )
        
        try:
            # Perform analysis
            print("⚡ Performing AI-powered task analysis...")
            analysis_result = await self.generation_service.analyze_task(analysis_request)
            
            # Display results
            print("📊 Analysis Results:")
            print(f"   • Complexity Score: {analysis_result.complexity_score}/10")
            print(f"   • Estimated Duration: {analysis_result.estimated_duration_hours} hours")
            print(f"   • Domain Category: {analysis_result.domain_category}")
            print(f"   • Required Skills: {', '.join(analysis_result.required_skills)}")
            print(f"   • Required Tools: {', '.join(analysis_result.required_tools)}")
            print(f"   • Risk Factors: {', '.join(analysis_result.risk_factors)}")
            
        except Exception as e:
            print(f"⚠️  Analysis failed (using fallback): {str(e)}")
        
        print("\n✅ Task analysis demo completed\n")
    
    async def demo_basic_crew_generation(self):
        """Demo basic dynamic crew generation."""
        print("🤖 DEMO 2: Dynamic Crew Generation")
        print("-" * 40)
        
        scenario = self.scenarios[1]  # Software development
        
        print(f"🛠️  Generating crew for: {scenario['name']}")
        print(f"🎯 Objective: {scenario['objective']}")
        print()
        
        # Create generation request
        generation_request = GenerationRequestCreate(
            objective=scenario['objective'],
            requirements=scenario['requirements'],
            llm_provider=DEMO_CONFIG['llm_provider'],
            optimization_enabled=True
        )
        
        try:
            print("🔄 Generating dynamic crew configuration...")
            result = await self.generation_service.create_generation_request(generation_request)
            
            print("🎉 Crew generation completed!")
            print(f"   • Request ID: {result.id}")
            print(f"   • Status: {result.generation_status}")
            print(f"   • Generated Crew ID: {result.generated_crew_id}")
            print(f"   • Generation Time: {result.generation_time_seconds:.2f}s")
            print(f"   • Optimization Applied: {result.optimization_applied}")
            
            if result.generation_result:
                crew_config = result.generation_result.crew_config
                agent_configs = result.generation_result.agent_configs
                manager_config = result.generation_result.manager_config
                
                print(f"\n📋 Crew Configuration:")
                print(f"   • Name: {crew_config.get('name', 'N/A')}")
                print(f"   • Process: {crew_config.get('process', 'N/A')}")
                print(f"   • Agent Count: {len(agent_configs)}")
                
                print(f"\n👥 Generated Agents:")
                for i, agent in enumerate(agent_configs[:3], 1):  # Show first 3
                    print(f"   {i}. {agent.get('role', 'Unknown Role')}")
                    print(f"      Goal: {agent.get('goal', 'N/A')}")
                    print(f"      Skills: {', '.join(agent.get('skills', []))}")
                
                print(f"\n👨‍💼 Manager Agent:")
                print(f"   • Role: {manager_config.get('role', 'N/A')}")
                print(f"   • Coordination Style: {manager_config.get('coordination_style', 'N/A')}")
                print(f"   • Manages: {len(manager_config.get('managed_agents', []))} agents")
                
                if result.generation_result.estimated_performance:
                    perf = result.generation_result.estimated_performance
                    print(f"\n📈 Performance Estimates:")
                    print(f"   • Success Rate: {perf.get('estimated_success_rate', 0):.1%}")
                    print(f"   • Efficiency Score: {perf.get('efficiency_score', 0):.2f}")
                    print(f"   • Overall Score: {perf.get('overall_score', 0):.2f}")
            
        except Exception as e:
            print(f"⚠️  Generation failed: {str(e)}")
        
        print("\n✅ Basic crew generation demo completed\n")
    
    async def demo_template_management(self):
        """Demo template creation and usage."""
        print("📝 DEMO 3: Template Management")
        print("-" * 40)
        
        # Create a template
        template_data = DynamicCrewTemplateCreate(
            name="Data Analytics Team Template",
            description="Reusable template for data analytics projects",
            template_type="analytics",
            template_config={
                "preferred_agent_roles": ["Data Scientist", "Data Engineer", "Business Analyst"],
                "required_tools": ["analysis_tools", "visualization_tools", "sql_tools"],
                "optimization_focus": "accuracy",
                "team_size_range": [3, 5],
                "coordination_style": "collaborative"
            }
        )
        
        try:
            print("📋 Creating analytics team template...")
            template = await self.generation_service.create_template(template_data)
            
            print(f"✅ Template created!")
            print(f"   • Template ID: {template.id}")
            print(f"   • Name: {template.name}")
            print(f"   • Type: {template.template_type}")
            print(f"   • Success Rate: {template.success_rate:.1%}")
            
            # Use the template for generation
            print(f"\n🔄 Generating crew using template...")
            scenario = self.scenarios[2]  # Data analytics
            
            generation_request = GenerationRequestCreate(
                objective=scenario['objective'],
                requirements=scenario['requirements'],
                template_id=template.id,
                llm_provider=DEMO_CONFIG['llm_provider']
            )
            
            result = await self.generation_service.create_generation_request(generation_request)
            
            print(f"🎉 Template-based generation completed!")
            print(f"   • Used Template: {template.name}")
            print(f"   • Status: {result.generation_status}")
            print(f"   • Agent Count: {len(result.generation_result.agent_configs) if result.generation_result else 0}")
            
        except Exception as e:
            print(f"⚠️  Template demo failed: {str(e)}")
        
        print("\n✅ Template management demo completed\n")
    
    async def demo_crew_optimization(self):
        """Demo crew optimization capabilities."""
        print("⚡ DEMO 4: Crew Optimization")
        print("-" * 40)
        
        try:
            # First, get a crew to optimize (from previous demo)
            requests = await self.generation_service.list_generation_requests(limit=1)
            
            if not requests or not requests[0].generated_crew_id:
                print("⚠️  No crew available for optimization demo")
                return
            
            crew_id = requests[0].generated_crew_id
            print(f"🎯 Optimizing Crew ID: {crew_id}")
            
            # Performance optimization
            print("\n🚀 Applying performance optimization...")
            perf_request = CrewOptimizationRequest(
                crew_id=crew_id,
                optimization_type="performance",
                target_metrics={"efficiency": 0.9, "speed": 0.8}
            )
            
            perf_result = await self.generation_service.optimize_crew(perf_request)
            
            print(f"✅ Performance optimization completed!")
            print(f"   • Optimization ID: {perf_result.id}")
            print(f"   • Score: {perf_result.optimization_score:.2f}/10")
            print(f"   • Applied: {perf_result.applied}")
            
            # Cost optimization
            print("\n💰 Applying cost optimization...")
            cost_request = CrewOptimizationRequest(
                crew_id=crew_id,
                optimization_type="cost",
                target_metrics={"cost_efficiency": 0.8}
            )
            
            cost_result = await self.generation_service.optimize_crew(cost_request)
            
            print(f"✅ Cost optimization completed!")
            print(f"   • Optimization ID: {cost_result.id}")
            print(f"   • Score: {cost_result.optimization_score:.2f}/10")
            print(f"   • Applied: {cost_result.applied}")
            
        except Exception as e:
            print(f"⚠️  Optimization demo failed: {str(e)}")
        
        print("\n✅ Crew optimization demo completed\n")
    
    async def demo_crew_validation(self):
        """Demo crew validation capabilities."""
        print("🔍 DEMO 5: Crew Configuration Validation")
        print("-" * 40)
        
        # Create a sample crew config to validate
        crew_config = {
            "name": "Sample Marketing Team",
            "description": "A marketing team for product launch",
            "process": "hierarchical",
            "agents": [
                {
                    "role": "Marketing Strategist",
                    "goal": "Develop comprehensive marketing strategy",
                    "skills": ["strategy", "market_research", "analytics"]
                },
                {
                    "role": "Content Creator",
                    "goal": "Create engaging marketing content",
                    "skills": ["writing", "design", "social_media"]
                },
                {
                    "role": "Digital Marketing Specialist",
                    "goal": "Execute digital marketing campaigns",
                    "skills": ["digital_marketing", "SEO", "advertising"]
                }
            ],
            "manager_agent": {
                "role": "Marketing Manager",
                "coordination_style": "collaborative"
            }
        }
        
        objective = "Launch a successful marketing campaign for a new product"
        
        try:
            print("🔍 Validating crew configuration...")
            print(f"🎯 Objective: {objective}")
            print(f"👥 Agents: {len(crew_config['agents'])}")
            
            validation_request = CrewValidationRequest(
                crew_config=crew_config,
                objective=objective
            )
            
            validation_result = await self.generation_service.validate_crew_configuration(validation_request)
            
            print(f"\n📊 Validation Results:")
            print(f"   • Valid: {'✅' if validation_result.valid else '❌'}")
            print(f"   • Validation Score: {validation_result.validation_score:.1f}/10")
            print(f"   • Success Rate: {validation_result.estimated_success_rate:.1%}")
            
            if validation_result.issues:
                print(f"   • Issues: {len(validation_result.issues)}")
                for issue in validation_result.issues[:3]:
                    print(f"     - {issue}")
            
            if validation_result.warnings:
                print(f"   • Warnings: {len(validation_result.warnings)}")
                for warning in validation_result.warnings[:3]:
                    print(f"     - {warning}")
            
            if validation_result.recommendations:
                print(f"   • Recommendations: {len(validation_result.recommendations)}")
                for rec in validation_result.recommendations[:3]:
                    print(f"     - {rec}")
            
        except Exception as e:
            print(f"⚠️  Validation demo failed: {str(e)}")
        
        print("\n✅ Crew validation demo completed\n")
    
    async def demo_bulk_generation(self):
        """Demo bulk crew generation capabilities."""
        print("📦 DEMO 6: Bulk Crew Generation")
        print("-" * 40)
        
        # Create bulk generation request
        objectives = [
            "Create a social media marketing campaign for a new fitness app",
            "Develop a customer onboarding process for a SaaS platform",
            "Design a user research study for an e-commerce website redesign"
        ]
        
        bulk_request = BulkGenerationRequest(
            objectives=objectives,
            shared_requirements={
                "timeline": "4 weeks",
                "budget": "moderate",
                "industry": "technology"
            },
            llm_provider=DEMO_CONFIG['llm_provider']
        )
        
        try:
            print(f"🔄 Generating {len(objectives)} crews in bulk...")
            for i, obj in enumerate(objectives, 1):
                print(f"   {i}. {obj[:60]}...")
            
            bulk_result = await self.generation_service.bulk_generate(bulk_request)
            
            print(f"\n📊 Bulk Generation Results:")
            print(f"   • Total Requests: {bulk_result.total_requests}")
            print(f"   • Successful: {bulk_result.successful_generations}")
            print(f"   • Failed: {bulk_result.failed_generations}")
            print(f"   • Success Rate: {(bulk_result.successful_generations/bulk_result.total_requests)*100:.1f}%")
            
            if bulk_result.errors:
                print(f"   • Errors: {len(bulk_result.errors)}")
                for error in bulk_result.errors[:2]:
                    print(f"     - {error}")
            
            print(f"\n✅ Generated crews:")
            for i, request in enumerate(bulk_result.generation_requests, 1):
                print(f"   {i}. Status: {request.generation_status} | "
                      f"Crew ID: {request.generated_crew_id or 'N/A'}")
            
        except Exception as e:
            print(f"⚠️  Bulk generation demo failed: {str(e)}")
        
        print("\n✅ Bulk generation demo completed\n")
    
    async def demo_advanced_features(self):
        """Demo advanced features and capabilities."""
        print("🌟 DEMO 7: Advanced Features")
        print("-" * 40)
        
        try:
            # List all generation requests
            print("📋 Recent Generation Requests:")
            requests = await self.generation_service.list_generation_requests(limit=5)
            
            for i, request in enumerate(requests, 1):
                print(f"   {i}. ID: {request.id} | Status: {request.generation_status} | "
                      f"Created: {request.created_at.strftime('%Y-%m-%d %H:%M')}")
            
            # List all templates
            print(f"\n📝 Available Templates:")
            templates = await self.generation_service.list_templates(limit=5)
            
            for i, template in enumerate(templates, 1):
                print(f"   {i}. {template.name} | Type: {template.template_type} | "
                      f"Success Rate: {template.success_rate:.1%} | Used: {template.usage_count} times")
            
            # Show statistics
            print(f"\n📊 Demo Statistics:")
            print(f"   • Total Requests: {len(requests)}")
            print(f"   • Total Templates: {len(templates)}")
            
            completed_requests = [r for r in requests if r.generation_status == "completed"]
            if completed_requests:
                avg_time = sum(r.generation_time_seconds or 0 for r in completed_requests) / len(completed_requests)
                print(f"   • Average Generation Time: {avg_time:.2f}s")
                print(f"   • Success Rate: {len(completed_requests)/len(requests)*100:.1f}%")
            
        except Exception as e:
            print(f"⚠️  Advanced features demo failed: {str(e)}")
        
        print("\n✅ Advanced features demo completed\n")
    
    def print_capabilities_summary(self):
        """Print a summary of Phase 7 capabilities."""
        print("🎯 Phase 7: Dynamic Crew Generation - Capabilities Summary")
        print("=" * 60)
        print()
        
        capabilities = [
            "🤖 AI-Powered Crew Composition",
            "   • Automatic agent role determination based on objectives",
            "   • Intelligent skill and tool assignment",
            "   • LLM-driven task complexity analysis",
            "",
            "👨‍💼 Automatic Manager Agent Coordination",
            "   • Hierarchical crew structure with manager oversight",
            "   • Delegation-enabled manager agents",
            "   • Coordination style optimization",
            "",
            "⚡ Dynamic Optimization",
            "   • Performance, cost, and speed optimization",
            "   • Real-time crew configuration adjustments",
            "   • ML-driven improvement suggestions",
            "",
            "🔍 Intelligent Validation",
            "   • Crew configuration validation",
            "   • Success rate estimation",
            "   • Issue detection and recommendations",
            "",
            "📝 Template-Based Generation",
            "   • Reusable crew patterns",
            "   • Learning from successful configurations",
            "   • Domain-specific templates",
            "",
            "📦 Bulk Operations",
            "   • Multiple crew generation in parallel",
            "   • Batch optimization and validation",
            "   • Scalable enterprise operations",
            "",
            "🔧 Advanced Features",
            "   • Comprehensive API endpoints",
            "   • Performance metrics and analytics",
            "   • Extensible plugin architecture"
        ]
        
        for capability in capabilities:
            print(capability)
        
        print()
        print("🚀 Ready for production deployment!")
        print("=" * 60)


async def main():
    """Main demo function."""
    demo = Phase7Demo()
    
    # Print capabilities summary
    demo.print_capabilities_summary()
    print()
    
    # Run the complete demo
    await demo.run_complete_demo()


if __name__ == "__main__":
    # Ensure event loop is available
    if sys.platform.startswith('win'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main()) 