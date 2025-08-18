import multiprocessing
import time
from peer_node import PeerNode  # assuming local import, not subprocess

RUN_TIME_MINUTES = 30
GROUP_NAME = "mktl-perf"
ROLES = ["small", "medium", "large", "x-large"]
PEERS_PER_ROLE = 25

def launch_peer(index, role):
    node = PeerNode(
        name=f"{role}-node-{index}",
        group=GROUP_NAME,
        role=role,
        log_dir="logs"
    )
    node.run()

if __name__ == "__main__":
    print(f"[launcher] Launching {PEERS_PER_ROLE * len(ROLES)} nodes...")
    processes = []

    for role in ROLES:
        for i in range(PEERS_PER_ROLE):
            p = multiprocessing.Process(target=launch_peer, args=(i, role))
            p.start()
            processes.append(p)
            time.sleep(0.2)  # stagger to reduce startup contention

    print(f"[launcher] All nodes started. Running for {RUN_TIME_MINUTES} minutes...")
    try:
        time.sleep(RUN_TIME_MINUTES * 60)
    except KeyboardInterrupt:
        print("[launcher] Keyboard interrupt received. Terminating processes...")

    print("[launcher] Test complete. Terminating all processes...")
    for p in processes:
        p.terminate()
        p.join()

    print("[launcher] All nodes shut down.")
