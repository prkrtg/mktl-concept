import os
import time
import zyre
import ctypes

# Enable verbose logging
os.environ["ZYRE_LOG"] = "1"

# Start Zyre node
node = zyre.Zyre(b"node-b")
node.set_interface(b"en0")
node.start()
node.join(b"buddies")
print("[node-b] Started and joined 'buddies'")
print("[node-b] Waiting for events...")

try:
    while True:
        msg = node.recv()
        if msg is None:
            continue

        # Safely extract all frames as bytes
        frames = []
        frame = msg.first()
        while frame:
            data_ptr = frame.data()
            size = frame.size()
            if data_ptr and size > 0:
                data = ctypes.string_at(data_ptr, size)
                frames.append(data)
            else:
                frames.append(b"")
            frame = msg.next()

        print(f"[node-b] Received event with {len(frames)} frame(s)")

        if len(frames) >= 3:
            event_type = frames[0]
            peer_uuid  = frames[1]
            sender     = frames[2]

            if event_type == b'JOIN':
                print(f"[node-b] JOIN from {sender.decode()} ({peer_uuid.decode()})")

            elif event_type == b'SHOUT' and len(frames) >= 4:
                content = frames[3]
                print(f"[node-b] SHOUT from {peer_uuid.decode()}: {content.decode()}")

            elif event_type == b'ENTER':
                print(f"[node-b] Peer ENTER: {peer_uuid.decode()}")

            elif event_type == b'EXIT':
                print(f"[node-b] Peer EXIT: {peer_uuid.decode()}")
            else:
                print(f"[node-b] Unknown or unhandled event: {event_type}")

        else:
            print("[node-b] Incomplete message received:", frames)

        time.sleep(0.1)

except KeyboardInterrupt:
    print("\n[node-b] Shutting down...")
    node.stop()

