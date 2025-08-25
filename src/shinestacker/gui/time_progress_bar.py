# pylint: disable=C0114, C0115, C0116, E0611
import time
from PySide6.QtWidgets import QProgressBar
from .colors import ColorPalette, ACTION_RUNNING_COLOR, ACTION_COMPLETED_COLOR


class TimerProgressBar(QProgressBar):
    light_background_color = ColorPalette.LIGHT_BLUE
    border_color = ColorPalette.DARK_BLUE
    text_color = ColorPalette.DARK_BLUE

    def __init__(self):
        super().__init__()
        super().setRange(0, 10)
        super().setValue(0)
        self.set_running_style()
        self._start_time = -1
        self._current_time = -1
        self.elapsed_str = ''

    def set_style(self, bar_color=None):
        if bar_color is None:
            bar_color = ColorPalette.MEDIUM_BLUE
        self.setStyleSheet(f"""
        QProgressBar {{
          border: 2px solid #{self.border_color.hex()};
          border-radius: 8px;
          text-align: center;
          font-weight: bold;
          font-size: 12px;
          background-color: #{self.light_background_color.hex()};
          color: #{self.text_color.hex()};
          min-height: 1px;
        }}
        QProgressBar::chunk {{
          border-radius: 6px;
          background-color: #{bar_color.hex()};
        }}
        """)

    def time_str(self, secs):
        ss = int(secs)
        x = secs - ss
        s = ss % 60
        mm = ss // 60
        m = mm % 60
        h = mm // 60
        t_str = f"{s:02d}" + f"{x:.1f}s".lstrip('0')
        if m > 0:
            t_str = f"{m:02d}:{t_str}"
        if h > 0:
            t_str = f"{h:02d}:{t_str}"
        if m > 0 or h > 0:
            t_str = t_str.lstrip('0')
        elif 0 < s < 10:
            t_str = t_str.lstrip('0')
        elif s == 0:
            t_str = t_str[1:]
        return t_str

    def check_time(self, val):
        if self._start_time < 0:
            raise RuntimeError("Start and must be called before setValue and stop")
        self._current_time = time.time()
        elapsed_time = self._current_time - self._start_time
        self.elapsed_str = self.time_str(elapsed_time)
        fmt = f"Progress: %p% - %v of %m - elapsed: {self.elapsed_str}"
        if 0 < val < self.maximum():
            time_per_iter = float(elapsed_time) / float(val)
            estimated_time = time_per_iter * self.maximum()
            remaining_time = max(0, estimated_time - elapsed_time)
            remaining_str = self.time_str(remaining_time)
            fmt += f", {remaining_str} remaining"
        self.setFormat(fmt)

    def start(self, steps):
        super().setMaximum(steps)
        self._start_time = time.time()
        self.setValue(0)

    def stop(self):
        self.check_time(self.maximum())
        self.setValue(self.maximum())

    # pylint: disable=C0103
    def setValue(self, val):
        self.check_time(val)
        super().setValue(val)
    # pylint: enable=C0103

    def set_running_style(self):
        self.set_style(ACTION_RUNNING_COLOR)

    def set_done_style(self):
        self.set_style(ACTION_COMPLETED_COLOR)
