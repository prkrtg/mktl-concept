import time
from message_coms import MessageComs
from message import MessageBuilder

GROUP_NAME = "mktl-test"

def node_a():
    print("[NODE A] Starting...")
    node = MessageComs(name="node-a", group=GROUP_NAME)
    node.start()

    # Optional: run for a fixed duration
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[NODE A] Shutting down...")
        node.stop()

def handle_test_key(msg, peer_id):
    print(f"[NODE A HANDLER] Message from {peer_id}: {msg.json_data}")


if __name__ == "__main__":
    node_a()
