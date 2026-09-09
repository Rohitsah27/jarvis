"""
Hardware monitoring worker running on a background QThread using psutil.
Prevents UI stutter while sampling real CPU, RAM, Disk, Network, and Battery stats.
"""
from dataclasses import dataclass
from typing import Optional
import time
import os
import psutil
from PySide6.QtCore import QThread, Signal, QObject


@dataclass
class SystemTelemetry:
    cpu_percent: float = 0.0
    ram_percent: float = 0.0
    ram_used_gb: float = 0.0
    ram_total_gb: float = 0.0
    disk_percent: float = 0.0
    disk_free_gb: float = 0.0
    disk_total_gb: float = 0.0
    network_online: bool = True
    network_speed_kb: float = 0.0
    battery_percent: Optional[int] = None
    battery_plugged: bool = True
    cpu_cores: int = 1
    cpu_freq_mhz: float = 0.0


class SystemMonitorWorker(QThread):
    """Background thread polling system metrics periodically."""

    telemetry_updated = Signal(object)  # Emits SystemTelemetry

    def __init__(self, interval_sec: float = 1.5, parent: Optional[QObject] = None):
        super().__init__(parent)
        self.interval_sec = interval_sec
        self._running = True
        self._last_net_bytes = 0
        self._last_net_time = time.time()

        try:
            net_io = psutil.net_io_counters()
            self._last_net_bytes = net_io.bytes_sent + net_io.bytes_recv
        except Exception:
            pass

    def run(self):
        # Prime psutil cpu measurement
        psutil.cpu_percent(interval=None)

        while self._running:
            try:
                # 1. CPU
                cpu = psutil.cpu_percent(interval=None)
                cores = psutil.cpu_count(logical=True) or 1
                freq = 0.0
                try:
                    cpu_freq = psutil.cpu_freq()
                    if cpu_freq:
                        freq = cpu_freq.current
                except Exception:
                    pass

                # 2. RAM
                vmem = psutil.virtual_memory()
                ram_pct = vmem.percent
                ram_used_gb = round(vmem.used / (1024**3), 1)
                ram_total_gb = round(vmem.total / (1024**3), 1)

                # 3. Disk
                drive = "C:\\" if os.name == "nt" else "/"
                disk_usage = psutil.disk_usage(drive)
                disk_pct = disk_usage.percent
                disk_free_gb = round(disk_usage.free / (1024**3), 1)
                disk_total_gb = round(disk_usage.total / (1024**3), 1)

                # 4. Battery
                bat_pct = None
                bat_plugged = True
                try:
                    battery = psutil.sensors_battery()
                    if battery:
                        bat_pct = int(battery.percent)
                        bat_plugged = battery.power_plugged
                except Exception:
                    pass

                # 5. Network Speed & Connectivity
                curr_time = time.time()
                elapsed = max(0.1, curr_time - self._last_net_time)
                speed_kb = 0.0
                online = True
                try:
                    net_io = psutil.net_io_counters()
                    curr_bytes = net_io.bytes_sent + net_io.bytes_recv
                    delta = max(0, curr_bytes - self._last_net_bytes)
                    speed_kb = round((delta / 1024.0) / elapsed, 1)
                    self._last_net_bytes = curr_bytes
                    self._last_net_time = curr_time
                except Exception:
                    online = False

                telemetry = SystemTelemetry(
                    cpu_percent=cpu,
                    ram_percent=ram_pct,
                    ram_used_gb=ram_used_gb,
                    ram_total_gb=ram_total_gb,
                    disk_percent=disk_pct,
                    disk_free_gb=disk_free_gb,
                    disk_total_gb=disk_total_gb,
                    network_online=online,
                    network_speed_kb=speed_kb,
                    battery_percent=bat_pct,
                    battery_plugged=bat_plugged,
                    cpu_cores=cores,
                    cpu_freq_mhz=freq,
                )

                self.telemetry_updated.emit(telemetry)

            except Exception:
                pass

            # Sleep in small slices so thread responds quickly to stop()
            steps = int(self.interval_sec * 10)
            for _ in range(steps):
                if not self._running:
                    break
                self.msleep(100)

    def stop(self):
        self._running = False
        self.wait(1000)
