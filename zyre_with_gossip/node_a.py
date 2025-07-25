from zyre_utils import setup_zyre_node
import time

node = setup_zyre_node(
    name=b"node-a",
    group=b"buddies",
    gossip_bind=b"tcp://127.0.0.1:9999"
)

print("[node-a] Running as gossip hub... Press Ctrl+C to exit.")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("[node-a] Shutting down...")
    node.stop()

