"""
# models/event_model.py

Defines a single event that occurred during an Expedition.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4


@dataclass
class Event:
    """A single event recorded during an Expedition."""

    category: str              # Raid, Broadcast, Incident, Achievement...
    event: str                 # Boss Clear, BRB, Pull Started...

    source: str                # Stream Events, Broadcast Desk, etc.

    payload: dict[str, Any] = field(default_factory=dict)

    severity: str = "info"

    notes: str = ""

    id: str = field(default_factory=lambda: str(uuid4()))

    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "category": self.category,
            "event": self.event,
            "severity": self.severity,
            "source": self.source,
            "notes": self.notes,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, data: dict):

        event = cls(
            category=data["category"],
            event=data["event"],
            source=data["source"],
            payload=data.get("payload", {}),
            severity=data.get("severity", "info"),
            notes=data.get("notes", ""),
        )

        event.id = data["id"]
        event.timestamp = datetime.fromisoformat(data["timestamp"])

        return event