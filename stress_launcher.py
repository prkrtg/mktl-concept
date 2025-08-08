import multiprocessing
import time
from peer_node import PeerNode  # direct import, no subprocess

TOTAL_NODES = 30
RUN_TIME_MINUTES = 30
GROUP_NAME = "mktl-perf"

def launch_peer(index):
    node = PeerNode(
        name=f"node-{index}",
        group=GROUP_NAME,
        role="standard",   # you can change per-node if needed
        log_dir="logs"
    )
    node.run()  # blocks until the node finishes

if __name__ == "__main__":
    print(f"[launcher] Launching {TOTAL_NODES} nodes...")
    processes = []

    for i in range(TOTAL_NODES):
        p = multiprocessing.Process(target=launch_peer, args=(i,))
        p.start()
        processes.append(p)
        time.sleep(0.2)  # slightly larger stagger to reduce startup contention

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
