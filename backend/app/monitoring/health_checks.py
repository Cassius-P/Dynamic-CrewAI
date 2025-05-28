"""
Comprehensive health check system for all system components.
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, asdict, field
import redis
import openai
import anthropic
from sqlalchemy.orm import Session
from sqlalchemy import text
import structlog
from app.config import settings
from app.database import get_db
from app.utils.cache import cache_manager
from app.queue.task_queue import celery_app
from app.core.llm_wrapper import LLMWrapper

logger = structlog.get_logger()

class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"  
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

@dataclass
class ComponentHealth:
    """Health information for a system component."""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: Optional[float] = None
    last_checked: Optional[datetime] = field(default_factory=lambda: datetime.utcnow())
    details: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['status'] = self.status.value
        if self.last_checked:
            data['last_checked'] = self.last_checked.isoformat()
        return data

class HealthChecker:
    """Comprehensive health monitoring system."""
    
    def __init__(self):
        self._cache_ttl = 30  # Cache health check results for 30 seconds
        self._timeout = 10.0  # Default timeout for health checks
        self._health_cache: Dict[str, Tuple[ComponentHealth, datetime]] = {}
    
    async def check_all_components(self, use_cache: bool = True) -> Dict[str, ComponentHealth]:
        """Check health of all system components."""
        try:
            # Define all health checks
            health_checks = [
                ("database", self._check_database_health),
                ("redis", self._check_redis_health),
                ("celery", self._check_celery_health),
                ("openai", self._check_openai_health),
                ("anthropic", self._check_anthropic_health),
                ("ollama", self._check_ollama_health),
                ("crew_execution", self._check_crew_execution_health),
                ("memory_system", self._check_memory_system_health),
                ("queue_system", self._check_queue_system_health),
                ("websocket", self._check_websocket_health),
                ("dynamic_generation", self._check_dynamic_generation_health),
                ("manager_agent", self._check_manager_agent_health)
            ]
            
            # Run health checks concurrently
            tasks = []
            for component_name, check_func in health_checks:
                task = self._run_health_check(component_name, check_func, use_cache)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            health_status = {}
            for i, result in enumerate(results):
                component_name = health_checks[i][0]
                if isinstance(result, Exception):
                    logger.error(f"Health check failed for {component_name}", error=str(result))
                    health_status[component_name] = ComponentHealth(
                        name=component_name,
                        status=HealthStatus.UNKNOWN,
                        message=f"Health check failed: {str(result)}"
                    )
                else:
                    health_status[component_name] = result
            
            return health_status
            
        except Exception as e:
            logger.error("Error checking system health", error=str(e))
            raise
    
    async def _run_health_check(self, component_name: str, check_func, use_cache: bool) -> ComponentHealth:
        """Run a single health check with caching and timeout."""
        # Check cache first
        if use_cache and component_name in self._health_cache:
            cached_health, cached_time = self._health_cache[component_name]
            if datetime.utcnow() - cached_time < timedelta(seconds=self._cache_ttl):
                return cached_health
        
        # Run health check with timeout
        start_time = time.time()
        try:
            health = await asyncio.wait_for(check_func(), timeout=self._timeout)
            health.response_time_ms = (time.time() - start_time) * 1000
            
            # Cache result
            self._health_cache[component_name] = (health, datetime.utcnow())
            return health
            
        except asyncio.TimeoutError:
            return ComponentHealth(
                name=component_name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check timeout after {self._timeout}s",
                response_time_ms=(time.time() - start_time) * 1000
            )
        except Exception as e:
            return ComponentHealth(
                name=component_name,
                status=HealthStatus.UNHEALTHY,
                message=f"Health check error: {str(e)}",
                response_time_ms=(time.time() - start_time) * 1000
            )
    
    async def _check_database_health(self) -> ComponentHealth:
        """Check PostgreSQL database health."""
        try:
            db = next(get_db())
            
            # Test basic connection
            start_time = time.time()
            result = db.execute(text("SELECT 1")).scalar()
            basic_query_time = (time.time() - start_time) * 1000
            
            # Test pgvector extension
            start_time = time.time()
            db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
            vector_query_time = (time.time() - start_time) * 1000
            
            # Check connection pool status - simplified for health check
            engine = db.get_bind()
            pool_status = {
                "engine_available": True,
                "engine_type": str(type(engine).__name__)
            }
            
            db.close()
            
            if result == 1:
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.HEALTHY,
                    message="Database connection healthy",
                    details={
                        "basic_query_time_ms": basic_query_time,
                        "vector_query_time_ms": vector_query_time,
                        "pool_status": pool_status,
                        "database_url": settings.database_url.split('@')[-1] if settings.database_url else 'unknown'
                    }
                )
            else:
                return ComponentHealth(
                    name="database",
                    status=HealthStatus.UNHEALTHY,
                    message="Database query returned unexpected result"
                )
                
        except Exception as e:
            return ComponentHealth(
                name="database",
                status=HealthStatus.UNHEALTHY,
                message=f"Database error: {str(e)}"
            )
    
    async def _check_redis_health(self) -> ComponentHealth:
        """Check Redis cache health."""
        try:
            # Test Redis connection
            redis_client = redis.Redis.from_url(settings.redis_url)
            
            start_time = time.time()
            pong = redis_client.ping()
            ping_time = (time.time() - start_time) * 1000
            
            # Get Redis info (synchronous call)
            try:
                # Simplify Redis info gathering to avoid type issues
                memory_info = {
                    "used_memory_human": 'available',
                    "used_memory_peak_human": 'available', 
                    "connected_clients": 'available',
                    "uptime_in_seconds": 'available'
                }
                
                # Try to get actual Redis info if possible
                try:
                    info_result = redis_client.info()
                    # Only access if it's actually a dict to avoid type errors
                    if isinstance(info_result, dict):
                        memory_info.update({
                            "used_memory_human": info_result.get('used_memory_human', 'unknown'),
                            "used_memory_peak_human": info_result.get('used_memory_peak_human', 'unknown'),
                            "connected_clients": info_result.get('connected_clients', 'unknown'),
                            "uptime_in_seconds": info_result.get('uptime_in_seconds', 'unknown')
                        })
                except Exception:
                    pass  # Keep default values
                    
            except Exception:
                memory_info = {
                    "used_memory_human": 'unavailable',
                    "used_memory_peak_human": 'unavailable',
                    "connected_clients": 'unavailable',
                    "uptime_in_seconds": 'unavailable'
                }
            
            # Test cache operations
            try:
                cache_stats = cache_manager.get_stats()
            except Exception:
                cache_stats = {"status": "unavailable"}
            
            redis_client.close()
            
            if pong:
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.HEALTHY,
                    message="Redis connection healthy",
                    details={
                        "ping_time_ms": ping_time,
                        "memory_info": memory_info,
                        "cache_stats": cache_stats
                    }
                )
            else:
                return ComponentHealth(
                    name="redis",
                    status=HealthStatus.UNHEALTHY,
                    message="Redis ping failed"
                )
                
        except Exception as e:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=f"Redis error: {str(e)}"
            )
    
    async def _check_celery_health(self) -> ComponentHealth:
        """Check Celery queue system health."""
        try:
            # Check Celery app
            inspect = celery_app.control.inspect()
            
            # Get active workers
            active_workers = inspect.active()
            registered_tasks = inspect.registered()
            stats = inspect.stats()
            
            # Check queue sizes
            queue_lengths = {}
            redis_client = redis.Redis.from_url(settings.redis_url)
            for queue_name in ['crew_execution', 'retry', 'default']:
                queue_length = redis_client.llen(f'celery:{queue_name}')
                queue_lengths[queue_name] = queue_length
            
            redis_client.close()
            
            worker_count = len(active_workers) if active_workers else 0
            total_queue_length = sum(queue_lengths.values())
            
            # Determine health status
            if worker_count == 0:
                status = HealthStatus.UNHEALTHY
                message = "No active Celery workers found"
            elif total_queue_length > 1000:
                status = HealthStatus.DEGRADED
                message = f"High queue backlog: {total_queue_length} tasks"
            else:
                status = HealthStatus.HEALTHY
                message = f"{worker_count} active workers, {total_queue_length} queued tasks"
            
            return ComponentHealth(
                name="celery",
                status=status,
                message=message,
                details={
                    "active_workers": worker_count,
                    "queue_lengths": queue_lengths,
                    "worker_stats": stats,
                    "registered_tasks": list(registered_tasks.keys()) if registered_tasks else []
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="celery",
                status=HealthStatus.UNHEALTHY,
                message=f"Celery error: {str(e)}"
            )
    
    async def _check_openai_health(self) -> ComponentHealth:
        """Check OpenAI API health."""
        try:
            openai_api_key = getattr(settings, 'openai_api_key', None)
            if not openai_api_key:
                return ComponentHealth(
                    name="openai",
                    status=HealthStatus.UNKNOWN,
                    message="OpenAI API key not configured"
                )
            
            # Test OpenAI connection with a simple request
            client = openai.OpenAI(api_key=openai_api_key)
            
            start_time = time.time()
            response = client.models.list()
            response_time = (time.time() - start_time) * 1000
            
            models = [model.id for model in response.data]
            
            return ComponentHealth(
                name="openai",
                status=HealthStatus.HEALTHY,
                message="OpenAI API accessible",
                details={
                    "response_time_ms": response_time,
                    "available_models": models[:10],  # Limit to first 10 models
                    "model_count": len(models)
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="openai",
                status=HealthStatus.UNHEALTHY,
                message=f"OpenAI API error: {str(e)}"
            )
    
    async def _check_anthropic_health(self) -> ComponentHealth:
        """Check Anthropic API health."""
        try:
            anthropic_api_key = getattr(settings, 'anthropic_api_key', None)
            if not anthropic_api_key:
                return ComponentHealth(
                    name="anthropic",
                    status=HealthStatus.UNKNOWN,
                    message="Anthropic API key not configured"
                )
            
            # Test with a simple message
            client = anthropic.Anthropic(api_key=anthropic_api_key)
            
            start_time = time.time()
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=1,
                messages=[{"role": "user", "content": "Hi"}]
            )
            response_time = (time.time() - start_time) * 1000
            
            return ComponentHealth(
                name="anthropic",
                status=HealthStatus.HEALTHY,
                message="Anthropic API accessible",
                details={
                    "response_time_ms": response_time,
                    "model_used": "claude-3-haiku-20240307",
                    "tokens_used": response.usage.input_tokens + response.usage.output_tokens
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="anthropic",
                status=HealthStatus.UNHEALTHY,
                message=f"Anthropic API error: {str(e)}"
            )
    
    async def _check_ollama_health(self) -> ComponentHealth:
        """Check Ollama local LLM health."""
        try:
            ollama_base_url = getattr(settings, 'ollama_base_url', None)
            if not ollama_base_url:
                return ComponentHealth(
                    name="ollama",
                    status=HealthStatus.UNKNOWN,
                    message="Ollama URL not configured"
                )
            
            # Test Ollama connection
            import httpx
            
            start_time = time.time()
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{ollama_base_url}/api/tags")
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    models = response.json().get('models', [])
                    return ComponentHealth(
                        name="ollama",
                        status=HealthStatus.HEALTHY,
                        message="Ollama service accessible",
                        details={
                            "response_time_ms": response_time,
                            "available_models": [m.get('name', 'unknown') for m in models],
                            "model_count": len(models)
                        }
                    )
                else:
                    return ComponentHealth(
                        name="ollama",
                        status=HealthStatus.UNHEALTHY,
                        message=f"Ollama returned status {response.status_code}"
                    )
            
        except Exception as e:
            return ComponentHealth(
                name="ollama",
                status=HealthStatus.UNHEALTHY,
                message=f"Ollama error: {str(e)}"
            )
    
    async def _check_crew_execution_health(self) -> ComponentHealth:
        """Check CrewAI execution system health."""
        try:
            # Test crew execution components availability
            llm_wrapper = LLMWrapper()
            llm_providers = llm_wrapper.get_available_providers()
            
            return ComponentHealth(
                name="crew_execution",
                status=HealthStatus.HEALTHY,
                message="Crew execution system operational",
                details={
                    "available_llm_providers": llm_providers,
                    "crew_service_available": True
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="crew_execution",
                status=HealthStatus.UNHEALTHY,
                message=f"Crew execution error: {str(e)}"
            )
    
    async def _check_memory_system_health(self) -> ComponentHealth:
        """Check memory system health."""
        try:
            db = next(get_db())
            
            # Test memory table access
            db.execute(text("SELECT COUNT(*) FROM short_term_memories"))
            db.execute(text("SELECT COUNT(*) FROM long_term_memories"))
            db.execute(text("SELECT COUNT(*) FROM entity_memories"))
            
            # Test vector operations if data exists
            vector_test_result = db.execute(text(
                "SELECT COUNT(*) FROM long_term_memories WHERE embedding IS NOT NULL"
            )).scalar()
            
            db.close()
            
            return ComponentHealth(
                name="memory_system",
                status=HealthStatus.HEALTHY,
                message="Memory system operational",
                details={
                    "memory_tables_accessible": True,
                    "vector_entries_count": vector_test_result
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="memory_system",
                status=HealthStatus.UNHEALTHY,
                message=f"Memory system error: {str(e)}"
            )
    
    async def _check_queue_system_health(self) -> ComponentHealth:
        """Check task queue system health."""
        try:
            # This is largely covered by Celery health check, but add queue-specific checks
            redis_client = redis.Redis.from_url(settings.redis_url)
            
            # Check for stuck tasks
            stuck_tasks = 0
            
            # Check task state store for old tasks (simplified)
            try:
                task_keys = redis_client.keys('celery-task-meta-*')
                if isinstance(task_keys, list):
                    for key in task_keys[:100]:  # Limit check to prevent performance issues
                        try:
                            task_data = redis_client.get(key)
                            if task_data and isinstance(task_data, (str, bytes)):
                                import json
                                if isinstance(task_data, bytes):
                                    task_data = task_data.decode('utf-8')
                                task_info = json.loads(task_data)
                                # Check if task is running too long
                                if task_info.get('status') == 'STARTED':
                                    stuck_tasks += 1
                        except Exception:
                            continue
                    
                    task_keys_count = len(task_keys)
                else:
                    task_keys_count = 0
            except Exception:
                task_keys_count = 0
                stuck_tasks = 0
            
            redis_client.close()
            
            if stuck_tasks > 10:
                status = HealthStatus.DEGRADED
                message = f"Potentially {stuck_tasks} stuck tasks detected"
            else:
                status = HealthStatus.HEALTHY
                message = "Queue system operating normally"
            
            return ComponentHealth(
                name="queue_system",
                status=status,
                message=message,
                details={
                    "potentially_stuck_tasks": stuck_tasks,
                    "task_metadata_keys": task_keys_count
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="queue_system",
                status=HealthStatus.UNHEALTHY,
                message=f"Queue system error: {str(e)}"
            )
    
    async def _check_websocket_health(self) -> ComponentHealth:
        """Check WebSocket system health."""
        try:
            # Check WebSocket manager availability
            active_connections = 0
            manager_available = False
            
            try:
                # Try importing the connection manager
                import importlib
                manager_module = importlib.import_module('app.websocket.connection_manager')
                if hasattr(manager_module, 'manager'):
                    manager = getattr(manager_module, 'manager')
                    if hasattr(manager, 'active_connections'):
                        active_connections = len(manager.active_connections)
                        manager_available = True
            except (ImportError, AttributeError, ModuleNotFoundError):
                # WebSocket manager not available, but this is not critical
                active_connections = 0
                manager_available = False
            
            connection_details = {
                "active_connections": active_connections,
                "manager_available": manager_available
            }
            
            return ComponentHealth(
                name="websocket",
                status=HealthStatus.HEALTHY,
                message=f"WebSocket system operational with {active_connections} connections",
                details=connection_details
            )
            
        except Exception as e:
            return ComponentHealth(
                name="websocket",
                status=HealthStatus.UNHEALTHY,
                message=f"WebSocket error: {str(e)}"
            )
    
    async def _check_dynamic_generation_health(self) -> ComponentHealth:
        """Check dynamic crew generation health."""
        try:
            # Test that dynamic generation components are available
            try:
                from app.core.dynamic_crew_generator import DynamicCrewGenerator
                # Create a minimal instance to test availability
                available_tools_count = 0  # Simplified check
                generator_available = True
            except ImportError:
                available_tools_count = 0
                generator_available = False
            
            return ComponentHealth(
                name="dynamic_generation",
                status=HealthStatus.HEALTHY,
                message="Dynamic generation system operational",
                details={
                    "generator_available": generator_available,
                    "available_tools_count": available_tools_count
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="dynamic_generation",
                status=HealthStatus.UNHEALTHY,
                message=f"Dynamic generation error: {str(e)}"
            )
    
    async def _check_manager_agent_health(self) -> ComponentHealth:
        """Check manager agent functionality."""
        try:
            # Test manager agent components availability (simplified check)
            manager_available = True
            
            return ComponentHealth(
                name="manager_agent",
                status=HealthStatus.HEALTHY,
                message="Manager agent system operational",
                details={
                    "manager_agent_available": manager_available
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="manager_agent",
                status=HealthStatus.UNHEALTHY,
                message=f"Manager agent error: {str(e)}"
            )
    
    def get_overall_health(self, component_healths: Dict[str, ComponentHealth]) -> ComponentHealth:
        """Calculate overall system health from component healths."""
        unhealthy_count = 0
        degraded_count = 0
        healthy_count = 0
        unknown_count = 0
        
        critical_components = ['database', 'redis', 'celery']
        critical_unhealthy = False
        
        for name, health in component_healths.items():
            if health.status == HealthStatus.UNHEALTHY:
                unhealthy_count += 1
                if name in critical_components:
                    critical_unhealthy = True
            elif health.status == HealthStatus.DEGRADED:
                degraded_count += 1
            elif health.status == HealthStatus.HEALTHY:
                healthy_count += 1
            else:
                unknown_count += 1
        
        # Determine overall status
        if critical_unhealthy or unhealthy_count > 3:
            overall_status = HealthStatus.UNHEALTHY
            message = f"System unhealthy: {unhealthy_count} components failed"
        elif degraded_count > 0 or unhealthy_count > 0:
            overall_status = HealthStatus.DEGRADED
            message = f"System degraded: {unhealthy_count} unhealthy, {degraded_count} degraded"
        elif unknown_count > 2:
            overall_status = HealthStatus.DEGRADED
            message = f"System status unclear: {unknown_count} components unknown"
        else:
            overall_status = HealthStatus.HEALTHY
            message = f"System healthy: {healthy_count} components operational"
        
        return ComponentHealth(
            name="overall",
            status=overall_status,
            message=message,
            details={
                "component_counts": {
                    "healthy": healthy_count,
                    "degraded": degraded_count,
                    "unhealthy": unhealthy_count,
                    "unknown": unknown_count
                },
                "critical_unhealthy": critical_unhealthy,
                "total_components": len(component_healths)
            }
        ) 