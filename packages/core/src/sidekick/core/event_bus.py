"""EventBus protocol and implementations.

Agent code must depend only on the EventBus protocol — never import LocalEventBus or
AWSEventBus directly. The runtime wires the correct implementation at startup.

Local (dev): LocalEventBus wraps Postgres LISTEN/NOTIFY via psycopg2.
Production: AWSEventBus publishes to EventBridge/SQS; subscribe() is a no-op because
  routing is configured in infrastructure (CDK/Terraform).
"""

import json
import logging
import threading
from collections import defaultdict
from typing import Callable, Protocol, runtime_checkable

import psycopg2
import psycopg2.extensions

logger = logging.getLogger(__name__)


@runtime_checkable
class EventBus(Protocol):
    """Publish events and register handlers for incoming events."""

    def publish(self, event_type: str, payload: dict) -> None:
        """Publish an event with the given payload."""
        ...

    def subscribe(self, event_type: str, handler: Callable[[dict], None]) -> None:
        """Register a handler to be called when an event of event_type arrives."""
        ...


class LocalEventBus:
    """Postgres LISTEN/NOTIFY backed event bus for local development.

    A single persistent connection is used for LISTEN; a separate connection is used
    for NOTIFY so that publish() works from any thread without holding a long transaction.

    Usage:
        bus = LocalEventBus(dsn="postgresql://...")
        bus.subscribe("artifact_written", my_handler)
        bus.start_listening()  # spawns a background thread
    """

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._handlers: dict[str, list[Callable[[dict], None]]] = defaultdict(list)
        self._listener_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def publish(self, event_type: str, payload: dict) -> None:
        """Send a NOTIFY with JSON payload on the event_type channel."""
        payload_json = json.dumps(payload)
        with psycopg2.connect(self._dsn) as conn:
            conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
            with conn.cursor() as cur:
                # Channel name is the event_type; payload is compact JSON
                cur.execute(f"NOTIFY {event_type}, %s", (payload_json,))

    def subscribe(self, event_type: str, handler: Callable[[dict], None]) -> None:
        """Register a handler for the given channel name."""
        self._handlers[event_type].append(handler)

    def start_listening(self) -> None:
        """Start a background thread that polls for notifications."""
        if self._listener_thread and self._listener_thread.is_alive():
            return
        self._stop_event.clear()
        self._listener_thread = threading.Thread(
            target=self._listen_loop, daemon=True, name="event-bus-listener"
        )
        self._listener_thread.start()

    def stop_listening(self) -> None:
        """Signal the listener thread to stop."""
        self._stop_event.set()

    def _listen_loop(self) -> None:
        conn = psycopg2.connect(self._dsn)
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            for channel in self._handlers:
                cur.execute(f"LISTEN {channel}")
        logger.info("EventBus listening on channels: %s", list(self._handlers))

        import select

        while not self._stop_event.is_set():
            if select.select([conn], [], [], 1.0)[0]:
                conn.poll()
                while conn.notifies:
                    notify = conn.notifies.pop(0)
                    self._dispatch(notify.channel, notify.payload)
        conn.close()

    def _dispatch(self, channel: str, payload_str: str) -> None:
        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError:
            logger.warning("Non-JSON notify payload on %s: %s", channel, payload_str)
            return
        for handler in self._handlers.get(channel, []):
            try:
                handler(payload)
            except Exception:
                logger.exception("Handler error on channel %s", channel)


class AWSEventBus:
    """EventBridge/SQS backed event bus for production.

    publish() sends to EventBridge. subscribe() is a no-op — handler wiring
    is declared in infrastructure (CDK/Terraform) which maps EventBridge rules
    to Lambda/Fargate targets. The same handler functions are invoked at runtime
    by the Lambda/Fargate entrypoint.
    """

    def __init__(self, event_bus_name: str = "default") -> None:
        import boto3

        self._client = boto3.client("events")
        self._event_bus_name = event_bus_name

    def publish(self, event_type: str, payload: dict) -> None:
        self._client.put_events(
            Entries=[
                {
                    "Source": "sidekick-pipeline",
                    "DetailType": event_type,
                    "Detail": json.dumps(payload),
                    "EventBusName": self._event_bus_name,
                }
            ]
        )

    def subscribe(self, event_type: str, handler: Callable[[dict], None]) -> None:
        # No-op: routing is configured in infrastructure, not at runtime.
        pass
