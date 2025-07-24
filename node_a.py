import os
import time
import ctypes
import zyre
import czmq

# Enable verbose Zyre/CZMQ logging
os.environ["ZYRE_LOG"] = "1"

# Helper to extract peer UUIDs
def get_peer_uuids(zlist_ptr):
    if not zlist_ptr:
        return []
    uuids = []
    peer = zlist_ptr.first()
    while peer:
        uuid_cstr = ctypes.cast(peer, ctypes.c_char_p).value
        if uuid_cstr:
            uuids.append(uuid_cstr.decode())
        peer = zlist_ptr.next()
    return uuids

# Zyre setup
node = zyre.Zyre(b"node-a")
node.set_interface(b"en0")  # Set correct interface (macOS Wi-Fi is usually en0)
node.start()
node.join(b"buddies")

print("[node-a] Started and joined 'buddies'")
print("[node-a] Waiting 5s for peer discovery...")
time.sleep(5)

# Check and print discovered peers
peers = node.peers()
peer_uuids = get_peer_uuids(peers)
if peer_uuids:
    print("[node-a] Peers discovered:")
    for uuid in peer_uuids:
        print("  -", uuid)
else:
    print("[node-a] No peers discovered.")

# Set up zmsg creation using ctypes bindings
libczmq = ctypes.CDLL("libczmq.dylib")
libczmq.zmsg_new.restype = czmq.zmsg_p
libczmq.zmsg_addstr.argtypes = [czmq.zmsg_p, ctypes.c_char_p]

def make_zmsg(text: str) -> czmq.zmsg_p:
    zmsg = libczmq.zmsg_new()
    libczmq.zmsg_addstr(zmsg, text.encode("utf-8"))
    return zmsg

# Send messages to group
for i in range(3):
    message = f"Hello #{i} from node-a"
    zmsg = make_zmsg(message)
    node.shout(b"buddies", zmsg)
    print(f"[node-a] Sent: {message}")
    time.sleep(1)

print("[node-a] Done, shutting down...")
node.stop()

