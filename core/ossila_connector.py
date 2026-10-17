import serial
import time
import logging
import json
import re

logger = logging.getLogger("OssilaConnector")

_shared_connector_instance = None


def get_shared_connector(port="COM3", baudrate=115200):
    global _shared_connector_instance
    if _shared_connector_instance is None:
        _shared_connector_instance = OssilaConnector(port=port, baudrate=baudrate)
    return _shared_connector_instance


def range_list(start: float, stop: float, num: int):
    if num <= 1:
        return [start]
    step = (stop - start) / (num - 1)
    return [start + i * step for i in range(num)]


class OssilaConnector:
    def __init__(self, port="COM3", baudrate=115200, min_v=-1.2, max_v=1.2):
        self.port = port
        self.baudrate = baudrate
        self.min_v = min_v  # Software safety limit for low resistance samples
        self.max_v = max_v
        self.ser = None
        logger.info(f"Initialized PySerial OssilaConnector on {port} (Safety Voltage Limit: [{min_v}V, {max_v}V])")

    def _get_serial(self):
        if self.ser is None or not self.ser.is_open:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1.0)
            time.sleep(0.2)
        return self.ser

    def close(self):
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(b"smu1 set enabled 0\r\n")
                time.sleep(0.05)
            except Exception:
                pass
            self.ser.close()
            self.ser = None

    def enable_channel(self, enabled: bool = True, channel: str = "smu1"):
        try:
            s = self._get_serial()
            cmd = f"{channel} set enabled {1 if enabled else 0}\r\n"
            s.write(cmd.encode("ascii"))
            time.sleep(0.05)
        except Exception as e:
            logger.error(f"Error setting channel state: {e}")

    def measure_point(self, voltage: float, channel: str = "smu1") -> dict:
        v_clamped = max(self.min_v, min(self.max_v, voltage))
        try:
            s = self._get_serial()
            s.reset_input_buffer()

            s.write(f"{channel} set voltage {v_clamped:.4f}\r\n".encode("ascii"))
            time.sleep(0.01)

            s.write(f"{channel} measure\r\n".encode("ascii"))
            
            raw_bytes = s.readline()
            raw = raw_bytes.decode("ascii", errors="ignore").strip()

            v_meas, i_meas = v_clamped, 0.0
            parsed_successfully = False

            if raw:
                try:
                    if raw.startswith("[") and raw.endswith("]"):
                        parsed = json.loads(raw)
                        v_meas, i_meas = float(parsed[0]), float(parsed[1])
                        parsed_successfully = True
                    else:
                        nums = [float(x) for x in re.findall(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", raw)]
                        if len(nums) >= 2:
                            v_meas, i_meas = nums[0], nums[1]
                            parsed_successfully = True
                except Exception:
                    pass

            if parsed_successfully:
                logger.info(f"MEASURED [{channel}]: V={v_meas:.4f}V, I={i_meas:.4e}A")

            return {
                "status": "success",
                "voltage_V": float(v_meas),
                "current_A": float(i_meas),
                "power_W": float(v_meas * i_meas),
                "channel": channel,
                "mode": "hardware" if parsed_successfully else "fallback"
            }
        except Exception as e:
            logger.error(f"Hardware exception: {e}")
            return {"status": "error", "message": str(e)}

    def sweep_voltage(self, start_v: float = -1.0, stop_v: float = 1.0, steps: int = 15, channel: str = "smu1") -> dict:
        self.enable_channel(True, channel=channel)
        v_list = range_list(start_v, stop_v, steps)
        data = []
        for v in v_list:
            res = self.measure_point(v, channel=channel)
            if res["status"] == "success":
                data.append(res)
        self.enable_channel(False, channel=channel)
        return {"status": "success", "count": len(data), "data": data}

    def hysteresis_sweep(self, v_max: float = 1.0, steps_per_branch: int = 6, channel: str = "smu1") -> dict:
        self.enable_channel(True, channel=channel)
        v_max_safe = min(self.max_v, abs(v_max))
        b1 = range_list(0, v_max_safe, steps_per_branch)
        b2 = range_list(v_max_safe, -v_max_safe, steps_per_branch * 2)
        b3 = range_list(-v_max_safe, 0, steps_per_branch)
        full_sweep = b1 + b2[1:] + b3[1:]

        data = []
        for v in full_sweep:
            res = self.measure_point(v, channel=channel)
            if res["status"] == "success":
                data.append(res)
        self.enable_channel(False, channel=channel)
        return {"status": "success", "count": len(data), "data": data}

    def measure_time_series_it(self, v_bias: float = 0.5, duration_sec: float = 5.0, interval_sec: float = 0.5, channel: str = "smu1") -> dict:
        self.enable_channel(True, channel=channel)
        steps = int(duration_sec / interval_sec)
        data = []
        start_t = time.time()
        for i in range(steps):
            res = self.measure_point(v_bias, channel=channel)
            if res["status"] == "success":
                res["time_sec"] = round(time.time() - start_t, 2)
                data.append(res)
            time.sleep(interval_sec)
        self.enable_channel(False, channel=channel)
        return {"status": "success", "count": len(data), "data": data}