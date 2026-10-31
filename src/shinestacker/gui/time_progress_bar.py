# pylint: disable=E0611
import time
from PySide6.QtWidgets import QProgressBar
from .colors import (
    ColorPalette,
    ACTION_RUNNING_COLOR, ACTION_COMPLETED_COLOR,
    ACTION_STOPPED_COLOR, ACTION_FAILED_COLOR,
    ACTION_RUNNING_BKG_COLOR, ACTION_COMPLETED_BKG_COLOR,
    ACTION_STOPPED_BKG_COLOR, ACTION_FAILED_BKG_COLOR,
    ACTION_RUNNING_TXT_COLOR, ACTION_COMPLETED_TXT_COLOR,
    ACTION_STOPPED_TXT_COLOR, ACTION_FAILED_TXT_COLOR
)


class TimerProgressBar(QProgressBar):
    border_color = ColorPalette.DARK_BLUE

    def __init__(self):
        super().__init__()
        super().setRange(0, 10)
        super().setValue(0)
        self.set_running_style()
        self._status = 'pending'
        self._start_time = -1
        self._current_time = -1
        self.elapsed_str = ''

    def set_style(self, bar_color=None, bar_bkg_color=None, bar_txt_color=None):
        if bar_color is None:
            bar_color = ColorPalette.MEDIUM_BLUE
        if bar_bkg_color is None:
            bar_bkg_color = ColorPalette.LIGHT_BLUE
        if bar_txt_color is None:
            bar_txt_color = ColorPalette.DARK_BLUE
        self.setStyleSheet(f"""
        QProgressBar {{
          border: 2px solid #{bar_txt_color.hex()};
          border-radius: 8px;
          text-align: center;
          font-weight: bold;
          font-size: 12px;
          background-color: #{bar_bkg_color.hex()};
          color: #{bar_txt_color.hex()};
        }}
        QProgressBar::chunk {{
          border-radius: 6px;
          background-color: #{bar_color.hex()};
        }}
        """)

    def capture_widget_state(self):
        return {
            'visible': self.isVisible(),
            'value': self.value(),
            'minimum': self.minimum(),
            'maximum': self.maximum(),
            'format': self.format(),
            'status': self._status
        }

    def restore_widget_state(self, state):
        if not state:
            return
        self.setVisible(state.get('visible', False))
        self.setMinimum(state.get('minimum', 0))
        self.setMaximum(state.get('maximum', 100))
        super().setValue(state.get('value', 0))
        if 'format' in state:
            self.setFormat(state['format'])
        status = state.get('status', 'pending')
        if status == 'pending':
            self._status = 'pending'
            super().setRange(0, 10)
            super().setValue(0)
        elif status == 'running':
            self.set_running_style()
        elif status == 'done':
            self.set_done_style()
        elif status == 'stopped':
            self.set_stopped_style()
        elif status == 'failed':
            self.set_failed_style()

    def time_str(self, secs):
        xsecs = int(secs * 10)
        x = xsecs % 10
        ss = xsecs // 10
        s = ss % 60
        mm = ss // 60
        m = mm % 60
        h = mm // 60
        t_str = f"{s:02d}.{x:1d}s"
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
        fmt = f"%p%, %v of %m. elapsed: {self.elapsed_str}"
        if 0 < val < self.maximum():
            time_per_iter = float(elapsed_time) / float(val)
            estimated_time = time_per_iter * self.maximum()
            remaining_time = max(0, estimated_time - elapsed_time)
            remaining_str = self.time_str(remaining_time)
            fmt += f", remaining: {remaining_str}"
        self.setFormat(fmt)

    def start(self, steps):
        super().setMaximum(steps)
        self._start_time = time.time()
        self.setValue(0)
        self.set_running_style()

    def run(self):
        self.set_running_style()

    def done(self):
        if self._start_time >= 0:
            self.setValue(self.maximum())
        else:
            super().setValue(self.maximum())
        self.set_done_style()

    def stop(self):
        self.set_stopped_style()

    def fail(self):
        self.set_failed_style()

    def clear(self):
        self._start_time = -1
        self._current_time = -1
        self.elapsed_str = ''
        super().setRange(0, 10)
        super().setValue(0)
        self.set_running_style()

    # pylint: disable=C0103
    def setValue(self, val):
        self.check_time(val)
        super().setValue(val)
        if val >= self.maximum() and self.maximum() > 0:
            self.set_done_style()
    # pylint: enable=C0103

    def set_running_style(self):
        self._status = 'running'
        self.set_style(
            ACTION_RUNNING_COLOR, ACTION_RUNNING_BKG_COLOR, ACTION_RUNNING_TXT_COLOR)

    def set_done_style(self):
        self._status = 'done'
        self.set_style(
            ACTION_COMPLETED_COLOR, ACTION_COMPLETED_BKG_COLOR, ACTION_COMPLETED_TXT_COLOR)

    def set_stopped_style(self):
        self._status = 'stopped'
        self.set_style(
            ACTION_STOPPED_COLOR, ACTION_STOPPED_BKG_COLOR, ACTION_STOPPED_TXT_COLOR)

    def set_failed_style(self):
        self._status = 'failed'
        self.set_style(
            ACTION_FAILED_COLOR, ACTION_FAILED_BKG_COLOR, ACTION_FAILED_TXT_COLOR)
