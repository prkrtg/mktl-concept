import argparse
import multiprocessing
import time
import os
import sys
import signal
from datetime import datetime
from multiprocessing import Process

peer_processes = []
should_terminate = multiprocessing.Event()


def launch_peer_process(peer_id, group, shout_rate, whisper_rate, log_dir):
    """Target function to run peer_node.py as a Python subprocess."""
    cmd = [
        sys.executable, "peer_node.py",
        "--id", f"peer-{peer_id}",
        "--group", group,
        "--shout-rate", str(shout_rate),
        "--whisper-rate", str(whisper_rate),
        "--log-dir", log_dir
    ]
    os.execv(sys.executable, cmd)  # Replaces current process with peer_node


def start_peer(peer_id, group, shout_rate, whisper_rate, log_dir):
    p = Process(
        target=launch_peer_process,
        args=(peer_id, group, shout_rate, whisper_rate, log_dir),
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
    parser = argparse.ArgumentParser(description="Zyre Stress Test Launcher (multiprocessing version)")
    parser.add_argument("--max-peers", type=int, default=100)
    parser.add_argument("--interval", type=float, default=0.2)
    parser.add_argument("--shout-rate", type=float, default=1.0)
    parser.add_argument("--whisper-rate", type=float, default=1.5)
    parser.add_argument("--group", type=str, default="bench")
    parser.add_argument("--log-dir", type=str, default="logs")
    args = parser.parse_args()

    os.makedirs(args.log_dir, exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    logfile = open("logs/launcher.log", "a")

    def log(msg):
        timestamp = datetime.now().isoformat(timespec="seconds")
        logfile.write(f"[{timestamp}] {msg}\n")
        logfile.flush()

    def handle_sigint(sig, frame):
        should_terminate.set()
        terminate_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    log(f"[launcher] Starting stress test with {args.max_peers} peers")

    for i in range(args.max_peers):
        if should_terminate.is_set():
            break
        proc = start_peer(i, args.group, args.shout_rate, args.whisper_rate, args.log_dir)
        peer_processes.append(proc)
        log(f"[launcher] Started peer-{i}")
        time.sleep(args.interval)

    log("[launcher] All peers launched. Press Ctrl+C to stop.")
    for proc in peer_processes:
        proc.join()


if __name__ == "__main__":
    main()
