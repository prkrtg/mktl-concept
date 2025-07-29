import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# --- Directories ---
LOG_DIR = "logs"
OUT_DIR = LOG_DIR
os.makedirs(OUT_DIR, exist_ok=True)

# --- Load and concatenate all CSV logs ---
expected_columns = ["msg_id", "rtt", "sent_time", "recv_time", "peer", "mode", "role"]
df_list = []

for csv_file in os.listdir(LOG_DIR):
    if csv_file.endswith(".csv"):
        path = os.path.join(LOG_DIR, csv_file)
        try:
            df = pd.read_csv(path, names=expected_columns, skiprows=1)
            df["timestamp"] = pd.to_datetime(df["sent_time"], unit="s", errors="coerce")
            df = df.dropna(subset=["timestamp"])
            df_list.append(df)
        except Exception as e:
            print(f"⚠️ Skipping {csv_file}: {e}")

if not df_list:
    print("No valid CSV files found.")
    exit(1)

df_all = pd.concat(df_list, ignore_index=True)

# --- Plot 1: Latency over time ---
plt.figure()
sns.lineplot(data=df_all, x="timestamp", y="rtt", hue="role")
plt.title("Latency Over Time by Role")
plt.xlabel("Time")
plt.ylabel("RTT (s)")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "plot_latency_over_time.png"))
plt.close()

# --- Plot 2: Latency histogram ---
df_valid = df_all[df_all["rtt"].notnull() & (df_all["rtt"] > 0)]
plt.figure()
try:
    sns.histplot(df_valid, x="rtt", hue="role", bins=50, kde=False)
    plt.title("Latency Distribution by Role")
    plt.xlabel("RTT (s)")
    plt.tight_layout()
    plt.savefig(os.path.join(OUT_DIR, "plot_latency_histogram.png"))
    plt.close()
except ValueError as e:
    print("⚠️ Histogram skipped due to insufficient data:", e)

# --- Plot 3: Messages per second ---
df_all["second"] = df_all["timestamp"].dt.floor("S")
msgs_per_sec = df_all.groupby("second").size().reset_index(name="message_count")

plt.figure()
sns.lineplot(data=msgs_per_sec, x="second", y="message_count")
plt.title("Messages Per Second (All Events)")
plt.xlabel("Time")
plt.ylabel("Message Count")
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig(os.path.join(OUT_DIR, "plot_throughput.png"))
plt.close()

print("Plots saved to:", OUT_DIR)
