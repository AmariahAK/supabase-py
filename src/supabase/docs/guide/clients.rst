.. _guide-clients:

Client Options
==============

Every aspect of the Supabase client can be tuned through
:py:class:`~supabase.ClientOptions` (sync) or
:py:class:`~supabase.AsyncClientOptions` (async).

Both are Python dataclasses with sensible defaults — you only need to
set the fields you want to override.

Basic Usage
-----------

.. code-block:: python

   from supabase import create_client, ClientOptions

   options = ClientOptions(
       schema="custom",
       auto_refresh_token=False,
   )
   supabase = create_client(url, key, options)

All Options
-----------

.. list-table::
   :header-rows: 1

   * - Option
     - Default
     - Description
   * - ``schema``
     - ``"public"``
     - Postgres schema for table operations
   * - ``headers``
     - auto
     - Extra HTTP headers sent with every request
   * - ``auto_refresh_token``
     - ``True``
     - Automatically refresh expired auth tokens
   * - ``persist_session``
     - ``True``
     - Persist logged-in sessions to storage
   * - ``storage``
     - memory
     - Storage backend for session persistence
   * - ``realtime``
     - ``None``
     - Options passed to the underlying realtime client
   * - ``postgrest_client_timeout``
     - 20s
     - Timeout for PostgREST requests
   * - ``storage_client_timeout``
     - 20s
     - Timeout for Storage requests
   * - ``function_client_timeout``
     - 20s
     - Timeout for Edge Function invocations
   * - ``flow_type``
     - ``"pkce"``
     - Auth flow type (``"pkce"`` or ``"implicit"``)
   * - ``httpx_client``
     - ``None``
     - Share an existing ``httpx.Client`` / ``AsyncClient``

Custom Headers
--------------

Add application-specific headers that travel with every request:

.. code-block:: python

   options = ClientOptions(
       headers={
           "x-app-name": "my-app",
           "x-version": "2.0.0",
       }
   )

The ``Authorization`` and ``apiKey`` headers are managed automatically
by the client and should not be overridden via ``headers``.

Custom Timeouts
---------------

Set per-service timeouts to control how long the client waits:

.. code-block:: python

   options = ClientOptions(
       postgrest_client_timeout=30.0,    # float or int (seconds)
       storage_client_timeout=60,        # int (seconds) — large files
       function_client_timeout=15,       # int (seconds) — quick functions
   )

Sharing an httpx Client
-----------------------

Pass your own ``httpx.Client`` (or ``httpx.AsyncClient``) to share
connection pools, custom transports, proxy settings, or TLS
configuration across all Supabase services:

.. code-block:: python

   import httpx
   from supabase import create_client, ClientOptions

   http = httpx.Client(
       timeout=httpx.Timeout(10.0, read=60.0),
       limits=httpx.Limits(max_connections=20),
   )
   options = ClientOptions(httpx_client=http)
   supabase = create_client(url, key, options)
   # PostgREST, Storage, Functions, and Auth all use the same http client

The shared httpx client also carries its own base headers (e.g.,
``x-user-agent``) which will be sent alongside the Supabase headers.

Changing Options After Creation
-------------------------------

Both ``SyncClientOptions`` and ``AsyncClientOptions`` expose a
``.replace()`` method that returns a **new** options object (the
original is not mutated):

.. code-block:: python

   new_options = options.replace(schema="other_schema")
   # options.schema is still "custom"

The ``replace()`` method uses ``None`` to mean "keep the current
value," so boolean fields like ``auto_refresh_token`` you must
pass the explicit ``True``/``False``.
