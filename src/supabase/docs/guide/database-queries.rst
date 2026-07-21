.. _guide-database-queries:

Database Queries
================

The Supabase Python client provides a fluent query builder for all
CRUD operations via PostgREST. Every query follows the same pattern:
choose a table, add filters, call ``.execute()``.

.. _query-table-access:

Table Access
------------

**Select a table:**

.. code-block:: python

   # Both are equivalent:
   supabase.table("countries")
   supabase.from_("countries")

Python reserves ``from`` as a keyword, so ``table()`` is the
preferred method. ``from_()`` is provided for compatibility with
the JavaScript SDK.

**Select a schema:**

.. code-block:: python

   supabase.schema("custom_schema").from_("countries")

The schema must be on the list of exposed schemas in your Supabase
project.

.. _query-select:

Select (Read)
-------------

.. code-block:: python

   # Select all columns
   result = supabase.table("countries").select("*").execute()

   # Select specific columns
   result = supabase.table("countries").select("name, capital").execute()

   # With filters
   result = (
       supabase.table("countries")
       .select("*")
       .eq("continent", "Europe")
       .order("name", desc=False)
       .limit(10)
       .execute()
   )

The result is an :py:class:`~postgrest.APIResponse` with ``.data``
(a list of dicts) and ``.count`` (when requested).

.. _query-insert:

Insert (Create)
---------------

.. code-block:: python

   result = (
       supabase.table("countries")
       .insert({"name": "Germany", "capital": "Berlin"})
       .execute()
   )

Insert multiple rows at once:

.. code-block:: python

   result = (
       supabase.table("countries")
       .insert([
           {"name": "France", "capital": "Paris"},
           {"name": "Spain", "capital": "Madrid"},
       ])
       .execute()
   )

.. _query-update:

Update
------

.. code-block:: python

   result = (
       supabase.table("countries")
       .update({"capital": "Jakarta"})
       .eq("name", "Indonesia")
       .execute()
   )

.. _query-upsert:

Upsert
------

Insert or update rows based on a conflict key:

.. code-block:: python

   result = (
       supabase.table("countries")
       .upsert({"name": "Indonesia", "capital": "Jakarta"})
       .execute()
   )

.. _query-delete:

Delete
------

.. code-block:: python

   result = (
       supabase.table("countries")
       .delete()
       .eq("name", "Testland")
       .execute()
   )

.. _query-filters:

Filters
-------

.. list-table::
   :header-rows: 1

   * - Filter
     - Description
   * - ``.eq("col", value)``
     - Equal to
   * - ``.neq("col", value)``
     - Not equal to
   * - ``.gt("col", value)``
     - Greater than
   * - ``.gte("col", value)``
     - Greater than or equal
   * - ``.lt("col", value)``
     - Less than
   * - ``.lte("col", value)``
     - Less than or equal
   * - ``.like("col", pattern)``
     - SQL LIKE pattern (``%`` wildcard)
   * - ``.ilike("col", pattern)``
     - Case-insensitive LIKE
   * - ``.is_("col", value)``
     - IS check (for ``NULL`` / booleans)
   * - ``.in_("col", [values])``
     - IN a list of values
   * - ``.contains("col", value)``
     - JSONB / array contains
   * - ``.order("col", desc=False)``
     - Order results
   * - ``.limit(n)``
     - Limit rows
   * - ``.range(start, end)``
     - Offset-based pagination (0-indexed)
   * - ``.or_("col.eq.val, col2.gt.val")``
     - Logical OR across fields

.. _query-rpc:

Stored Procedures (RPC)
-----------------------

.. code-block:: python

   result = supabase.rpc("add_numbers", {"a": 3, "b": 5}).execute()

   # Read-only function
   result = supabase.rpc("get_stats", get=True).execute()

   # Return count only (no data)
   result = supabase.rpc("process_batch", {"ids": [1,2,3]}, head=True).execute()

All parameters are passed as a dictionary. The ``get`` flag calls the
function in read-only mode, and ``head`` suppresses the data payload.

.. _query-count:

Counting Results
----------------

.. code-block:: python

   result = (
       supabase.table("countries")
       .select("*", count="exact")
       .eq("continent", "Europe")
       .execute()
   )
   print(result.count)  # number of matching rows

.. _query-single:

Single Row
----------

.. code-block:: python

   result = (
       supabase.table("countries")
       .select("*")
       .eq("name", "Germany")
       .single()
       .execute()
   )
   # result.data is a dict, not a list

Use ``.maybe_single()`` if the row might not exist — it returns
``None`` instead of raising.

Return Types
------------

Every ``.execute()`` call returns an :py:class:`~postgrest.APIResponse`:

.. code-block:: python

   result = supabase.table("countries").select("*").execute()
   result.data     # list[dict] — the rows
   result.count    # int | None — row count (if `count=` was used)
