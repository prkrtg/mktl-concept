import os
import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import zscore
import glob

# Constants
LOG_DIR = "logs"
OUT_DIR = "normalized_logs"
os.makedirs(OUT_DIR, exist_ok=True)

def load_and_concatenate_logs(log_dir):
    """Load all CSV logs from a directory into a single DataFrame."""
    csv_files = glob.glob(os.path.join(log_dir, "*.csv"))
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {log_dir}")

    dfs = []
    for csv_file in csv_files:
        df = pd.read_csv(csv_file)
        df["source_file"] = os.path.basename(csv_file)
        dfs.append(df)
    return pd.concat(dfs, ignore_index=True)

def normalize_rtt_by_role(df):
    """Add z-score normalization for RTT within each role group."""
    df = df.copy()
    df["rtt"] = pd.to_numeric(df["rtt"], errors="coerce")
    df = df[df["mode"] == "RECV"]
    df = df.dropna(subset=["rtt"])
    df["rtt_zscore"] = df.groupby("role")["rtt"].transform(zscore)
    return df

def save_normalized_data(df, out_dir):
    """Save normalized data per original source file."""
    os.makedirs(out_dir, exist_ok=True)
    for file_name, group_df in df.groupby("source_file"):
        out_file = os.path.join(out_dir, file_name)
        group_df.to_csv(out_file, index=False)

def plot_rtt_histograms(df):
    """Plot histogram of RTTs per role."""
    roles = df["role"].unique()
    for role in roles:
        subset = df[df["role"] == role]
        plt.figure()
        plt.hist(subset["rtt"], bins=50, alpha=0.7)
        plt.title(f"RTT Histogram for Role: {role}")
        plt.xlabel("RTT (sec)")
        plt.ylabel("Count")
        plt.grid(True)
        plt.tight_layout()
        plt.savefig(f"histogram_{role}.png")

def plot_rtt_zscore_vs_time(df):
    """Scatterplot of RTT z-score over elapsed time (minutes) since first receive."""
    if df is None or df.empty:
        print("[plot] No data to plot.")
        return

    df = df.copy()
    df["recv_time"] = pd.to_numeric(df["recv_time"], errors="coerce")
    df = df.dropna(subset=["recv_time", "rtt_zscore", "role"])
    if df.empty:
        print("[plot] No valid rows after cleaning.")
        return

    # Normalize to elapsed minutes from the first recv_time
    start = df["recv_time"].min()
    df["elapsed_min"] = (df["recv_time"] - start) / 60.0
    df = df.sort_values("elapsed_min")

    plt.figure(figsize=(10, 6))
    for role in df["role"].dropna().unique():
        subset = df[df["role"] == role]
        if subset.empty:
            continue
        plt.scatter(subset["elapsed_min"], subset["rtt_zscore"], label=role, alpha=0.6, s=10)

    plt.title("RTT Z-Score Over Time by Role")
    plt.xlabel("Elapsed Time (minutes)")
    plt.ylabel("RTT Z-Score")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig("rtt_zscore_vs_time.png")


df_logs = load_and_concatenate_logs(LOG_DIR)
df_normalized = normalize_rtt_by_role(df_logs)
save_normalized_data(df_normalized, OUT_DIR)
plot_rtt_histograms(df_normalized)
plot_rtt_zscore_vs_time(df_normalized)
