import argparse
import multiprocessing
import subprocess
import time
import signal
import os
import sys
from datetime import datetime

peer_processes = []

def launch_peer(peer_id, group, shout_rate, whisper_rate, log_dir):
    """Launch a peer_node.py process with unique ID and args."""
    env = os.environ.copy()
    cmd = [
        sys.executable, "peer_node.py",
        "--id", f"peer-{peer_id}",
        "--group", group,
        "--shout-rate", str(shout_rate),
        "--whisper-rate", str(whisper_rate),
        "--log-dir", log_dir
    ]
    return subprocess.Popen(cmd, env=env)

def terminate_all():
    print("\n[launcher] Terminating all peer processes...")
    for proc in peer_processes:
        proc.terminate()
    for proc in peer_processes:
        proc.wait()
    log("[launcher] All peers terminated.")

def main():
    parser = argparse.ArgumentParser(description="Zyre Stress Test Launcher")
    parser.add_argument("--max-peers", type=int, default=100, help="Maximum number of peer nodes")
    parser.add_argument("--interval", type=float, default=0.2, help="Interval (sec) between adding peers")
    parser.add_argument("--shout-rate", type=float, default=1.0, help="SHOUT interval (sec) per peer")
    parser.add_argument("--whisper-rate", type=float, default=1.5, help="WHISPER interval (sec) per peer")
    parser.add_argument("--group", type=str, default="bench", help="Zyre group name")
    parser.add_argument("--log-dir", type=str, default="logs", help="Directory for peer logs")
    args = parser.parse_args()

    os.makedirs(args.log_dir, exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    logfile = open("logs/launcher.log", "a")

    def log(msg):
        timestamp = datetime.now().isoformat(timespec="seconds")
        logfile.write(f"[{timestamp}] {msg}\n")
        logfile.flush()

    def handle_sigint(sig, frame):
        terminate_all()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_sigint)

    log(f"[launcher] Starting stress test with max {args.max_peers} peers...")

    for i in range(args.max_peers):
        proc = launch_peer(i, args.group, args.shout_rate, args.whisper_rate, args.log_dir)
        peer_processes.append(proc)
        log(f"[launcher] Started peer-{i}")
        time.sleep(args.interval)

    log("[launcher] All peers launched. Press Ctrl+C to stop.")
    for proc in peer_processes:
        proc.wait()

if __name__ == "__main__":
    main()

