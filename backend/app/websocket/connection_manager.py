"""WebSocket connection manager for real-time updates."""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect
from dataclasses import dataclass
from app.websocket.events import WebSocketEvent, EventRouter, EventFilter, EventType

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConnection:
    """Represents an active WebSocket connection."""
    
    websocket: WebSocket
    client_id: str
    subscriptions: Set[str]
    connected_at: datetime
    last_heartbeat: Optional[datetime] = None
    
    def __init__(self, websocket: WebSocket, client_id: str, subscriptions: Optional[Set[str]] = None):
        self.websocket = websocket
        self.client_id = client_id
        self.subscriptions = subscriptions or set()
        self.connected_at = datetime.utcnow()
        self.last_heartbeat = None
    
    def is_subscribed_to(self, topic: str) -> bool:
        """Check if connection is subscribed to a specific topic."""
        return topic in self.subscriptions
    
    def add_subscription(self, topic: str):
        """Add a subscription topic."""
        self.subscriptions.add(topic)
    
    def remove_subscription(self, topic: str):
        """Remove a subscription topic."""
        self.subscriptions.discard(topic)
    
    def update_heartbeat(self):
        """Update the last heartbeat timestamp."""
        self.last_heartbeat = datetime.utcnow()


class ConnectionManager:
    """Manages WebSocket connections and event broadcasting."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocketConnection] = {}
        self.event_router = EventRouter()
        self._connection_lock = asyncio.Lock()
        
    async def connect(self, websocket: WebSocket, client_id: str, subscriptions: Optional[Set[str]] = None):
        """Connect a new WebSocket client."""
        await websocket.accept()
        
        async with self._connection_lock:
            connection = WebSocketConnection(
                websocket=websocket,
                client_id=client_id,
                subscriptions=subscriptions
            )
            self.active_connections[client_id] = connection
            
        logger.info(f"WebSocket client {client_id} connected with subscriptions: {subscriptions}")
        
        # Send connection established event
        event = WebSocketEvent.create_system_event(
            event_type=EventType.CONNECTION_ESTABLISHED,
            component="websocket",
            message=f"Client {client_id} connected"
        )
        await self.send_event(event, client_id)
    
    def disconnect(self, client_id: str):
        """Disconnect a WebSocket client."""
        if client_id in self.active_connections:
            connection = self.active_connections.pop(client_id)
            self.event_router.remove_filter(client_id)
            logger.info(f"WebSocket client {client_id} disconnected")
    
    async def send_personal_message(self, message: str, client_id: str):
        """Send a text message to a specific client."""
        if client_id in self.active_connections:
            try:
                connection = self.active_connections[client_id]
                await connection.websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error sending message to client {client_id}: {e}")
                self.disconnect(client_id)
    
    async def send_personal_json(self, data: Dict[str, Any], client_id: str):
        """Send JSON data to a specific client."""
        if client_id in self.active_connections:
            try:
                connection = self.active_connections[client_id]
                await connection.websocket.send_json(data)
            except Exception as e:
                logger.error(f"Error sending JSON to client {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: str):
        """Broadcast a text message to all connected clients."""
        disconnected_clients = []
        
        for client_id, connection in self.active_connections.items():
            try:
                await connection.websocket.send_text(message)
            except Exception as e:
                logger.error(f"Error broadcasting to client {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def broadcast_json(self, data: Dict[str, Any]):
        """Broadcast JSON data to all connected clients."""
        disconnected_clients = []
        
        for client_id, connection in self.active_connections.items():
            try:
                await connection.websocket.send_json(data)
            except Exception as e:
                logger.error(f"Error broadcasting JSON to client {client_id}: {e}")
                disconnected_clients.append(client_id)
        
        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)
    
    async def send_event(self, event: WebSocketEvent, client_id: str):
        """Send an event to a specific client."""
        if client_id in self.active_connections:
            event_data = event.to_json_dict()
            await self.send_personal_json(event_data, client_id)
    
    async def broadcast_event(self, event: WebSocketEvent):
        """Broadcast an event to all connected clients."""
        event_data = event.to_json_dict()
        await self.broadcast_json(event_data)
    
    async def send_event_to_subscribed(self, event: WebSocketEvent, topic: str):
        """Send an event to clients subscribed to a specific topic."""
        subscribed_clients = self.get_subscribed_clients(topic)
        
        for client_id in subscribed_clients:
            await self.send_event(event, client_id)
    
    async def send_filtered_event(self, event: WebSocketEvent):
        """Send an event to clients based on event router filters."""
        all_client_ids = list(self.active_connections.keys())
        target_clients = self.event_router.get_target_clients(event, all_client_ids)
        
        for client_id in target_clients:
            await self.send_event(event, client_id)
    
    def get_connection_count(self) -> int:
        """Get the number of active connections."""
        return len(self.active_connections)
    
    def get_all_client_ids(self) -> List[str]:
        """Get all connected client IDs."""
        return list(self.active_connections.keys())
    
    def is_connected(self, client_id: str) -> bool:
        """Check if a client is currently connected."""
        return client_id in self.active_connections
    
    def get_subscribed_clients(self, topic: str) -> List[str]:
        """Get clients subscribed to a specific topic."""
        subscribed_clients = []
        
        for client_id, connection in self.active_connections.items():
            if connection.is_subscribed_to(topic):
                subscribed_clients.append(client_id)
        
        return subscribed_clients
    
    def update_subscriptions(self, client_id: str, subscriptions: Set[str]):
        """Update subscriptions for a client."""
        if client_id in self.active_connections:
            self.active_connections[client_id].subscriptions = subscriptions
            logger.info(f"Updated subscriptions for client {client_id}: {subscriptions}")
    
    def add_subscription(self, client_id: str, topic: str):
        """Add a subscription for a client."""
        if client_id in self.active_connections:
            self.active_connections[client_id].add_subscription(topic)
            logger.info(f"Added subscription {topic} for client {client_id}")
    
    def remove_subscription(self, client_id: str, topic: str):
        """Remove a subscription for a client."""
        if client_id in self.active_connections:
            self.active_connections[client_id].remove_subscription(topic)
            logger.info(f"Removed subscription {topic} for client {client_id}")
    
    def get_client_subscriptions(self, client_id: str) -> Optional[Set[str]]:
        """Get subscriptions for a specific client."""
        if client_id in self.active_connections:
            return self.active_connections[client_id].subscriptions
        return None
    
    def add_event_filter(self, client_id: str, event_filter: EventFilter):
        """Add event filter for a client."""
        self.event_router.add_filter(client_id, event_filter)
    
    def remove_event_filter(self, client_id: str):
        """Remove event filter for a client."""
        self.event_router.remove_filter(client_id)
    
    async def handle_client_message(self, client_id: str, message: Dict[str, Any]):
        """Handle incoming message from a WebSocket client."""
        try:
            message_type = message.get("type")
            
            if message_type == "heartbeat":
                await self._handle_heartbeat(client_id)
            elif message_type == "subscribe":
                await self._handle_subscription_request(client_id, message)
            elif message_type == "unsubscribe":
                await self._handle_unsubscription_request(client_id, message)
            else:
                logger.warning(f"Unknown message type from client {client_id}: {message_type}")
                
        except Exception as e:
            logger.error(f"Error handling message from client {client_id}: {e}")
    
    async def _handle_heartbeat(self, client_id: str):
        """Handle heartbeat message from client."""
        if client_id in self.active_connections:
            self.active_connections[client_id].update_heartbeat()
            
            # Send heartbeat response
            response = {
                "type": "heartbeat_response",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
            await self.send_personal_json(response, client_id)
    
    async def _handle_subscription_request(self, client_id: str, message: Dict[str, Any]):
        """Handle subscription request from client."""
        topics = message.get("topics", [])
        
        for topic in topics:
            self.add_subscription(client_id, topic)
        
        # Send confirmation
        response = {
            "type": "subscription_confirmed",
            "topics": topics,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        await self.send_personal_json(response, client_id)
    
    async def _handle_unsubscription_request(self, client_id: str, message: Dict[str, Any]):
        """Handle unsubscription request from client."""
        topics = message.get("topics", [])
        
        for topic in topics:
            self.remove_subscription(client_id, topic)
        
        # Send confirmation
        response = {
            "type": "unsubscription_confirmed",
            "topics": topics,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        await self.send_personal_json(response, client_id)
    
    async def cleanup_stale_connections(self, max_idle_minutes: int = 30):
        """Clean up stale connections that haven't sent heartbeat."""
        now = datetime.utcnow()
        stale_clients = []
        
        for client_id, connection in self.active_connections.items():
            if connection.last_heartbeat:
                idle_time = (now - connection.last_heartbeat).total_seconds() / 60
                if idle_time > max_idle_minutes:
                    stale_clients.append(client_id)
        
        for client_id in stale_clients:
            logger.info(f"Cleaning up stale connection for client {client_id}")
            self.disconnect(client_id)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get statistics about active connections."""
        total_connections = len(self.active_connections)
        
        # Count subscriptions
        subscription_counts = {}
        for connection in self.active_connections.values():
            for topic in connection.subscriptions:
                subscription_counts[topic] = subscription_counts.get(topic, 0) + 1
        
        # Calculate connection durations
        now = datetime.utcnow()
        connection_durations = []
        for connection in self.active_connections.values():
            duration = (now - connection.connected_at).total_seconds()
            connection_durations.append(duration)
        
        avg_duration = sum(connection_durations) / len(connection_durations) if connection_durations else 0
        
        return {
            "total_connections": total_connections,
            "subscription_counts": subscription_counts,
            "average_connection_duration_seconds": avg_duration,
            "connection_durations": connection_durations
        }


# Global connection manager instance
connection_manager = ConnectionManager() 