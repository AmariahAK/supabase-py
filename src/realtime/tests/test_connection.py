import asyncio
import datetime
import os
from typing import AsyncIterator

import aiohttp
import pytest
from dotenv import load_dotenv
from pydantic import BaseModel
from websockets import broadcast

from realtime import (
    RealtimeChannel,
    RealtimeClient,
    RealtimePostgresChangesListenEvent,
    RealtimeSubscribeStates,
)
from realtime.channel import RealtimeChannelOptions
from realtime.client import connect_once
from realtime.message import (
    BroadcastMessage,
    Message,
    PostgresChangesMessage,
    SystemMessage,
)
from realtime.types import DEFAULT_HEARTBEAT_INTERVAL, DEFAULT_TIMEOUT, ChannelEvents

load_dotenv()


URL = os.getenv("SUPABASE_URL") or "http://127.0.0.1:54321"
PUBLISHABLE_KEY = (
    os.getenv("SUPABASE_PUBLISHABLE_KEY")
    or "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZS1kZW1vIiwicm9sZSI6ImFub24iLCJleHAiOjE5ODM4MTI5OTZ9.CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0"
)


@pytest.fixture
async def socket() -> AsyncIterator[RealtimeClient]:
    url = f"{URL}/realtime/v1"
    key = PUBLISHABLE_KEY
    async with connect_once(url, key) as client:
        yield client


class SignupMessageResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    expires_at: int
    refresh_token: str


async def access_token() -> str:
    url = f"{URL}/auth/v1/signup"
    headers = {"apikey": PUBLISHABLE_KEY, "Content-Type": "application/json"}
    data = {
        "email": os.getenv("SUPABASE_TEST_EMAIL")
        or f"test_{datetime.datetime.now().strftime('%Y%m%d%H%M%S.%f')}@example.com",
        "password": os.getenv("SUPABASE_TEST_PASSWORD") or "test.123",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=data) as response:
            if response.status == 200:
                response_content = await response.read()
                signup_response = SignupMessageResponse.model_validate_json(
                    response_content
                )
                return signup_response.access_token
            else:
                raise Exception(
                    f"Failed to get access token. Status: {response.status}"
                )


def test_init_client():
    client = RealtimeClient(URL, PUBLISHABLE_KEY)

    assert client is not None
    assert client.url.startswith("ws://") or client.url.startswith("wss://")
    assert "/websocket" in client.url
    assert client.url.split("apikey=")[1] == PUBLISHABLE_KEY
    assert client.auto_reconnect is True
    assert client.params == {}
    assert client.hb_interval == DEFAULT_HEARTBEAT_INTERVAL
    assert client.max_retries == 5
    assert client.initial_backoff == 1.0
    assert client.timeout == DEFAULT_TIMEOUT


@pytest.mark.asyncio
async def test_broadcast_events(socket: RealtimeClient):
    channel_options = RealtimeChannelOptions() \
        .broadcast(listen_self=True, ack=True) \
        .presence(enabled=True)
    async with socket.channel(
        "test-broadcast",
        params=channel_options,
    ) as chan:
        # Send 3 broadcast events
        for i in range(3):
            await chan.send_broadcast("test-event", {"message": f"Event {i + 1}"})

        message_stream = chan.messages
        msg1 = await message_stream.__anext__()
        assert isinstance(msg1, BroadcastMessage)
        msg2 = await message_stream.__anext__()
        assert isinstance(msg2, BroadcastMessage)
        msg3 = await message_stream.__anext__()
        assert isinstance(msg3, BroadcastMessage)
        assert msg1.payload["event"] == "test-event"
        assert msg2.payload["event"] == "test-event"
        assert msg3.payload["event"] == "test-event"
        assert msg1.payload["payload"]["message"] == "Event 1"
        assert msg2.payload["payload"]["message"] == "Event 2"
        assert msg3.payload["payload"]["message"] == "Event 3"


@pytest.mark.asyncio
async def test_postgrest_changes(socket: RealtimeClient):
    token = await access_token()
    await socket.set_auth(token)

    channel_options = RealtimeChannelOptions() \
        .postgres_changes(RealtimePostgresChangesListenEvent.All, table="todos") \
        .postgres_changes(RealtimePostgresChangesListenEvent.Insert, table="todos") \
        .postgres_changes(RealtimePostgresChangesListenEvent.Update, table="todos") \
        .postgres_changes(RealtimePostgresChangesListenEvent.Delete, table="todos")

    async with socket.channel("test-postgres-changes", channel_options) as chan:
        message_stream = chan.messages
        async with asyncio.timeout(5):
            system_msg = await message_stream.__anext__()
            assert isinstance(system_msg, SystemMessage)
            assert system_msg.payload.status == 'ok'
            created_todo_id = await create_todo(
                token, {"description": "Test todo", "is_completed": False}
            )
            
            insert = await message_stream.__anext__()
            assert isinstance(insert, PostgresChangesMessage)
            
            await update_todo(
                token, created_todo_id, {"description": "Updated todo", "is_completed": True}
            )
            update = await message_stream.__anext__()
            assert isinstance(update, PostgresChangesMessage)
           
            await delete_todo(token, created_todo_id)
            delete = await message_stream.__anext__()
            assert isinstance(delete, PostgresChangesMessage)

    assert insert.payload["data"]["record"] is not None
    assert insert.payload["data"]["record"]["id"] == created_todo_id
    assert insert.payload["data"]["record"]["description"] == "Test todo"
    assert not insert.payload["data"]["record"]["is_completed"]

    assert update.payload["data"]["record"] is not None
    assert update.payload["data"]["record"]["id"] == created_todo_id
    assert update.payload["data"]["record"]["description"] == "Updated todo"
    assert update.payload["data"]["record"]["is_completed"]

    assert delete.payload["data"]["old_record"]["id"] == created_todo_id

    # assert received_events["insert"] == [insert]
    # assert received_events["update"] == [update]
    # assert received_events["delete"] == [delete]

@pytest.mark.asyncio
async def test_postgrest_changes_on_different_tables(socket: RealtimeClient):
    token = await access_token()

    await socket.set_auth(token)

    channel_options = RealtimeChannelOptions() \
        .postgres_changes(RealtimePostgresChangesListenEvent.Insert, table="todos") \
        .postgres_changes(RealtimePostgresChangesListenEvent.Insert, table="messages") \

    async with socket.channel("test-postgres-changes", params=channel_options) as channel:
        message_stream = channel.messages
        async with asyncio.timeout(5):
            system_msg = await message_stream.__anext__()
            assert isinstance(system_msg, SystemMessage)
            assert system_msg.payload.status == 'ok'
            created_todo_id = await create_todo(
                token, {"description": "Test todo", "is_completed": False}
            )
            insert_todo = await message_stream.__anext__()
            assert isinstance(insert_todo, PostgresChangesMessage)
            created_message_id = await create_message(
                token, {"title": "Test message", "message": "This is a test message"}
            )
            insert_message = await message_stream.__anext__()
            assert isinstance(insert_message, PostgresChangesMessage)

    assert insert_todo.payload["data"]["record"] is not None
    assert insert_todo.payload["data"]["record"]["id"] == created_todo_id
    assert insert_todo.payload["data"]["record"]["description"] == "Test todo"
    assert insert_todo.payload["data"]["record"]["is_completed"] is False

    assert insert_message.payload["data"]["record"] is not None
    assert insert_message.payload["data"]["record"]["id"] == created_message_id
    assert insert_message.payload["data"]["record"]["title"] == "Test message"
    assert insert_message.payload["data"]["record"]["message"] == "This is a test message"

class CreateTodoResponse(BaseModel):
    id: str


async def create_todo(access_token: str, todo: dict) -> str:
    url = f"{URL}/rest/v1/todos?select=id"
    headers = {
        "apikey": PUBLISHABLE_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.pgrst.object+json",
        "Prefer": "return=representation",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=todo) as response:
            if response.status == 201:
                response_content = await response.read()
                create_todo_response = CreateTodoResponse.model_validate_json(
                    response_content
                )
                return create_todo_response.id
            else:
                raise Exception(f"Failed to create todo. Status: {response.status}")


async def update_todo(access_token: str, id: str, todo: dict):
    url = f"{URL}/rest/v1/todos?id=eq.{id}"
    headers = {
        "apikey": PUBLISHABLE_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.patch(url, headers=headers, json=todo) as response:
            if response.status != 204:
                raise Exception(f"Failed to update todo. Status: {response.status}")


class CreateMsgResponse(BaseModel):
    id: int


async def create_message(access_token: str, message: dict) -> int:
    url = f"{URL}/rest/v1/messages?select=id"
    headers = {
        "apikey": PUBLISHABLE_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.pgrst.object+json",
        "Prefer": "return=representation",
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=message) as response:
            if response.status == 201:
                response_content = await response.read()
                create_msg_response = CreateMsgResponse.model_validate_json(
                    response_content
                )
                return create_msg_response.id
            else:
                raise Exception(f"Failed to create message. Status: {response.status}")


async def delete_todo(access_token: str, id: str):
    url = f"{URL}/rest/v1/todos?id=eq.{id}"
    headers = {
        "apikey": PUBLISHABLE_KEY,
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    async with aiohttp.ClientSession() as session:
        async with session.delete(url, headers=headers) as response:
            if response.status != 204:
                raise Exception(f"Failed to delete todo. Status: {response.status}")

@pytest.mark.asyncio
async def test_subscribe_to_private_channel_with_broadcast_replay(
    socket: RealtimeClient,
):
    """Test that channel subscription sends correct payload with broadcast replay configuration."""
    token = await access_token()

    await socket.set_auth(token)

    messages = 10

    # Calculate replay timestamp
    ten_mins_ago = datetime.datetime.now() - datetime.timedelta(minutes=10)
    ten_mins_ago_ms = int(ten_mins_ago.timestamp() * 1000)

    channel_options = RealtimeChannelOptions() \
        .private(True) \
        .presence(enabled=True) \
        .broadcast(ack=True) \
        .access_token(token)

    async with socket.channel("test-private-channel", params=channel_options) as chan:
        for i in range(10):
            await chan.send_broadcast("test", {"i": i})

    channel_options = RealtimeChannelOptions() \
        .private(True) \
        .broadcast(listen_self=True, replay_since=ten_mins_ago_ms, replay_limit=10) \
        .access_token(token)

    async with socket.channel("test-private-channel-replay", params=channel_options) as chan:
        message_stream = chan.messages
        while True:
            broadcast = await message_stream.__anext__()
            print(broadcast.__repr__())
            assert isinstance(broadcast, BroadcastMessage)

@pytest.mark.asyncio
async def test_subscribe_to_channel_with_empty_replay_config(
    socket: AsyncRealtimeClient,
):
    """Test that channel subscription handles empty replay configuration correctly."""
    import json
    from unittest.mock import AsyncMock, patch

    # Mock the websocket connection
    mock_ws = AsyncMock()
    socket._ws_connection = mock_ws

    # Connect the socket
    await socket.connect()

    # Create channel with empty replay configuration
    channel: AsyncRealtimeChannel = socket.channel(
        "test-empty-replay",
        params={
            "config": {
                "private": False,
                "broadcast": {"ack": True, "self": False, "replay": {}},
                "presence": {"enabled": True, "key": ""},
            }
        },
    )

    # Mock the subscription callback
    callback_called = False

    def mock_callback(state, error):
        nonlocal callback_called
        callback_called = True

    # Subscribe to the channel
    await channel.subscribe(mock_callback)

    # Verify that send was called
    assert mock_ws.send.called, "WebSocket send should have been called"

    # Get the sent message
    sent_message = mock_ws.send.call_args[0][0]
    message_data = json.loads(sent_message)

    # Verify the payload structure
    payload = message_data["payload"]
    config = payload["config"]

    assert config["private"] is False
    assert "broadcast" in config

    broadcast_config = config["broadcast"]
    assert broadcast_config["ack"] is True
    assert broadcast_config["self"] is False
    assert broadcast_config["replay"] == {}

    await socket.close()


@pytest.mark.asyncio
async def test_subscribe_to_channel_without_replay_config(socket: RealtimeClient):
    """Test that channel subscription works without replay configuration."""
    import json
    from unittest.mock import AsyncMock, patch

    # Mock the websocket connection
    mock_ws = AsyncMock()
    socket._ws_connection = mock_ws

    # Connect the socket
    await socket.connect()

    # Create channel without replay configuration
    channel: AsyncRealtimeChannel = socket.channel(
        "test-no-replay",
        params={
            "config": {
                "private": False,
                "broadcast": {"ack": True, "self": True},
                "presence": {"enabled": True, "key": ""},
            }
        },
    )

    # Mock the subscription callback
    callback_called = False

    def mock_callback(state, error):
        nonlocal callback_called
        callback_called = True

    # Subscribe to the channel
    await channel.subscribe(mock_callback)

    # Verify that send was called
    assert mock_ws.send.called, "WebSocket send should have been called"

    # Get the sent message
    sent_message = mock_ws.send.call_args[0][0]
    message_data = json.loads(sent_message)

    # Verify the payload structure
    payload = message_data["payload"]
    config = payload["config"]

    assert config["private"] is False
    assert "broadcast" in config

    broadcast_config = config["broadcast"]
    assert broadcast_config["ack"] is True
    assert broadcast_config["self"] is True
    assert "replay" not in broadcast_config

    await socket.close()
