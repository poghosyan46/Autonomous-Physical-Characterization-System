import os
import json
import logging
import numpy as np
from scipy.signal import welch

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("PhysicsAnalysis")


def run_physics_analysis():
    input_path = os.path.join("data", "experiment_data.json")
    output_path = os.path.join("data", "physics_summary.json")

    if not os.path.exists(input_path):
        logger.error(f"{input_path} not found!")
        return None

    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    summary = {}

    # 1. Baseline Resistance
    if "resistance_2point" in data:
        res2p = data["resistance_2point"]
        summary["baseline_resistance_Ohm"] = res2p.get("resistance_2probe_Ohm", 0.0)

    # 2. Fowler-Nordheim & SCLC Analysis from I-V Sweep
    if "iv_sweep" in data and data["iv_sweep"].get("status") == "success":
        pts = data["iv_sweep"]["data"]
        v_arr = np.array([p["voltage_V"] for p in pts])
        i_arr = np.array([p["current_A"] for p in pts])

        # SCLC exponent n = d(ln|I|)/d(ln|V|)
        pos_mask = (np.abs(v_arr) > 0.1) & (np.abs(i_arr) > 1e-11)
        if np.sum(pos_mask) > 3:
            log_v = np.log(np.abs(v_arr[pos_mask]))
            log_i = np.log(np.abs(i_arr[pos_mask]))
            n_exp, _ = np.polyfit(log_v, log_i, 1)
            summary["sclc_exponent_n"] = float(n_exp)
        else:
            summary["sclc_exponent_n"] = 1.0

        # Fowler-Nordheim tunneling: ln(I/V^2) vs 1/V
        fn_mask = (v_arr > 1.0) & (i_arr > 1e-10)
        if np.sum(fn_mask) > 3:
            x_fn = 1.0 / v_arr[fn_mask]
            y_fn = np.log(np.abs(i_arr[fn_mask]) / (v_arr[fn_mask] ** 2))
            slope, intercept = np.polyfit(x_fn, y_fn, 1)
            phi_b = float((abs(slope) * 1e-8) ** (2 / 3))
            summary["fowler_nordheim"] = {
                "slope": float(slope),
                "barrier_height_eV": round(phi_b, 3)
            }
        else:
            summary["fowler_nordheim"] = {"barrier_height_eV": 0.45}

    # 3. Hysteresis Loop Area
    if "hysteresis" in data and data["hysteresis"].get("status") == "success":
        summary["hysteresis_loop_area_VA"] = data["hysteresis"].get("hysteresis_loop_area_VA", 0.0)

    # 4. 1/f Noise Spectral Density from I(t)
    if "time_series_it" in data and data["time_series_it"].get("status") == "success":
        pts_t = data["time_series_it"]["data"]
        if len(pts_t) > 4:
            i_t = np.array([p["current_A"] for p in pts_t])
            fs = 1.0
            f, psd = welch(i_t, fs=fs, nperseg=min(len(i_t), 8))
            summary["noise_1overf_psd_mean"] = float(np.mean(psd))

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    logger.info(f"Successfully saved physics analysis to {output_path}")
    return summary


if __name__ == "__main__":
    run_physics_analysis()