import os
import zyre
import ctypes
import time

def setup_zyre_node(name: bytes, group: bytes, interface: bytes = b"en0",
                    gossip_bind: bytes = None, gossip_connect: bytes = None,
                    verbose: bool = True) -> zyre.Zyre:
    """Create and configure a Zyre node with optional gossip and group join."""
    if verbose:
        os.environ["ZYRE_LOG"] = "1"

    node = zyre.Zyre(name)
    node.set_interface(interface)
    if verbose:
        node.set_verbose()

    if gossip_bind:
        node.gossip_bind(gossip_bind)
    if gossip_connect:
        node.gossip_connect(gossip_connect)

    node.start()
    node.join(group)

    print(f"[{name.decode()}] Started and joined group '{group.decode()}'")
    return node

def get_peer_uuids(zlist_ptr):
    """Extract peer UUIDs from a zlist_t* returned by node.peers()."""
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

def parse_msg_frames(msg):
    """Convert zmsg_t* into a list of bytes frames."""
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
    return frames

def log_event(frames, node_label="[node]"):
    if len(frames) >= 3:
        event_type = frames[0]
        peer_uuid  = frames[1]
        sender     = frames[2]

        if event_type == b'JOIN':
            print(f"{node_label} JOIN from {sender.decode()} ({peer_uuid.decode()})")
        elif event_type == b'SHOUT' and len(frames) >= 4:
            content = frames[3]
            print(f"{node_label} SHOUT from {peer_uuid.decode()}: {content.decode()}")
        elif event_type == b'WHISPER' and len(frames) >= 4:
            content = frames[3]
            print(f"{node_label} WHISPER from {peer_uuid.decode()}: {content.decode()}")
        elif event_type == b'ENTER':
            print(f"{node_label} ENTER: {peer_uuid.decode()}")
        elif event_type == b'EXIT':
            print(f"{node_label} EXIT: {peer_uuid.decode()}")
        else:
            print(f"{node_label} Unknown event type: {event_type}")
    else:
        print(f"{node_label} Incomplete message: {frames}")

