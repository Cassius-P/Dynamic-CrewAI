"""Tests for WebSocket connection manager."""

import pytest
import json
from unittest.mock import Mock, AsyncMock
from fastapi import WebSocket
from app.websocket.connection_manager import ConnectionManager, WebSocketConnection
from app.websocket.events import EventType, WebSocketEvent


@pytest.fixture
def connection_manager():
    """Create a connection manager instance for testing."""
    return ConnectionManager()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    websocket = Mock(spec=WebSocket)
    websocket.send_text = AsyncMock()
    websocket.send_json = AsyncMock()
    websocket.close = AsyncMock()
    return websocket


class TestConnectionManager:
    """Test cases for WebSocket connection manager."""

    @pytest.mark.asyncio
    async def test_connect_new_client(self, connection_manager, mock_websocket):
        """Test connecting a new WebSocket client."""
        client_id = "test_client_1"
        
        await connection_manager.connect(mock_websocket, client_id)
        
        assert client_id in connection_manager.active_connections
        assert connection_manager.active_connections[client_id].websocket == mock_websocket
        assert connection_manager.get_connection_count() == 1
        
        # Should send connection established event
        assert mock_websocket.send_json.call_count == 1
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "connection.established"

    @pytest.mark.asyncio
    async def test_disconnect_client(self, connection_manager, mock_websocket):
        """Test disconnecting a WebSocket client."""
        client_id = "test_client_1"
        
        await connection_manager.connect(mock_websocket, client_id)
        connection_manager.disconnect(client_id)
        
        assert client_id not in connection_manager.active_connections
        assert connection_manager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_send_personal_message(self, connection_manager, mock_websocket):
        """Test sending a personal message to a specific client."""
        client_id = "test_client_1"
        message = "Hello, client!"
        
        await connection_manager.connect(mock_websocket, client_id)
        await connection_manager.send_personal_message(message, client_id)
        
        mock_websocket.send_text.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_send_personal_json(self, connection_manager, mock_websocket):
        """Test sending JSON data to a specific client."""
        client_id = "test_client_1"
        data = {"type": "test", "message": "Hello"}
        
        await connection_manager.connect(mock_websocket, client_id)
        # Reset mock to ignore connection established event
        mock_websocket.send_json.reset_mock()
        
        await connection_manager.send_personal_json(data, client_id)
        
        mock_websocket.send_json.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_broadcast_message(self, connection_manager):
        """Test broadcasting a message to all connected clients."""
        # Create multiple mock connections
        clients = []
        for i in range(3):
            mock_ws = Mock(spec=WebSocket)
            mock_ws.send_text = AsyncMock()
            mock_ws.send_json = AsyncMock()
            client_id = f"client_{i}"
            await connection_manager.connect(mock_ws, client_id)
            clients.append((client_id, mock_ws))
        
        message = "Broadcast message"
        await connection_manager.broadcast(message)
        
        # Verify all clients received the message
        for client_id, mock_ws in clients:
            mock_ws.send_text.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_json(self, connection_manager):
        """Test broadcasting JSON data to all connected clients."""
        # Create multiple mock connections
        clients = []
        for i in range(3):
            mock_ws = Mock(spec=WebSocket)
            mock_ws.send_text = AsyncMock()
            mock_ws.send_json = AsyncMock()
            client_id = f"client_{i}"
            await connection_manager.connect(mock_ws, client_id)
            # Reset mock to ignore connection established event
            mock_ws.send_json.reset_mock()
            clients.append((client_id, mock_ws))
        
        data = {"type": "broadcast", "message": "Hello all"}
        await connection_manager.broadcast_json(data)
        
        # Verify all clients received the JSON data
        for client_id, mock_ws in clients:
            mock_ws.send_json.assert_called_once_with(data)

    @pytest.mark.asyncio
    async def test_send_to_nonexistent_client(self, connection_manager):
        """Test sending message to a non-existent client."""
        # Should not raise an exception
        await connection_manager.send_personal_message("test", "nonexistent_client")
        await connection_manager.send_personal_json({"test": "data"}, "nonexistent_client")

    @pytest.mark.asyncio
    async def test_connection_count(self, connection_manager):
        """Test connection count tracking."""
        assert connection_manager.get_connection_count() == 0
        
        # Add multiple connections
        for i in range(5):
            mock_ws = Mock(spec=WebSocket)
            mock_ws.send_json = AsyncMock()
            await connection_manager.connect(mock_ws, f"client_{i}")
        
        assert connection_manager.get_connection_count() == 5
        
        # Remove some connections
        for i in range(3):
            connection_manager.disconnect(f"client_{i}")
        
        assert connection_manager.get_connection_count() == 2

    @pytest.mark.asyncio
    async def test_get_all_client_ids(self, connection_manager):
        """Test getting all connected client IDs."""
        client_ids = ["client_1", "client_2", "client_3"]
        
        for client_id in client_ids:
            mock_ws = Mock(spec=WebSocket)
            mock_ws.send_json = AsyncMock()
            await connection_manager.connect(mock_ws, client_id)
        
        connected_ids = connection_manager.get_all_client_ids()
        assert set(connected_ids) == set(client_ids)

    @pytest.mark.asyncio
    async def test_is_connected(self, connection_manager, mock_websocket):
        """Test checking if a client is connected."""
        client_id = "test_client"
        
        assert not connection_manager.is_connected(client_id)
        
        await connection_manager.connect(mock_websocket, client_id)
        assert connection_manager.is_connected(client_id)
        
        connection_manager.disconnect(client_id)
        assert not connection_manager.is_connected(client_id)

    @pytest.mark.asyncio
    async def test_send_event(self, connection_manager, mock_websocket):
        """Test sending WebSocket events to clients."""
        client_id = "test_client"
        await connection_manager.connect(mock_websocket, client_id)
        # Reset mock to ignore connection established event
        mock_websocket.send_json.reset_mock()
        
        event = WebSocketEvent(
            type=EventType.EXECUTION_STARTED,
            data={"execution_id": "exec_1", "crew_id": "crew_1"},
            timestamp="2024-01-01T00:00:00Z"
        )
        
        await connection_manager.send_event(event, client_id)
        
        expected_data = {
            "type": "execution.started",
            "data": {"execution_id": "exec_1", "crew_id": "crew_1"},
            "timestamp": "2024-01-01T00:00:00Z"
        }
        mock_websocket.send_json.assert_called_once_with(expected_data)

    @pytest.mark.asyncio
    async def test_broadcast_event(self, connection_manager):
        """Test broadcasting events to all connected clients."""
        # Create multiple connections
        clients = []
        for i in range(3):
            mock_ws = Mock(spec=WebSocket)
            mock_ws.send_json = AsyncMock()
            client_id = f"client_{i}"
            await connection_manager.connect(mock_ws, client_id)
            # Reset mock to ignore connection established event
            mock_ws.send_json.reset_mock()
            clients.append((client_id, mock_ws))
        
        event = WebSocketEvent(
            type=EventType.SYSTEM_STATUS,
            data={"status": "healthy"},
            timestamp="2024-01-01T00:00:00Z"
        )
        
        await connection_manager.broadcast_event(event)
        
        expected_data = {
            "type": "system.status",
            "data": {"status": "healthy"},
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
        for client_id, mock_ws in clients:
            mock_ws.send_json.assert_called_once_with(expected_data)

    @pytest.mark.asyncio
    async def test_connection_with_subscriptions(self, connection_manager, mock_websocket):
        """Test connection with subscription filters."""
        client_id = "test_client"
        subscriptions = {"execution_1", "crew_1"}
        
        await connection_manager.connect(mock_websocket, client_id, subscriptions)
        
        connection = connection_manager.active_connections[client_id]
        assert connection.subscriptions == subscriptions

    @pytest.mark.asyncio
    async def test_update_subscriptions(self, connection_manager, mock_websocket):
        """Test updating client subscriptions."""
        client_id = "test_client"
        initial_subscriptions = {"execution_1"}
        new_subscriptions = {"execution_1", "execution_2", "crew_1"}
        
        await connection_manager.connect(mock_websocket, client_id, initial_subscriptions)
        connection_manager.update_subscriptions(client_id, new_subscriptions)
        
        connection = connection_manager.active_connections[client_id]
        assert connection.subscriptions == new_subscriptions

    @pytest.mark.asyncio
    async def test_get_subscribed_clients(self, connection_manager):
        """Test getting clients subscribed to specific topics."""
        # Create connections with different subscriptions
        clients_data = [
            ("client_1", {"execution_1", "crew_1"}),
            ("client_2", {"execution_1"}),
            ("client_3", {"crew_2"}),
        ]
        
        for client_id, subscriptions in clients_data:
            mock_ws = Mock(spec=WebSocket)
            mock_ws.send_json = AsyncMock()
            await connection_manager.connect(mock_ws, client_id, subscriptions)
        
        # Test filtering by subscription
        execution_1_clients = connection_manager.get_subscribed_clients("execution_1")
        assert set(execution_1_clients) == {"client_1", "client_2"}
        
        crew_1_clients = connection_manager.get_subscribed_clients("crew_1")
        assert crew_1_clients == ["client_1"]
        
        crew_2_clients = connection_manager.get_subscribed_clients("crew_2")
        assert crew_2_clients == ["client_3"]


class TestWebSocketConnection:
    """Test cases for WebSocketConnection model."""

    def test_websocket_connection_creation(self, mock_websocket):
        """Test creating a WebSocketConnection instance."""
        client_id = "test_client"
        subscriptions = {"execution_1", "crew_1"}
        
        connection = WebSocketConnection(
            websocket=mock_websocket,
            client_id=client_id,
            subscriptions=subscriptions
        )
        
        assert connection.websocket == mock_websocket
        assert connection.client_id == client_id
        assert connection.subscriptions == subscriptions
        assert connection.connected_at is not None

    def test_websocket_connection_default_subscriptions(self, mock_websocket):
        """Test WebSocketConnection with default empty subscriptions."""
        client_id = "test_client"
        
        connection = WebSocketConnection(
            websocket=mock_websocket,
            client_id=client_id
        )
        
        assert connection.subscriptions == set()

    def test_is_subscribed_to(self, mock_websocket):
        """Test subscription checking."""
        subscriptions = {"execution_1", "crew_1"}
        connection = WebSocketConnection(
            websocket=mock_websocket,
            client_id="test_client",
            subscriptions=subscriptions
        )
        
        assert connection.is_subscribed_to("execution_1")
        assert connection.is_subscribed_to("crew_1")
        assert not connection.is_subscribed_to("execution_2")
        assert not connection.is_subscribed_to("nonexistent")

    def test_add_subscription(self, mock_websocket):
        """Test adding a new subscription."""
        connection = WebSocketConnection(
            websocket=mock_websocket,
            client_id="test_client",
            subscriptions={"execution_1"}
        )
        
        connection.add_subscription("crew_1")
        assert "crew_1" in connection.subscriptions
        assert len(connection.subscriptions) == 2

    def test_remove_subscription(self, mock_websocket):
        """Test removing a subscription."""
        connection = WebSocketConnection(
            websocket=mock_websocket,
            client_id="test_client",
            subscriptions={"execution_1", "crew_1"}
        )
        
        connection.remove_subscription("execution_1")
        assert "execution_1" not in connection.subscriptions
        assert "crew_1" in connection.subscriptions
        assert len(connection.subscriptions) == 1

    def test_remove_nonexistent_subscription(self, mock_websocket):
        """Test removing a non-existent subscription."""
        connection = WebSocketConnection(
            websocket=mock_websocket,
            client_id="test_client",
            subscriptions={"execution_1"}
        )
        
        # Should not raise an exception
        connection.remove_subscription("nonexistent")
        assert "execution_1" in connection.subscriptions
        assert len(connection.subscriptions) == 1 