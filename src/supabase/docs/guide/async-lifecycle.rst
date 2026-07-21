.. _guide-async-lifecycle:

Async Lifecycle
===============

``supabase-py`` provides parallel sync and async implementations of
the entire client surface. This page explains the differences, event
loop considerations, and best practices.

Sync vs Async — Quick Reference
-------------------------------

=========================== ================================== ===================================
Concept                     Sync                                Async
=========================== ================================== ===================================
Factory                     ``create_client(url, key)``         ``await create_async_client(url, key)``
Client class                ``Client``                          ``AsyncClient``
Options class               ``ClientOptions``                   ``AsyncClientOptions``
Auth client                 ``SupabaseAuthClient``              ``AsyncSupabaseAuthClient``
Storage                     ``storage`` property (sync)         ``storage`` property (async)
Realtime                    ``SyncRealtimeClient``              ``AsyncRealtimeClient``
=========================== ================================== ===================================

The async client uses ``httpx.AsyncClient`` under the hood and all
network calls are ``await``\ -able.

Creating an Async Client
------------------------

.. code-block:: python

   from supabase import create_async_client, AsyncClient

   client = await create_async_client(url, key)

The factory is ``async`` because it attempts to load an existing
session from storage during initialization:

.. code-block:: python

   # Under the hood (simplified):
   async def create(cls, url, key, options):
       client = cls(url, key, options)
       session = await client.auth.get_session()   # IO-bound
       # ... update headers with session token
       return client

Event Loop Ownership
--------------------

- The async client is **not a context manager** — you create it with
  ``await create_async_client()`` and manage its lifetime yourself.
- The async client spawns a background task via
  ``asyncio.create_task(self.realtime.set_auth(...))`` whenever auth
  state changes. This means the client **must** live within a running
  event loop.
- For a typical ``asyncio.run()`` entry point, create the client inside
  the async function and pass it around:

.. code-block:: python

   async def main():
       client = await create_async_client(url, key)
       result = await client.table("users").select("*").execute()
       print(result.data)

   asyncio.run(main())

Session Storage
---------------

Sync uses ``SyncMemoryStorage``; async uses ``AsyncMemoryStorage``.
Both are in-memory only — sessions are lost when the process exits.
For persistent sessions, pass your own storage implementation that
conforms to ``SyncSupportedStorage`` / ``AsyncSupportedStorage``
protocols.

Realtime Auth in Async
----------------------

Unlike sync, the async client explicitly propagates auth state changes
to the realtime client via a background task:

.. code-block:: python

   # In AsyncClient._listen_to_auth_events:
   asyncio.create_task(self.realtime.set_auth(access_token))

This ensures the websocket connection carries the correct auth token
when the user signs in, refreshes, or signs out — without blocking the
event callback.

Client Cleanup
--------------

To shut down properly:

.. code-block:: python

   await client.auth.sign_out()
   # The realtime connection and any background tasks are cleaned up

For long-running applications (e.g., FastAPI), keep one client per
event loop and sign out on application shutdown.
