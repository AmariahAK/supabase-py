.. _guide-storage-functions:

Storage & Functions
===================

The Supabase client provides file storage management via
``client.storage`` and edge function invocation via
``client.functions``.

Storage
-------

.. _storage-buckets:

Buckets
^^^^^^^

Access a bucket with ``.from_()`` (Python reserves ``from`` as a
keyword):

.. code-block:: python

   bucket = supabase.storage.from_("avatars")

Upload
^^^^^^

.. code-block:: python

   # Upload from bytes
   with open("photo.png", "rb") as f:
       result = supabase.storage.from_("avatars").upload(
           "user/123/profile.png", f.read()
       )

   # Upload from a file path
   result = supabase.storage.from_("avatars").upload(
       "user/123/profile.png", "/path/to/photo.png"
   )

Download
^^^^^^^^

.. code-block:: python

   data = supabase.storage.from_("avatars").download("user/123/profile.png")
   # data is bytes
   with open("downloaded.png", "wb") as f:
       f.write(data)

List Files
^^^^^^^^^^

.. code-block:: python

   files = supabase.storage.from_("avatars").list("user/123/")
   for f in files:
       print(f["name"], f["metadata"]["size"])

Remove
^^^^^^

.. code-block:: python

   supabase.storage.from_("avatars").remove([
       "user/123/old_photo.png",
       "user/123/tmp.png",
   ])

Move / Rename
^^^^^^^^^^^^^

.. code-block:: python

   supabase.storage.from_("avatars").move(
       "user/123/tmp.png",
       "user/123/confirmed.png",
   )

Signed URLs
^^^^^^^^^^^

.. code-block:: python

   url = supabase.storage.from_("avatars").create_signed_url(
       "user/123/profile.png", 60  # expires in 60 seconds
   )
   print(url)  # Temporary, signed download URL

   # For public buckets:
   url = supabase.storage.from_("avatars").get_public_url(
       "user/123/profile.png"
   )

Edge Functions
--------------

.. _functions-invoke:

Invoke
^^^^^^

.. code-block:: python

   resp = supabase.functions.invoke(
       "hello-world",
       invoke_options={
           "body": {"name": "Alice"},
       },
   )

   # With a specific region
   from supabase_functions import FunctionRegion
   resp = supabase.functions.invoke(
       "hello-world",
       invoke_options={
           "body": {"name": "Alice"},
           "region": FunctionRegion.US_EAST_1,
       },
   )

Error Handling
^^^^^^^^^^^^^^

Two exception classes cover all failure modes:

.. code-block:: python

   from supabase import FunctionsHttpError, FunctionsRelayError

   try:
       resp = supabase.functions.invoke("my-function", invoke_options={"body": {}})
   except FunctionsHttpError as e:
       # HTTP error (4xx, 5xx) from the function
       print(e.to_dict())
   except FunctionsRelayError as e:
       # Relay error from Supabase infrastructure
       print(e.to_dict())

``FunctionsHttpError`` wraps 4xx/5xx responses with ``.to_dict()``
for structured error inspection.
