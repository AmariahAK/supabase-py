.. _guide-start:

Getting Started
===============

This page walks you through installing ``supabase-py``, configuring
your environment, creating your first client, and running your first
query.

Installation
------------

Install the package (Python >= 3.9):

.. code-block:: bash

   # with pip
   pip install supabase

   # with uv
   uv add supabase

   # with conda
   conda install -c conda-forge supabase

Environment Variables
---------------------

The client needs your Supabase **project URL** and **API key**.
Store them as environment variables:

.. code-block:: bash

   export SUPABASE_URL="https://<project-id>.supabase.co"
   export SUPABASE_KEY="<your-anon-or-service-role-key>"

Or in a ``.env`` file:

.. code-block:: text

   SUPABASE_URL=https://<project-id>.supabase.co
   SUPABASE_KEY=<your-anon-or-service-role-key>

Creating a Client
-----------------

**Synchronous client** — use :py:func:`~supabase.create_client`:

.. code-block:: python

   import os
   from supabase import create_client, Client

   url: str = os.environ["SUPABASE_URL"]
   key: str = os.environ["SUPABASE_KEY"]
   supabase: Client = create_client(url, key)

**Asynchronous client** — use :py:func:`~supabase.create_async_client`:

.. code-block:: python

   import os
   from supabase import create_async_client, AsyncClient

   url: str = os.environ["SUPABASE_URL"]
   key: str = os.environ["SUPABASE_KEY"]
   supabase: AsyncClient = await create_async_client(url, key)

The async factory is also available as ``acreate_client`` for brevity.

Your First Query
----------------

With a client in hand, run a query against a public table:

.. code-block:: python

   # Insert a row
   result = supabase.table("countries").insert({"name": "Germany"}).execute()
   print(result.data)  # [{"id": 1, "name": "Germany", ...}]

   # Select rows
   result = supabase.table("countries").select("*").execute()
   print(result.data)

The pattern is always the same: choose a table, build a query chain,
and call ``.execute()``. See :doc:`/guide/database-queries` for all
supported operations.

Client Reuse Guidance
---------------------

- **Reuse a single client instance** within your application's
  lifetime. The client internally manages auth state, header
  propagation, and lazy service clients (PostgREST, Storage,
  Functions).
- **Do not create a new client per request.** Client initialization
  is cheap but not free, and each client maintains its own session
  tracking and realtime connections.
- **Multiple clients are fine** when you need separate auth contexts
  (e.g., different user sessions). Create one client per session
  store.
- **For serverless / per-request contexts**, create the client once
  at module level and reuse it across invocations. Pass custom
  ``Authorization`` headers via :doc:`ClientOptions </guide/clients>`
  if needed.

Next Steps
----------

- :doc:`/guide/clients` — customise timeouts, schemas, shared HTTP clients
- :doc:`/guide/async-lifecycle` — understand sync vs async patterns
- :doc:`/guide/database-queries` — full CRUD and filter reference
