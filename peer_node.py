import os
import time
import csv
import uuid
import random
import argparse
import threading
import queue
from message_coms import MessageComs
from message import MessageBuilder

RUN_DURATION_SEC = 30 * 60  # 30 minutes
WHISPER_INTERVAL = 5        # seconds
SHOUT_INTERVAL = 15         # seconds
LOG_FIELDS = ["msg_id", "rtt", "sent_time", "recv_time", "peer", "mode", "role"]

class PeerNode:
    def __init__(self, name, group, role="standard", log_dir="logs"):
        self.name = name
        self.role = role
        self.group = group
        self.uuid = str(uuid.uuid4())
        self.start_time = time.time()
        self.coms = MessageComs(name=self.name, group=self.group)
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.csv_file = os.path.join(self.log_dir, f"{self.name}.csv")

        self._init_logger()

        # Register message handlers
        self.coms.register_handler("peer.hello", self._handle_hello)
        self.coms.register_handler("perf.echo", self._handle_echo)

        self.log_queue = queue.Queue()
        self.log_thread = threading.Thread(target=self._log_writer_loop, daemon=True)
        self.log_thread.start()

    def _init_logger(self):
        self.log_fp = open(self.csv_file, "w", newline="")
        self.logger = csv.DictWriter(self.log_fp, fieldnames=LOG_FIELDS)
        self.logger.writeheader()

    def _handle_hello(self, msg, sender):
        self.peers.add(sender)

    def _handle_echo(self, msg, sender):
        recv_time = time.time()
        sent_time = msg.json_data.get("sent_time")
        rtt = recv_time - sent_time if sent_time else 0.0
        peer_id = sender.decode() if isinstance(sender, bytes) else sender
        self.log_queue.put({
            "msg_id": msg.req_id,
            "rtt": f"{rtt:.6f}",
            "sent_time": sent_time,
            "recv_time": recv_time,
            "peer": peer_id,
            "mode": "RECV",
            "role": self.role
        })
        return {"rtt": rtt, "echoed": True}
    def run(self):
        print(f"[{self.name}] Starting node in group '{self.group}' with role '{self.role}'")
        self.coms.start()
        last_whisper = 0
        last_shout = 0

        try:
            while time.time() - self.start_time < RUN_DURATION_SEC:
                now = time.time()

                # Periodic SHOUT with generic status
                if now - last_shout >= SHOUT_INTERVAL:
                    msg = (
                        MessageBuilder(self.coms)
                        .with_type("shout")
                        .with_sender_id(self.coms.uuid)
                        .with_req_id(str(uuid.uuid4()))
                        .with_key("peer.status")
                        .with_json_data({
                            "status": "alive",
                            "role": self.role,
                            "timestamp": now,
                        })
                        .build()
                    )
                    self.coms.send(msg)
                    last_shout = now

                # Periodic WHISPER to a random known peer
                known_peers = list(self.coms._peer_keys.keys())
                if now - last_whisper >= WHISPER_INTERVAL and known_peers:
                    peer = random.choice(known_peers)
                    sent_time = time.time()
                    msg = (
                        MessageBuilder(self.coms)
                        .with_type("whisper")
                        .with_sender_id(self.coms.uuid)
                        .with_req_id(str(uuid.uuid4()))
                        .with_key("perf.echo")
                        .with_destination(peer)
                        .with_json_data({"sent_time": sent_time})
                        .build()
                    )
                    self.coms.send(msg)
                    self.log_queue.put({
                        "msg_id": msg.req_id,
                        "rtt": "",
                        "sent_time": sent_time,
                        "recv_time": "",
                        "peer": peer,
                        "mode": "SEND",
                        "role": self.role
                    })
                    last_whisper = now

                time.sleep(0.1)
        finally:
            self.log_queue.put(None)
            self.log_thread.join()
            self.log_fp.close()
            print(f"[{self.name}] Shut down complete.")

    def _log_writer_loop(self):
        while True:
            entry = self.log_queue.get()
            if entry is None:
                break
            try:
                self.logger.writerow(entry)
                self.log_fp.flush()
            except Exception as e:
                print(f"[{self.name}] Logging error: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--name", required=True)
    parser.add_argument("--group", default="mktl-perf")
    parser.add_argument("--role", default="standard")
    parser.add_argument("--log-dir", default="logs")
    args = parser.parse_args()

    node = PeerNode(args.name, args.group, args.role, args.log_dir)
    node.run()

if __name__ == "__main__":
    main()
