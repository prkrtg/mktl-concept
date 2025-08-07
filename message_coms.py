import ctypes
import threading
import queue
from typing import Callable, Dict, Optional

from zyre import Zyre, czmq, ZyreEvent
from message import Message, VALID_TYPES, MessageBuilder
from ctypes import c_char_p

# Load CZMQ Library
libczmq = ctypes.CDLL("libczmq.dylib")
libczmq.zmsg_new.restype = ctypes.c_void_p
libczmq.zmsg_addmem.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t]
libczmq.zmsg_destroy.argtypes = [ctypes.POINTER(ctypes.c_void_p)]


def build_zmsg(payload: bytes, blob: Optional[bytes] = None) -> czmq.zmsg_p:
    raw_ptr = libczmq.zmsg_new()
    if not raw_ptr:
        raise RuntimeError("Failed to create zmsg")
    libczmq.zmsg_addmem(raw_ptr, ctypes.c_char_p(payload), len(payload))
    if blob:
        libczmq.zmsg_addmem(raw_ptr, ctypes.c_char_p(blob), len(blob))
    return ctypes.cast(raw_ptr, czmq.zmsg_p)


def destroy_zmsg(zmsg_ptr: czmq.zmsg_p):
    libczmq.zmsg_destroy(ctypes.byref(zmsg_ptr))


class MessageComs:
    def __init__(self, name: str, group: Optional[str] = None, max_queue: int = 1000, workers: int = 2, verbose: bool = True):
        self.node = Zyre(name.encode())
        if verbose:
            self.node.set_verbose()
        self.node.start()

        self.uuid = self.node.uuid().decode()
        self.group = group
        if group:
            self.node.join(group.encode())

        self.queue = queue.Queue(maxsize=max_queue)
        self.handlers: Dict[str, Callable[[Message], None]] = {}
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._worker_threads = [
            threading.Thread(target=self._worker_loop, daemon=True)
            for _ in range(workers)
        ]
        self._running = False
        self.handlers = {}
        self.responded_to: set[str] = set()
        self._peer_keys = {}  # Maps peer_id → list of keys they support

    def register_handler(self, key: str, handler: Callable[[Message], None]):
        self.handlers[key] = handler

    def send(self, msg: Message):
        payload = msg.to_json().encode()
        zmsg_ptr = build_zmsg(payload, msg.binary_blob)

        if msg.msg_type == "whisper":
            if not msg.destination:
                raise ValueError("WHISPER requires a destination")
            peer_id_bytes = msg.destination.encode() if isinstance(msg.destination, str) else msg.destination
            peer_id = c_char_p(peer_id_bytes)
            self.node.whisper(peer_id, zmsg_ptr)

        elif msg.msg_type == "shout":
            target_group = self.group
            if not target_group:
                raise ValueError("No group specified for SHOUT")
            self.node.shout(target_group.encode(), zmsg_ptr)

        else:
            raise ValueError(f"Unsupported msg_type: {msg.msg_type}")

    def _recv_loop(self):
        print("[MessageComs] Starting receive loop...")
        while self._running:
            event = ZyreEvent(self.node)
            if not event:
                continue

            ev_type = event.type()
            if isinstance(ev_type, bytes):
                ev_type = ev_type.decode()

            print(f"[MessageComs] Received event: {ev_type}")
            peer_id = event.peer_uuid().decode()

            # Handle peer entry
            if ev_type == "ENTER":
                print(f"[MessageComs] Peer ENTERED: {peer_id}, sending group SHOUT")

                # Broadcast our keys to the group
                msg = (
                    MessageBuilder(self)
                    .with_type("shout")
                    .with_sender_id(self.uuid)
                    .with_req_id("peer-join")
                    .with_key("peer.keys")
                    .with_json_data({
                        "event": "peer_entered",
                        "from": self.uuid,
                        "keys": list(self.handlers.keys())
                    })
                    .build()
                )
                self.send(msg)
                continue

            # Ignore non-message events
            if ev_type not in ("WHISPER", "SHOUT"):
                continue

            frames = event.msg()
            if not frames:
                continue

            try:
                json_data = frames.popstr()
                blob = frames.popmem() if frames.size() > 0 else None

                msg = Message.from_json(
                    json_data,
                    coms=self,
                    blob=blob,
                    destination=peer_id,
                    received_by=self.uuid.encode()
                )

                # Automatically track peer key registry
                if msg.key == "peer.keys":
                    keys = msg.json_data.get("keys", [])
                    print(f"[MessageComs] Noted keys from {peer_id}: {keys}")
                    self._peer_keys[peer_id] = keys

                # Queue message for async consumer
                self.queue.put_nowait((msg, peer_id))

            except Exception as e:
                print(f"[MessageComs] Error parsing message: {e}")

    def _worker_loop(self):
        while self._running:
            try:
                msg, sender = self.queue.get(timeout=1)

                # Handle request/reply
                if msg.msg_type == "whisper":
                    if msg.is_request:
                        print(f"[MessageComs] Handling request {msg.req_id}")
                        try:
                            handler = self.handlers.get(msg.key)
                            if handler:
                                result = handler(msg, sender)
                                if result is not None:
                                    msg.respond(result)
                            else:
                                msg.fail(Exception("No handler for key"))
                        except Exception as e:
                            msg.fail(e)

                    elif msg.is_reply:
                        print(f"[MessageComs] Received reply to {msg.json_data.get('reply_to')}")
                        pass

            except queue.Empty:
                continue
            except Exception as e:
                print(f"[MessageComs] Handler error: {e}")

    def _send_keys(self, target_uuid: Optional[bytes] = None):
        msg = Message(
            coms=self,
            sender_id=self.uuid,
            msg_type="whisper" if target_uuid else "shout",
            req_id="keys",
            key="key.announce",
            json_data={"announce": "key"},
            binary_blob=None,
            destination=target_uuid.decode() if target_uuid else None,
            received_by=None
        )
        self.send(msg)

    def start(self):
        self._running = True
        self._recv_thread.start()
        for thread in self._worker_threads:
            thread.start()

    def stop(self):
        self._running = False
        self.node.stop()
        self._recv_thread.join()
        for thread in self._worker_threads:
            thread.join()
