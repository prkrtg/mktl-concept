import os
import time
import ctypes
import zyre
import czmq

os.environ["ZYRE_LOG"] = "1"

# Helper to extract UUIDs from node.peers()
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

# Helper to create zmsg_t* from string
libczmq = ctypes.CDLL("libczmq.dylib")
libczmq.zmsg_new.restype = czmq.zmsg_p
libczmq.zmsg_addstr.argtypes = [czmq.zmsg_p, ctypes.c_char_p]

def make_zmsg(text: str) -> czmq.zmsg_p:
    zmsg = libczmq.zmsg_new()
    libczmq.zmsg_addstr(zmsg, text.encode("utf-8"))
    return zmsg

# Create node
node = zyre.Zyre(b"node-c")
node.set_interface(b"en0")
node.start()
node.join(b"buddies")

print("[node-c] Started and joined 'buddies'")
print("[node-c] Waiting for peer discovery...")
time.sleep(5)

peers = node.peers()
peer_uuids = get_peer_uuids(peers)

if peer_uuids:
    target_uuid = peer_uuids[0]
    print(f"[node-c] Whispering to {target_uuid}")
    msg = make_zmsg("Hello from node-c (WHISPER)")
    node.whisper(target_uuid.encode(), msg)
else:
    print("[node-c] No peers discovered to WHISPER to.")

print("[node-c] Done. Shutting down.")
node.stop()

