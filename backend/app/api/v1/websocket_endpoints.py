"""WebSocket API endpoints for real-time updates."""

import json
import logging
from typing import Dict, Any, Optional, Set
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from app.websocket.connection_manager import connection_manager
from app.websocket.events import EventType, WebSocketEvent

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/executions/{execution_id}")
async def websocket_execution_updates(websocket: WebSocket, execution_id: str):
    """WebSocket endpoint for execution-specific updates."""
    client_id = f"execution_{execution_id}_{id(websocket)}"
    subscriptions = {execution_id, f"execution_{execution_id}"}
    
    try:
        await connection_manager.connect(websocket, client_id, subscriptions)
        logger.info(f"Client connected to execution updates: {execution_id}")
        
        while True:
            try:
                # Receive messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                await connection_manager.handle_client_message(client_id, message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client {client_id}")
            except Exception as e:
                logger.error(f"Error handling message from client {client_id}: {e}")
                
    except Exception as e:
        logger.error(f"WebSocket connection error for execution {execution_id}: {e}")
    finally:
        connection_manager.disconnect(client_id)
        logger.info(f"Client disconnected from execution updates: {execution_id}")


@router.websocket("/ws/crews/{crew_id}")
async def websocket_crew_updates(websocket: WebSocket, crew_id: str):
    """WebSocket endpoint for crew-specific updates."""
    client_id = f"crew_{crew_id}_{id(websocket)}"
    subscriptions = {crew_id, f"crew_{crew_id}"}
    
    try:
        await connection_manager.connect(websocket, client_id, subscriptions)
        logger.info(f"Client connected to crew updates: {crew_id}")
        
        while True:
            try:
                # Receive messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                await connection_manager.handle_client_message(client_id, message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client {client_id}")
            except Exception as e:
                logger.error(f"Error handling message from client {client_id}: {e}")
                
    except Exception as e:
        logger.error(f"WebSocket connection error for crew {crew_id}: {e}")
    finally:
        connection_manager.disconnect(client_id)
        logger.info(f"Client disconnected from crew updates: {crew_id}")


@router.websocket("/ws/global")
async def websocket_global_updates(websocket: WebSocket):
    """WebSocket endpoint for system-wide updates."""
    client_id = f"global_{id(websocket)}"
    
    try:
        await connection_manager.connect(websocket, client_id)
        logger.info(f"Client connected to global updates")
        
        while True:
            try:
                # Receive messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                await connection_manager.handle_client_message(client_id, message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client {client_id}")
            except Exception as e:
                logger.error(f"Error handling message from client {client_id}: {e}")
                
    except Exception as e:
        logger.error(f"WebSocket connection error for global updates: {e}")
    finally:
        connection_manager.disconnect(client_id)
        logger.info(f"Client disconnected from global updates")


@router.websocket("/ws/metrics")
async def websocket_metrics_stream(websocket: WebSocket):
    """WebSocket endpoint for real-time performance metrics."""
    client_id = f"metrics_{id(websocket)}"
    subscriptions = {"metrics", "performance", "system_performance"}
    
    try:
        await connection_manager.connect(websocket, client_id, subscriptions)
        logger.info(f"Client connected to metrics stream")
        
        while True:
            try:
                # Receive messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                await connection_manager.handle_client_message(client_id, message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client {client_id}")
            except Exception as e:
                logger.error(f"Error handling message from client {client_id}: {e}")
                
    except Exception as e:
        logger.error(f"WebSocket connection error for metrics stream: {e}")
    finally:
        connection_manager.disconnect(client_id)
        logger.info(f"Client disconnected from metrics stream")


@router.websocket("/ws/custom")
async def websocket_custom_subscriptions(websocket: WebSocket):
    """WebSocket endpoint with custom subscription management."""
    client_id = f"custom_{id(websocket)}"
    
    try:
        await connection_manager.connect(websocket, client_id)
        logger.info(f"Client connected with custom subscriptions")
        
        while True:
            try:
                # Receive messages from client
                data = await websocket.receive_text()
                message = json.loads(data)
                await connection_manager.handle_client_message(client_id, message)
                
            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received from client {client_id}")
            except Exception as e:
                logger.error(f"Error handling message from client {client_id}: {e}")
                
    except Exception as e:
        logger.error(f"WebSocket connection error for custom subscriptions: {e}")
    finally:
        connection_manager.disconnect(client_id)
        logger.info(f"Client disconnected from custom subscriptions")


# HTTP endpoints for WebSocket management

@router.get("/connections")
async def get_websocket_connections():
    """Get active WebSocket connection statistics."""
    try:
        stats = connection_manager.get_connection_stats()
        return {
            "status": "success",
            "data": {
                "active_connections": stats["total_connections"],
                "subscription_counts": stats["subscription_counts"],
                "average_connection_duration": stats["average_connection_duration_seconds"],
                "uptime_statistics": {
                    "connections": stats["total_connections"],
                    "average_duration_seconds": stats["average_connection_duration_seconds"]
                }
            }
        }
    except Exception as e:
        logger.error(f"Error getting connection statistics: {e}")
        raise HTTPException(status_code=500, detail="Failed to get connection statistics")


@router.get("/connections/{client_id}")
async def get_client_connection_info(client_id: str):
    """Get information about a specific client connection."""
    try:
        if not connection_manager.is_connected(client_id):
            raise HTTPException(status_code=404, detail="Client not found")
        
        subscriptions = connection_manager.get_client_subscriptions(client_id)
        connection_info = connection_manager.active_connections[client_id]
        
        return {
            "status": "success",
            "data": {
                "client_id": client_id,
                "connected": True,
                "subscriptions": list(subscriptions) if subscriptions else [],
                "connected_at": connection_info.connected_at.isoformat(),
                "last_heartbeat": connection_info.last_heartbeat.isoformat() if connection_info.last_heartbeat else None
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting client connection info: {e}")
        raise HTTPException(status_code=500, detail="Failed to get client connection info")


@router.post("/broadcast")
async def broadcast_message_to_all(message: Dict[str, Any]):
    """Broadcast a message to all connected WebSocket clients."""
    try:
        # Create a system event for the broadcast
        event = WebSocketEvent.create_system_event(
            event_type=EventType.SYSTEM_ALERT,
            component="admin_broadcast",
            message=message.get("message", ""),
            metrics=message.get("data", {})
        )
        
        await connection_manager.broadcast_event(event)
        
        return {
            "status": "success",
            "message": "Message broadcasted to all connected clients",
            "recipients": connection_manager.get_connection_count()
        }
    except Exception as e:
        logger.error(f"Error broadcasting message: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast message")


@router.post("/broadcast/{subscription}")
async def broadcast_message_to_subscription(
    subscription: str,
    message: Dict[str, Any]
):
    """Broadcast a message to clients subscribed to a specific topic."""
    try:
        # Create a system event for the targeted broadcast
        event = WebSocketEvent.create_system_event(
            event_type=EventType.SYSTEM_ALERT,
            component="targeted_broadcast",
            message=message.get("message", ""),
            metrics=message.get("data", {}),
            target=subscription
        )
        
        await connection_manager.send_event_to_subscribed(event, subscription)
        
        subscribers = connection_manager.get_subscribed_clients(subscription)
        
        return {
            "status": "success",
            "message": f"Message broadcasted to subscribers of '{subscription}'",
            "subscription": subscription,
            "recipients": len(subscribers),
            "client_ids": subscribers
        }
    except Exception as e:
        logger.error(f"Error broadcasting to subscription {subscription}: {e}")
        raise HTTPException(status_code=500, detail="Failed to broadcast to subscription")


@router.post("/disconnect/{client_id}")
async def disconnect_client(client_id: str):
    """Administratively disconnect a specific client."""
    try:
        if not connection_manager.is_connected(client_id):
            raise HTTPException(status_code=404, detail="Client not found")
        
        connection_manager.disconnect(client_id)
        
        return {
            "status": "success",
            "message": f"Client {client_id} disconnected successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error disconnecting client {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to disconnect client")


@router.delete("/connections")
async def cleanup_stale_connections(max_idle_minutes: int = 30):
    """Clean up stale WebSocket connections."""
    try:
        await connection_manager.cleanup_stale_connections(max_idle_minutes)
        
        return {
            "status": "success",
            "message": f"Cleaned up stale connections (idle > {max_idle_minutes} minutes)",
            "remaining_connections": connection_manager.get_connection_count()
        }
    except Exception as e:
        logger.error(f"Error cleaning up stale connections: {e}")
        raise HTTPException(status_code=500, detail="Failed to cleanup stale connections")


@router.get("/health")
async def websocket_health_check():
    """Health check endpoint for WebSocket service."""
    try:
        stats = connection_manager.get_connection_stats()
        
        return {
            "status": "healthy",
            "service": "websocket",
            "active_connections": stats["total_connections"],
            "timestamp": WebSocketEvent(type=EventType.SYSTEM_STATUS, data={}).timestamp
        }
    except Exception as e:
        logger.error(f"WebSocket health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "websocket",
                "error": str(e)
            }
        ) 