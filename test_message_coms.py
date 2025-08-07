import time
from message_coms import MessageComs
from message import MessageBuilder

GROUP_NAME = "mktl-test"

def handle_test_message(msg):
    print("\n[HANDLER] === Received Message ===")
    print(f"[HANDLER] Type    : {msg.msg_type.upper()}")
    print(f"[HANDLER] From    : {msg.sender_id}")
    print(f"[HANDLER] Key     : {msg.key}")
    print(f"[HANDLER] Payload : {msg.json_data}")
    print(f"[HANDLER] Raw     : {msg}")
    print("[HANDLER] =========================\n")

def fallback_handler(msg):
    print("\n[FALLBACK] === Received Unknown Key ===")
    print(f"[FALLBACK] Type    : {msg.msg_type.upper()}")
    print(f"[FALLBACK] From    : {msg.sender_id}")
    print(f"[FALLBACK] Key     : {msg.key}")
    print(f"[FALLBACK] Payload : {msg.json_data}")
    print(f"[FALLBACK] Raw     : {msg}")
    print("[FALLBACK] =============================\n")

def test_message_coms():
    print("[TEST] Starting test...")

    print("[TEST] Creating node_b (receiver)...")
    node_b = MessageComs(name="node-b", group=GROUP_NAME)
    node_b.register_handler("test.key", handle_test_message)
    node_b.register_handler("key.announce", handle_test_message)
    node_b.register_handler("*", fallback_handler)
    node_b.start()

    print("[TEST] Creating node_a (sender)...")
    node_a = MessageComs(name="node-a", group=GROUP_NAME)
    node_a.register_handler("key.announce", handle_test_message)
    node_a.register_handler("*", fallback_handler)
    node_a.start()

    print("[TEST] Waiting for peer discovery...")
    time.sleep(3)

    print(f"[DEBUG] node_a peers: {node_a.node.peers()}")
    print(f"[DEBUG] node_b peers: {node_b.node.peers()}")

    print(f"[DEBUG] node_a group: {node_a.group}")
    print(f"[DEBUG] node_b group: {node_b.group}")

    print("[TEST] Building message...")
    msg = (
        MessageBuilder(node_a)
        .with_type("shout")
        .with_sender_id(node_a.uuid)
        .with_req_id("req-001")
        .with_key("test.key")
        .with_json_data({"hello": "zyre!"})
        .build()
    )

    print(f"[TEST] Built message: {msg}")
    print("[TEST] Sending message...")
    node_a.send(msg)

    time.sleep(1)
    print("[TEST] Re-sending message for redundancy...")
    node_a.send(msg)

    print("[TEST] Waiting for delivery...")
    time.sleep(4)

    print("[TEST] Stopping nodes...")
    node_a.stop()
    node_b.stop()

    print("[TEST] Done.")

if __name__ == "__main__":
    test_message_coms()
