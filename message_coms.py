import ctypes
import threading
import queue
import uuid
from typing import Callable, Dict, Optional

from zyre import Zyre, czmq
from message import Message, VALID_TYPES

# Load CZMQ library for manual zmsg construction
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

    def register_handler(self, key: str, handler: Callable[[Message], None]):
        self.handlers[key] = handler

    def send(self, msg: Message):
        payload = msg.to_json().encode()
        zmsg_ptr = build_zmsg(payload, msg.binary_blob)

        if msg.msg_type == "whisper":
            if not msg.destination:
                raise ValueError("WHISPER requires a destination")
            self.node.whisper(msg.destination, zmsg_ptr)

        elif msg.msg_type == "shout":
            target_group = self.group
            if not target_group:
                raise ValueError("No group specified for SHOUT")
            self.node.shout(target_group.encode(), zmsg_ptr)

        else:
            raise ValueError(f"Unsupported msg_type: {msg.msg_type}")

    def _send_keys(self, target_uuid: Optional[bytes] = None):
        """Send each known key to the target peer (WHISPER) or group (SHOUT)."""
        for key in self.handlers:
            msg = Message(
                coms=self,
                sender_id=self.uuid,
                msg_type="whisper" if target_uuid else "shout",
                req_id=str(uuid.uuid4()),
                key=key,
                json_data={"announce": "key"},
                destination=target_uuid,
            )
            print(f"[MessageComs] Sending {msg.msg_type.upper()} for key '{key}' to {target_uuid or 'GROUP'}")
            self.send(msg)

    def _recv_loop(self):
        while self._running:
            event = self.node.recv()
            if not hasattr(event, "type"):
                continue

            ev_type = event.type()
            if ev_type == "ENTER":
                peer_uuid_bytes = event.peer_uuid()
                print(f"[MessageComs] ENTER from peer: {peer_uuid_bytes.decode()}")
                self._send_keys(target_uuid=peer_uuid_bytes)
                continue

            if ev_type not in ("WHISPER", "SHOUT"):
                continue

            frames = event.msg()
            if not frames:
                continue

            try:
                json_data = frames[0].decode()
                blob = frames[1] if len(frames) > 1 else None
                sender_id = event.peer_uuid().decode()
                msg = Message.from_json(
                    json_data,
                    coms=self,
                    blob=blob,
                    received_by=self.uuid.encode()
                )
                self.queue.put_nowait((msg, sender_id))
            except Exception as e:
                print(f"[MessageComs] Error parsing message: {e}")

    def _worker_loop(self):
        while self._running:
            try:
                msg, sender = self.queue.get(timeout=1)
                handler = self.handlers.get(msg.key)
                if handler:
                    handler(msg)
                else:
                    print(f"[MessageComs] No handler for message key: {msg.key}")
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[MessageComs] Handler error: {e}")

    def start(self):
        self._running = True
        self._recv_thread.start()
        for thread in self._worker_threads:
            thread.start()

        # SHOUT keys on startup after short delay
        if self.handlers:
            threading.Timer(1.0, self._send_keys).start()

    def stop(self):
        self._running = False
        self.node.stop()
        self._recv_thread.join()
        for thread in self._worker_threads:
            thread.join()
