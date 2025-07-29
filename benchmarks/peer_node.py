import os
import time
import uuid
import random
import logging
import ctypes
import czmq
import csv
from multiprocessing import Process, Queue
from zyre_utils import setup_zyre_node, get_peer_uuids, parse_msg_frames

libczmq = ctypes.CDLL("libczmq.dylib")
libczmq.zmsg_new.restype = czmq.zmsg_p
libczmq.zmsg_addstr.argtypes = [czmq.zmsg_p, ctypes.c_char_p]


def make_zmsg(text: str) -> czmq.zmsg_p:
    zmsg = libczmq.zmsg_new()
    libczmq.zmsg_addstr(zmsg, text.encode("utf-8"))
    return zmsg


def make_payload(role: str):
    msg_id = str(uuid.uuid4())  # Generate a unique message ID
    sent_time = time.time()  # Get the current time (sent_time)

    # Role-based payloads, ensuring the format always includes msg_id and sent_time
    sizes = {
        "low": f"{msg_id} {sent_time}",  # Low role: ping with msg_id and sent_time
        "medium": f"{msg_id} {sent_time} " + "M" * (500 * 1024),  # Medium role: large message
        "high": f"{msg_id} {sent_time} " + "H" * (2 * 1024 * 1024),  # High role: even larger message
        "hungry": f"{msg_id} {sent_time} " + "X" * (50 * 1024 * 1024),  # Hungry role: massive message
    }

    return sizes.get(role, f"{msg_id} {sent_time}")  # Default to low if no valid role


def write_csv(queue, log_path_csv):
    """Write messages from the queue to the CSV file."""
    with open(log_path_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["msg_id", "rtt", "sent_time", "recv_time", "peer", "mode", "role"])
        writer.writeheader()

        while True:
            msg = queue.get()
            if msg == "DONE":
                break
            writer.writerow(msg)


class PeerNode:
    def __init__(self, peer_id, group, shout_rate, whisper_rate, log_dir, role=None):
        self.peer_id = str(peer_id)
        self.group = group
        self.shout_rate = shout_rate
        self.whisper_rate = whisper_rate
        self.log_dir = log_dir
        self.role = role or random.choice(["low", "medium", "high", "hungry"])

        # Queue for communication between processes
        self.queue = Queue()

        os.makedirs(self.log_dir, exist_ok=True)
        self.log_path_txt = os.path.join(self.log_dir, f"{self.peer_id}.log")
        self.log_path_csv = os.path.join(self.log_dir, f"{self.peer_id}.csv")

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(name)s] %(message)s",
            handlers=[logging.FileHandler(self.log_path_txt), logging.StreamHandler()]
        )
        self.logger = logging.getLogger(self.peer_id)
        self.logger.info(f"Starting with role: {self.role}")

        self.peer_uuid = None
        self.payload = make_payload(self.role)
        self.last_shout = time.time()
        self.last_whisper = time.time()


    def _discover_peer(self, node):
        for _ in range(60):
            peers = get_peer_uuids(node.peers())
            if peers:
                self.peer_uuid = peers[0]
                self.logger.info(f"Found peer {self.peer_uuid}")
                break
            time.sleep(0.5)

        if not self.peer_uuid:
            self.logger.warning("No peer found after 30s, continuing anyway...")

    def start_csv_writer(self):
        """Start the CSV writer process."""
        writer_process = Process(target=write_csv, args=(self.queue, self.log_path_csv))
        writer_process.start()
        return writer_process

    def send_shout(self, node):
        """Send SHOUT message."""
        msg_id = str(uuid.uuid4())
        msg = make_zmsg(f"{msg_id} {time.time()}")
        node.shout(self.group.encode(), msg)
        self.queue.put({
            "msg_id": msg_id,
            "rtt": 0,
            "sent_time": time.time(),
            "recv_time": 0,
            "peer": "ALL",
            "mode": "SHOUT",
            "role": self.role
        })

    def send_whisper(self, node):
        """Send WHISPER message."""
        msg_id = str(uuid.uuid4())
        msg = make_zmsg(f"{msg_id} {time.time()}")
        node.whisper(self.peer_uuid.encode(), msg)
        self.queue.put({
            "msg_id": msg_id,
            "rtt": 0,
            "sent_time": time.time(),
            "recv_time": 0,
            "peer": self.peer_uuid,
            "mode": "WHISPER",
            "role": self.role
        })

    def receive_messages(self, node):
        """Handle incoming messages."""
        msg = node.recv()
        if msg:
            frames = parse_msg_frames(msg)

            # Check if there are enough frames
            if len(frames) >= 4:
                event_type = frames[0].decode()  # Decode event type (SHOUT or WHISPER)
                peer = frames[1].decode(errors="ignore")  # Decode peer UUID
                name = frames[2].decode(errors="ignore")  # Decode sender name
                content = frames[3]  # This is the message content or group name

                if event_type == "SHOUT" and len(frames) >= 5:
                    content = frames[4]  # For SHOUT, message content is at index 4

                # Debugging: log the event type, peer, and content (payload)
                self.logger.debug(
                    f"Received {event_type} from {peer} ({name}) with content: {content.decode(errors='ignore')}")

                try:
                    payload = content.decode(errors="ignore")  # Decode the content payload

                    # Handle SHOUT and WHISPER events
                    if event_type in ["SHOUT", "WHISPER"]:
                        parts = payload.split()  # Split into msg_id and sent_time

                        # Check if the payload is in the expected format (msg_id sent_time)
                        if len(parts) == 2:
                            msg_id, sent_time = parts
                            recv_time = time.time()
                            latency = recv_time - float(sent_time)

                            # Queue the data for logging in CSV
                            self.queue.put({
                                "msg_id": msg_id,
                                "rtt": latency,
                                "sent_time": sent_time,
                                "recv_time": recv_time,
                                "peer": peer,
                                "mode": event_type,
                                "role": self.role
                            })
                            self.logger.info(f"Received {event_type} from {peer} ({name}) latency={latency:.4f}")
                        else:
                            # Handle malformed payload
                            self.logger.warning(f"Invalid {event_type} format: {payload}")
                    else:
                        # Handle any other event types like JOIN, ENTER, LEAVE
                        self.logger.info(f"Received unknown event: {event_type} from {peer} ({name})")

                except Exception as e:
                    self.logger.warning(f"[{self.peer_id}] Decode error for event {event_type} from {peer}: {e}")
            else:
                # Not supported
                self.logger.warning(f"Not supported")

    def run(self, node):
        """Start the node and handle message sending/receiving."""
        self._discover_peer(node)
        writer_process = self.start_csv_writer()

        try:
            while True:
                now = time.time()
                if self.shout_rate > 0 and now - self.last_shout >= 1 / self.shout_rate:
                    self.last_shout = now
                    self.send_shout(node)

                if self.whisper_rate > 0 and self.peer_uuid and now - self.last_whisper >= 1 / self.whisper_rate:
                    self.last_whisper = now
                    self.send_whisper(node)

                self.receive_messages(node)
                time.sleep(0.001)
        except KeyboardInterrupt:
            self.logger.info("Shutting down")
        finally:
            self.queue.put("DONE")
            writer_process.join()
