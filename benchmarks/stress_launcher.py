import argparse
import multiprocessing
import time
import os
import sys
import signal
from datetime import datetime
from peer_node import PeerNode, setup_zyre_node
import random

peer_processes = []
should_terminate = multiprocessing.Event()


def launch_peer_process(peer_id, group, shout_rate, whisper_rate, log_dir, role=None):
    """Target function to run PeerNode and pass the node object."""
    if role is None:
        role = random.choice(["low", "medium", "high", "hungry"])

    # Setup the Zyre node
    node = setup_zyre_node(name=f"peer-{peer_id}".encode(), group=group.encode())

    # Now create the PeerNode with the setup node
    peer_node = PeerNode(
        peer_id=f"peer-{peer_id}",
        group=group,
        shout_rate=shout_rate,
        whisper_rate=whisper_rate,
        log_dir=log_dir,
        role=role
    )

    peer_node.run(node)

def start_peer(peer_id, group, shout_rate, whisper_rate, log_dir, role="low"):
    """Start PeerNode in a separate process."""
    p = multiprocessing.Process(
        target=launch_peer_process,
        args=(peer_id, group, shout_rate, whisper_rate, log_dir, role),  # Include role in args
        daemon=False
    )
    p.start()
    return p


def terminate_all():
    print("\n[launcher] Terminating all peer processes...")
    for proc in peer_processes:
        if proc.is_alive():
            proc.terminate()
    for proc in peer_processes:
        proc.join()
    print("[launcher] All peers terminated.")


def main():
    parser = argparse.ArgumentParser(description="Zyre Stress Test Launcher")
    parser.add_argument("--max-peers", type=int, default=100)
    parser.add_argument("--interval", type=float, default=0.2)
    parser.add_argument("--shout-rate", type=float, default=1.0)
    parser.add_argument("--whisper-rate", type=float, default=1.5)
    parser.add_argument("--group", type=str, default="bench")
    parser.add_argument("--log-dir", type=str, default="logs")
    parser.add_argument("--role", choices=["low", "medium", "high", "hungry"], default="low")  # Default role added
    args = parser.parse_args()

    os.makedirs(args.log_dir, exist_ok=True)
    logfile = open("logs/launcher.log", "a")

    def log(msg):
        timestamp = datetime.now().isoformat(timespec="seconds")
        logfile.write(f"[{timestamp}] {msg}\n")
        logfile.flush()

    def handle_sigint(sig, frame):
        should_terminate.set()
        log("Interrupt received. Terminating peers...")
        for proc in peer_processes:
            if proc.is_alive():
                proc.terminate()
        for proc in peer_processes:
            proc.join()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    for i in range(args.max_peers):
        if should_terminate.is_set():
            break
        proc = start_peer(i, args.group, args.shout_rate, args.whisper_rate, args.log_dir, args.role)
        peer_processes.append(proc)
        log(f"Started peer-{i}")
        time.sleep(args.interval)

    log("All peers launched. Press Ctrl+C to stop.")
    for proc in peer_processes:
        proc.join()


if __name__ == "__main__":
    main()
