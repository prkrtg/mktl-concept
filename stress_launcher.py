import multiprocessing
import subprocess
import random
import time
import os

ROLES = ["low", "medium", "high", "hungry"]
NODES_PER_ROLE = 25
TOTAL_NODES = NODES_PER_ROLE * len(ROLES)
RUN_TIME_MINUTES = 30

def launch_peer(index, role):
    env = os.environ.copy()
    cmd = ["python3", "peer_node.py", f"--name=node-{index}", f"--role={role}"]
    subprocess.run(cmd, env=env)

if __name__ == "__main__":
    print(f"[launcher] Launching {TOTAL_NODES} nodes...")
    processes = []

    # Assign 25 nodes per role
    roles_list = []
    for role in ROLES:
        roles_list.extend([role] * NODES_PER_ROLE)
    random.shuffle(roles_list)

    for i in range(TOTAL_NODES):
        p = multiprocessing.Process(target=launch_peer, args=(i, roles_list[i]))
        p.start()
        processes.append(p)
        time.sleep(0.1)  # small stagger to reduce contention at startup

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
