# pylint: disable=E0611
import psutil
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel, QProgressBar, QSizePolicy
from PySide6.QtCore import QTimer, Qt
from .colors import ColorPalette


class StatusBarSystemMonitor(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.setup_timer()
        self.setFixedHeight(28)

    def setup_ui(self):
        bar_width = 100
        bar_height = 22
        layout = QHBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(0, 2, 0, 0)
        layout.setAlignment(Qt.AlignLeft)
        layout.setAlignment(Qt.AlignCenter)
        cpu_widget = QWidget()
        cpu_widget.setFixedSize(bar_width, bar_height)
        self.cpu_bar = QProgressBar(cpu_widget)
        self.cpu_bar.setRange(0, 100)
        self.cpu_bar.setTextVisible(False)
        self.cpu_bar.setGeometry(0, 0, bar_width, bar_height)
        self.cpu_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #cccccc;
                border-radius: 5px;
                background: #F0F0F0;
            }}
            QProgressBar::chunk {{
                background-color: #{ColorPalette.LIGHT_BLUE.hex()};
                border-radius: 5px;
            }}
        """)
        self.cpu_label = QLabel("CPU: --%", cpu_widget)
        self.cpu_label.setAlignment(Qt.AlignCenter)
        self.cpu_label.setGeometry(0, 0, bar_width, bar_height)
        self.cpu_label.setStyleSheet(f"""
            QLabel {{
                color: #{ColorPalette.DARK_BLUE.hex()};
                font-weight: bold;
                background: transparent;
                font-size: 12px;
            }}
        """)
        mem_widget = QWidget()
        mem_widget.setFixedSize(bar_width, bar_height)
        self.mem_bar = QProgressBar(mem_widget)
        self.mem_bar.setRange(0, 100)
        self.mem_bar.setTextVisible(False)
        self.mem_bar.setGeometry(0, 0, bar_width, bar_height)
        self.mem_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #CCCCCC;
                border-radius: 5px;
                background: #f0f0f0;
            }}
            QProgressBar::chunk {{
                background-color: #{ColorPalette.LIGHT_GREEN.hex()};
                border-radius: 5px;
            }}
        """)
        self.mem_label = QLabel("MEM: --%", mem_widget)
        self.mem_label.setAlignment(Qt.AlignCenter)
        self.mem_label.setGeometry(0, 0, bar_width, bar_height)
        self.mem_label.setStyleSheet(f"""
            QLabel {{
                color: #{ColorPalette.DARK_BLUE.hex()};
                font-weight: bold;
                background: transparent;
                font-size: 12px;
            }}
        """)
        layout.addWidget(cpu_widget)
        layout.addWidget(mem_widget)
        layout.addStretch()
        self.setLayout(layout)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def setup_timer(self):
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_stats)
        self.timer.start(1000)

    def update_stats(self):
        cpu_percent = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        mem_percent = memory.percent
        self.cpu_bar.setValue(int(cpu_percent))
        self.cpu_label.setText(f"CPU: {cpu_percent:.1f}%")
        self.mem_bar.setValue(int(mem_percent))
        self.mem_label.setText(f"MEM: {mem_percent:.1f}%")
