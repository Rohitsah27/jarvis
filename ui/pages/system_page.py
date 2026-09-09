"""
In-depth System Telemetry and Hardware Diagnostics Page.
Shows live CPU, RAM, Disk, Network throughput, Battery status, and Event Logs.
"""
from typing import Optional
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QProgressBar,
    QFrame,
    QSizePolicy,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ui.styles.theme import theme
from ui.components.activity_log import ActivityLogWidget
from core.system.monitor import SystemTelemetry


class TelemetryCard(QFrame):
    """Card displaying a hardware metric with progress bar."""

    def __init__(self, title: str, unit: str = "%", parent=None):
        super().__init__(parent)
        self.unit = unit
        self.setObjectName("TelemetryCard")
        self.setStyleSheet(
            f"""
            QFrame#TelemetryCard {{
                background-color: {theme.BG_PANEL};
                border: 1px solid rgba(0, 210, 255, 0.18);
                border-radius: 12px;
            }}
            """
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        # Title Row
        h_row = QHBoxLayout()
        self.lbl_title = QLabel(title)
        self.lbl_title.setFont(QFont(theme.FONT_FAMILY, 10, QFont.Bold))
        self.lbl_title.setStyleSheet("color: #ffffff; background: transparent;")

        self.lbl_value = QLabel(f"0{unit}")
        self.lbl_value.setFont(QFont(theme.FONT_MONO, 12, QFont.Bold))
        self.lbl_value.setStyleSheet(f"color: {theme.CYAN_ACCENT}; background: transparent;")

        h_row.addWidget(self.lbl_title)
        h_row.addStretch(1)
        h_row.addWidget(self.lbl_value)
        layout.addLayout(h_row)

        # Progress bar
        self.pbar = QProgressBar()
        self.pbar.setFixedHeight(8)
        self.pbar.setTextVisible(False)
        self.pbar.setStyleSheet(
            f"""
            QProgressBar {{
                background-color: #0b1422;
                border: 1px solid rgba(0, 210, 255, 0.15);
                border-radius: 4px;
            }}
            QProgressBar::chunk {{
                background-color: {theme.CYAN_ACCENT};
                border-radius: 4px;
            }}
            """
        )
        layout.addWidget(self.pbar)

        # Subtitle details
        self.lbl_details = QLabel("Initializing telemetry...")
        self.lbl_details.setFont(QFont(theme.FONT_FAMILY, 8))
        self.lbl_details.setStyleSheet(f"color: {theme.TEXT_SECONDARY}; background: transparent;")
        layout.addWidget(self.lbl_details)

    def set_metric(self, val: float, details: str = ""):
        self.pbar.setValue(int(val))
        self.lbl_value.setText(f"{val:.1f}{self.unit}")
        if details:
            self.lbl_details.setText(details)


class SystemPage(QWidget):
    """Full hardware diagnostic center."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 14, 20, 14)
        main_layout.setSpacing(14)

        # Header Title
        lbl_head = QLabel("SYSTEM HARDWARE & TELEMETRY MONITOR")
        lbl_head.setFont(QFont(theme.FONT_DISPLAY, 12, QFont.Bold))
        lbl_head.setStyleSheet(f"color: {theme.CYAN_ACCENT}; letter-spacing: 1.5px;")
        main_layout.addWidget(lbl_head)

        # Metric Cards Grid (2x2)
        grid = QGridLayout()
        grid.setSpacing(14)

        self.card_cpu = TelemetryCard("PROCESSOR (CPU)")
        self.card_ram = TelemetryCard("SYSTEM MEMORY (RAM)")
        self.card_disk = TelemetryCard("STORAGE DRIVE (C:)")
        self.card_net = TelemetryCard("NETWORK THROUGHPUT", unit=" KB/s")

        grid.addWidget(self.card_cpu, 0, 0)
        grid.addWidget(self.card_ram, 0, 1)
        grid.addWidget(self.card_disk, 1, 0)
        grid.addWidget(self.card_net, 1, 1)

        main_layout.addLayout(grid)

        # Live Activity Log Component
        self.activity_log = ActivityLogWidget(self)
        main_layout.addWidget(self.activity_log, 1)

        # Seed initial log events
        self.activity_log.log_event("Hardware diagnostics initialized", "SYS")
        self.activity_log.log_event("psutil telemetry worker thread started", "SYS")
        self.activity_log.log_event("System ready for operational commands", "AI")

    def update_telemetry(self, t: SystemTelemetry):
        self.card_cpu.set_metric(
            t.cpu_percent,
            f"{t.cpu_cores} Logical Cores | {t.cpu_freq_mhz:.0f} MHz" if t.cpu_freq_mhz else f"{t.cpu_cores} Logical Cores"
        )
        self.card_ram.set_metric(
            t.ram_percent,
            f"{t.ram_used_gb} GB Used / {t.ram_total_gb} GB Total"
        )
        self.card_disk.set_metric(
            t.disk_percent,
            f"{t.disk_free_gb} GB Free of {t.disk_total_gb} GB"
        )
        bat_str = f" | Battery: {t.battery_percent}%" if t.battery_percent is not None else ""
        self.card_net.set_metric(
            min(100.0, t.network_speed_kb),
            f"Transfer: {t.network_speed_kb:.1f} KB/s | Status: {'ONLINE' if t.network_online else 'OFFLINE'}{bat_str}"
        )
