from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime
import uuid
import json

# Only transport modes Zyre supports for sending
VALID_TYPES = {"whisper", "shout"}

@dataclass(frozen=True)
class Message:
    coms: "MessageComs"                     # Communication context (e.g. Zyre wrapper)
    sender_id: str                          # UUID or logical name of sender
    msg_type: str                           # "whisper" or "shout"
    req_id: str                             # Correlation ID
    key: str                                # Logical routing key (e.g. "camera.expose")
    json_data: dict                         # Main payload (structured data)
    binary_blob: Optional[bytes] = None     # Optional binary payload
    destination: Optional[bytes] = None     # WHISPER target (peer UUID)
    received_by: Optional[bytes] = None     # Populated by receiving peer if needed

    def to_json(self) -> str:
        """Serialize to JSON string (excluding binary)."""
        return json.dumps({
            "sender_id": self.sender_id,
            "msg_type": self.msg_type,
            "req_id": self.req_id,
            "key": self.key,
            "json_data": self.json_data,
            "has_blob": self.binary_blob is not None
        })

    @staticmethod
    def from_json(
        data: str,
        coms: "MessageComs",
        blob: Optional[bytes] = None,
        destination: Optional[bytes] = None,
        received_by: Optional[bytes] = None
    ) -> "Message":
        """Deserialize from JSON, attach binary if needed."""
        obj = json.loads(data)
        return Message(
            coms=coms,
            sender_id=obj["sender_id"],
            msg_type=obj["msg_type"],
            req_id=obj["req_id"],
            key=obj["key"],
            json_data=obj["json_data"],
            binary_blob=blob,
            destination=destination,
            received_by=received_by
        )

class MessageBuilder:
    def __init__(self, coms: "MessageComs"):
        self._coms = coms
        self._sender_id = coms.uuid
        self._msg_type = None
        self._req_id = str(uuid.uuid4())
        self._key = None
        self._json_data = {}
        self._binary_blob = None
        self._destination = None
        self._received_by = None

    def with_type(self, msg_type: str):
        if msg_type not in VALID_TYPES:
            raise ValueError(f"Invalid msg_type: {msg_type}. Must be one of {VALID_TYPES}")
        self._msg_type = msg_type
        return self

    def with_sender_id(self, sender_id: str):
        self._sender_id = sender_id
        return self

    def with_req_id(self, req_id: Optional[str] = None):
        self._req_id = req_id or str(uuid.uuid4())
        return self

    def with_key(self, key: str):
        self._key = key
        return self

    def with_json_data(self, data: dict):
        self._json_data = data
        return self

    def with_binary_blob(self, blob: Optional[bytes]):
        self._binary_blob = blob
        return self

    def with_destination(self, destination: bytes):
        self._destination = destination
        return self

    def with_received_by(self, received_by: bytes):
        self._received_by = received_by
        return self

    def build(self) -> Message:
        if not self._msg_type:
            raise ValueError("msg_type is required")
        if not self._key:
            raise ValueError("key is required")

        return Message(
            coms=self._coms,
            sender_id=self._sender_id,
            msg_type=self._msg_type,
            req_id=self._req_id,
            key=self._key,
            json_data=self._json_data,
            binary_blob=self._binary_blob,
            destination=self._destination,
            received_by=self._received_by
        )
