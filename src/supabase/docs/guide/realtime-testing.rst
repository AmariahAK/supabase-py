.. _guide-realtime-testing:

Realtime & Testing
==================

The Supabase client exposes the full realtime API for subscribing to
database changes, broadcasting messages, and tracking presence.

Channels
--------

A channel groups related subscriptions. Create one with a unique
topic name:

.. code-block:: python

   channel = supabase.channel("room-1")

Broadcast
---------

Send and receive messages on a channel:

.. code-block:: python

   def on_broadcast(payload):
       print(f"Received: {payload}")

   channel = supabase.channel("room-1")
   channel.on_broadcast("chat", on_broadcast).subscribe()

   # Send a message
   channel.send({
       "type": "broadcast",
       "event": "chat",
       "payload": {"message": "hello!"},
   })

Presence
--------

Track who is online in a channel:

.. code-block:: python

   channel = supabase.channel("room-1")

   def on_presence(presence):
       print(f"Online users: {presence}")

   channel.on_presence(on_presence).subscribe()

   # Announce presence
   channel.track({"user": "alice", "status": "online"})

Postgres Changes
----------------

Subscribe to database changes in realtime:

.. code-block:: python

   def on_insert(payload):
       print(f"New row: {payload.new}")

   channel = (
       supabase.channel("schema-db-changes")
       .on_postgres_changes(
           "INSERT",
           schema="public",
           table="messages",
           callback=on_insert,
       )
       .subscribe()
   )

The ``callback`` receives a payload with ``.new`` (the new row), ``.old``
(the previous row for UPDATE/DELETE), and ``.event_type``.

Supported events: ``INSERT``, ``UPDATE``, ``DELETE``, ``*`` (all).

Channel Lifecycle
-----------------

.. code-block:: python

   channel = supabase.channel("room-1")
   channel.subscribe()        # Connect and start receiving events
   channel.unsubscribe()      # Disconnect but keep the channel
   supabase.remove_channel(channel)  # Unsubscribe and remove

   # List all active channels
   channels = supabase.get_channels()

   # Remove all channels at once
   supabase.remove_all_channels()

Testing Patterns
----------------

Use pytest with a session-scoped fixture to reuse one client across
tests:

.. code-block:: python

   import os
   import pytest
   from supabase import create_client, Client

   @pytest.fixture(scope="session")
   def supabase() -> Client:
       url = os.environ["SUPABASE_TEST_URL"]
       key = os.environ["SUPABASE_TEST_KEY"]
       return create_client(url, key)

   def test_insert(supabase: Client):
       result = supabase.table("countries").insert({
           "name": "Test Country"
       }).execute()
       assert len(result.data) > 0

   def test_select(supabase: Client):
       result = supabase.table("countries").select("*").execute()
       assert len(result.data) > 0

For async tests, install ``pytest-asyncio`` and use ``@pytest.mark.asyncio``:

.. code-block:: python

   import pytest
   from supabase import create_async_client, AsyncClient

   @pytest.fixture(scope="session")
   async def async_client() -> AsyncClient:
       url = os.environ["SUPABASE_TEST_URL"]
       key = os.environ["SUPABASE_TEST_KEY"]
       return await create_async_client(url, key)

   @pytest.mark.asyncio
   async def test_async_query(async_client: AsyncClient):
       result = await async_client.table("countries").select("*").execute()
       assert len(result.data) > 0

Environment Setup
^^^^^^^^^^^^^^^^^

The test runner expects these environment variables (set via
``.env``, shell exports, or CI secrets):

.. code-block:: text

   SUPABASE_TEST_URL=https://<project-id>.supabase.co
   SUPABASE_TEST_KEY=<your-anon-or-service-role-key>

The supabase-py test suite loads them from ``tests/tests.env``
via ``python-dotenv``.
