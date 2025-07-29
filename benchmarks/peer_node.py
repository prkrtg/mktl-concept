import os
import time
import uuid
import random
import argparse
import logging
import ctypes
import czmq
import csv

from zyre_utils import setup_zyre_node, get_peer_uuids, parse_msg_frames

# zmsg helpers
libczmq = ctypes.CDLL("libczmq.dylib")
libczmq.zmsg_new.restype = czmq.zmsg_p
libczmq.zmsg_addstr.argtypes = [czmq.zmsg_p, ctypes.c_char_p]

def make_zmsg(text: str) -> czmq.zmsg_p:
    zmsg = libczmq.zmsg_new()
    libczmq.zmsg_addstr(zmsg, text.encode("utf-8"))
    return zmsg

def make_payload(role: str):
    if role == "low":
        return "ping"
    elif role == "medium":
        return "M" * (500 * 1024)
    elif role == "high":
        return "H" * (2 * 1024 * 1024)
    elif role == "hungry":
        return "X" * (50 * 1024 * 1024)
    else:
        raise ValueError(f"Unknown role: {role}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", required=True)
    parser.add_argument("--log-dir", default="logs")
    parser.add_argument("--group", default="bench")
    parser.add_argument("--shout-rate", type=float, default=1.0)
    parser.add_argument("--whisper-rate", type=float, default=1.0)
    parser.add_argument("--role", choices=["low", "medium", "high", "hungry"], default=None)
    args = parser.parse_args()

    os.makedirs(args.log_dir, exist_ok=True)
    log_path_txt = os.path.join(args.log_dir, f"{args.id}.log")
    log_path_csv = os.path.join(args.log_dir, f"{args.id}.csv")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(message)s",
        handlers=[logging.FileHandler(log_path_txt), logging.StreamHandler()]
    )

    role = args.role or random.choice(["low", "medium", "high", "hungry"])
    logging.info(f"[{args.id}] Starting with role: {role}")

    node = setup_zyre_node(name=args.id.encode(), group=args.group.encode())

    logging.info(f"[{args.id}] Waiting for peers...")
    peer_uuid = None
    while not peer_uuid:
        peers = get_peer_uuids(node.peers())
        if peers:
            peer_uuid = peers[0]
            logging.info(f"[{args.id}] Found peer {peer_uuid}")
        time.sleep(0.5)

    payload = make_payload(role)

    last_shout = time.time()
    last_whisper = time.time()

    with open(log_path_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["msg_id", "rtt", "sent_time", "recv_time", "peer", "mode", "role"])
        writer.writeheader()

    while True:
        now = time.time()

        if args.shout_rate > 0 and now - last_shout >= 1 / args.shout_rate:
            last_shout = now
            msg_id = str(uuid.uuid4())
            msg = make_zmsg(f"{msg_id} {now}")
            node.shout(args.group.encode(), msg)
            with open(log_path_csv, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["msg_id", "rtt", "sent_time", "recv_time", "peer", "mode", "role"])
                writer.writerow({
                    "msg_id": msg_id,
                    "rtt": 0,
                    "sent_time": now,
                    "recv_time": 0,
                    "peer": "ALL",
                    "mode": "SHOUT",
                    "role": role
                })

        if args.whisper_rate > 0 and now - last_whisper >= 1 / args.whisper_rate:
            last_whisper = now
            msg_id = str(uuid.uuid4())
            msg = make_zmsg(f"{msg_id} {now}")
            node.whisper(peer_uuid.encode(), msg)
            with open(log_path_csv, "a", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["msg_id", "rtt", "sent_time", "recv_time", "peer", "mode", "role"])
                writer.writerow({
                    "msg_id": msg_id,
                    "rtt": 0,
                    "sent_time": now,
                    "recv_time": 0,
                    "peer": peer_uuid,
                    "mode": "WHISPER",
                    "role": role
                })

        msg = node.recv()
        if msg:
            frames = parse_msg_frames(msg)
            if len(frames) >= 4:
                event = frames[0]
                peer = frames[1]
                content = frames[3]
                try:
                    payload = content.decode()
                    parts = payload.split()
                    if len(parts) == 2:
                        msg_id, sent_time = parts
                        recv_time = time.time()
                        latency = recv_time - float(sent_time)
                        with open(log_path_csv, "a", newline="") as f:
                            writer = csv.DictWriter(f, fieldnames=["msg_id", "rtt", "sent_time", "recv_time", "peer", "mode", "role"])
                            writer.writerow({
                                "msg_id": msg_id,
                                "rtt": latency,
                                "sent_time": sent_time,
                                "recv_time": recv_time,
                                "peer": peer.decode(errors="ignore"),
                                "mode": "RECV",
                                "role": role
                            })
                        logging.info(f"[{args.id}] Received {event.decode()} from {peer.decode(errors='ignore')} latency={latency:.4f}")
                except Exception as e:
                    logging.warning(f"[{args.id}] Could not decode message: {e}")

        time.sleep(0.001)

if __name__ == "__main__":
    main()
