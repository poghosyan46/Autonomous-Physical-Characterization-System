import os
import json
import logging
import matplotlib.pyplot as plt
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("GeneratePlots")


def generate_scientific_plots():
    data_path = os.path.join("data", "experiment_data.json")
    output_img = os.path.join("data", "plots_output.png")

    if not os.path.exists(data_path):
        logger.error(f"{data_path} not found!")
        return False

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    fig, axs = plt.subplots(2, 2, figsize=(11, 8.5), dpi=300)
    plt.subplots_adjust(hspace=0.35, wspace=0.3)

    # Panel 1: I-V Sweep
    if "iv_sweep" in data and data["iv_sweep"].get("status") == "success":
        pts = data["iv_sweep"]["data"]
        v = [p["voltage_V"] for p in pts]
        i = [p["current_A"] * 1e6 for p in pts]
        axs[0, 0].plot(v, i, "o-", color="#1f77b4", linewidth=2, markersize=4)
        axs[0, 0].set_title("Full-Range I-V Sweep", fontsize=11, fontweight="bold")
        axs[0, 0].set_xlabel("Voltage (V)")
        axs[0, 0].set_ylabel("Current (µA)")
        axs[0, 0].grid(True, linestyle="--", alpha=0.6)

    # Panel 2: Adaptive Fine Sweep
    if "adaptive_fine_sweep" in data and data["adaptive_fine_sweep"].get("status") == "success":
        pts = data["adaptive_fine_sweep"]["data"]
        v = [p["voltage_V"] for p in pts]
        i = [p["current_A"] * 1e6 for p in pts]
        axs[0, 1].plot(v, i, "s-", color="#ff7f0e", linewidth=1.8, markersize=3)
        axs[0, 1].set_title("Adaptive High-Density Scan", fontsize=11, fontweight="bold")
        axs[0, 1].set_xlabel("Voltage (V)")
        axs[0, 1].set_ylabel("Current (µA)")
        axs[0, 1].grid(True, linestyle="--", alpha=0.6)

    # Panel 3: Hysteresis Loop
    if "hysteresis" in data and data["hysteresis"].get("status") == "success":
        pts = data["hysteresis"]["data"]
        v = [p["voltage_V"] for p in pts]
        i = [p["current_A"] * 1e6 for p in pts]
        axs[1, 0].plot(v, i, "-", color="#2ca02c", linewidth=1.5)
        axs[1, 0].set_title("Hysteresis Cyclic Sweep", fontsize=11, fontweight="bold")
        axs[1, 0].set_xlabel("Voltage (V)")
        axs[1, 0].set_ylabel("Current (µA)")
        axs[1, 0].grid(True, linestyle="--", alpha=0.6)

    # Panel 4: Time-Series I(t)
    if "time_series_it" in data and data["time_series_it"].get("status") == "success":
        pts = data["time_series_it"]["data"]
        t = [p.get("time_sec", idx) for idx, p in enumerate(pts)]
        i = [p["current_A"] * 1e6 for p in pts]
        axs[1, 1].plot(t, i, "d-", color="#d62728", linewidth=2, markersize=4)
        axs[1, 1].set_title("Dynamic Time-Series I(t)", fontsize=11, fontweight="bold")
        axs[1, 1].set_xlabel("Time (s)")
        axs[1, 1].set_ylabel("Current (µA)")
        axs[1, 1].grid(True, linestyle="--", alpha=0.6)

    plt.savefig(output_img, bbox_inches="tight")
    plt.close()
    logger.info(f"Successfully generated scientific plots at {output_img}")
    return True


if __name__ == "__main__":
    generate_scientific_plots()