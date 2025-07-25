import time
import ctypes
import czmq
from zyre_utils import setup_zyre_node, get_peer_uuids

node = setup_zyre_node(
    name=b"node-c",
    group=b"buddies",
    gossip_connect=b"tcp://127.0.0.1:9999"
)

time.sleep(5)
peer_uuids = get_peer_uuids(node.peers())

libczmq = ctypes.CDLL("libczmq.dylib")
libczmq.zmsg_new.restype = czmq.zmsg_p
libczmq.zmsg_addstr.argtypes = [czmq.zmsg_p, ctypes.c_char_p]

def make_zmsg(text: str) -> czmq.zmsg_p:
    zmsg = libczmq.zmsg_new()
    libczmq.zmsg_addstr(zmsg, text.encode("utf-8"))
    return zmsg

if peer_uuids:
    target_uuid = peer_uuids[0]
    print(f"[node-c] Whispering to {target_uuid}")
    msg = make_zmsg("Hello from node-c (WHISPER)")
    node.whisper(target_uuid.encode(), msg)
else:
    print("[node-c] No peers to whisper to.")

node.stop()

