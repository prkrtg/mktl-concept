import time
from zyre_utils import setup_zyre_node, parse_msg_frames, log_event

node = setup_zyre_node(
    name=b"node-b",
    group=b"buddies",
    gossip_connect=b"tcp://127.0.0.1:9999"
)

print("[node-b] Waiting for events...")
try:
    while True:
        msg = node.recv()
        if msg is None:
            continue
        frames = parse_msg_frames(msg)
        log_event(frames, "[node-b]")
        time.sleep(0.1)

except KeyboardInterrupt:
    node.stop()

