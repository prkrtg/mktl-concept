import time
from message_coms import MessageComs

GROUP_NAME = "mktl-test"

def handle_test_message(msg):
    print(f"[NODE B] Received {msg.msg_type.upper()} from {msg.sender_id}")
    print(f"[NODE B] Key: {msg.key}")
    print(f"[NODE B] Payload: {msg.json_data}")
    print(f"[NODE B] Raw Message: {msg}")

def node_b():
    print("[NODE B] Starting...")
    node = MessageComs(name="node-b", group=GROUP_NAME)
    node.register_handler("test.key", handle_test_message)
    node.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[NODE B] Shutting down...")
        node.stop()

if __name__ == "__main__":
    node_b()
