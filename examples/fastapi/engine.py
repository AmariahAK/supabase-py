# examples/fastapi/engine.py
import asyncio

from supabase._async.client import AsyncClient


async def on_task_change(service_client: AsyncClient, payload: dict) -> None:
    """
    Called by the Realtime subscription for each UPDATE on the tasks table.

    FRICTION NOTE: The supabase-py Realtime callback is synchronous by design
    in some versions — if channel.on_postgres_changes() does not accept an
    async callback, wrap this function with asyncio.create_task() inside a
    sync wrapper. See friction_log.md — "Realtime callback async support".
    """
    new_record = payload.get("new", {})
    if not new_record or not new_record.get("id"):
        return

    rules_response = await service_client.table("rules").select("*").execute()

    for rule in rules_response.data:
        if (
            rule["watch_column"] == "status"
            and rule["watch_value"] == new_record.get("status")
        ):
            await service_client.table("rule_events").insert({
                "rule_id": rule["id"],
                "task_id": new_record["id"],
                "payload": new_record,
            }).execute()

            # FRICTION: channel.send() requires an active subscription first.
            # Creating a new channel and subscribing before every broadcast is
            # expensive. See friction_log.md — "Broadcast requires prior subscribe".
            broadcast_channel = service_client.channel(rule["broadcast_channel"])
            await broadcast_channel.subscribe()
            await broadcast_channel.send(
                type="broadcast",
                event="rule_fired",
                payload={"rule": rule, "task": new_record},
            )


async def start_engine(service_client: AsyncClient) -> None:
    """
    Background coroutine that holds the persistent Realtime connection.
    Launched once at app startup via asyncio.create_task().
    """
    channel = service_client.channel("tasks-watcher")

    # FRICTION: on_postgres_changes may only accept a sync callable.
    # If async callbacks are not supported, we wrap with asyncio.get_event_loop().
    # Document the actual behavior in friction_log.md.
    def _sync_wrapper(payload: dict) -> None:
        asyncio.get_running_loop().create_task(on_task_change(service_client, payload))

    channel.on_postgres_changes(
        event="UPDATE",
        schema="public",
        table="tasks",
        callback=_sync_wrapper,
    )

    # FRICTION: Manual connect() required before subscribe(). No auto-connect.
    # See friction_log.md — "Manual connect() required before subscribe()".
    await service_client.realtime.connect()
    await channel.subscribe()

    # Keep the coroutine alive; AsyncRealtimeClient handles WS keepalive internally.
    await asyncio.Event().wait()
