# pylint: disable=C0103, R0914
from PySide6.QtWidgets import QLayout
from PySide6.QtCore import Qt, QRect, QSize, QPoint


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1, justify=True):
        super().__init__(parent)
        self._item_list = []
        self._justify = justify
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)

    def addItem(self, item):
        self._item_list.append(item)

    def count(self):
        return len(self._item_list)

    def itemAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._item_list):
            return self._item_list.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientations(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._item_list:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def setJustify(self, justify):
        self._justify = justify
        self.invalidate()

    def justify(self):
        return self._justify

    def _do_layout(self, rect, test_only):
        x = rect.x()
        y = rect.y()
        line_height = 0
        spacing = self.spacing()
        lines = []
        current_line = []
        current_line_width = 0
        for item in self._item_list:
            space_x = spacing
            next_x = x + item.sizeHint().width() + space_x
            if next_x - space_x > rect.right() and line_height > 0:
                lines.append((current_line, current_line_width, line_height))
                x = rect.x()
                y = y + line_height + spacing
                next_x = x + item.sizeHint().width() + space_x
                current_line = []
                current_line_width = 0
                line_height = 0
            current_line.append(item)
            current_line_width += item.sizeHint().width()
            x = next_x
            line_height = max(line_height, item.sizeHint().height())
        if current_line:
            lines.append((current_line, current_line_width, line_height))
        y_offset = rect.y()
        for line, line_width, line_height in lines:
            if not test_only:
                available_width = rect.width() - (len(line) - 1) * spacing
                if self._justify and len(line) > 1:
                    stretch_factor = available_width / line_width if line_width > 0 else 1
                    x_offset = rect.x()
                    for item in line:
                        item_width = int(item.sizeHint().width() * stretch_factor)
                        item.setGeometry(QRect(QPoint(x_offset, y_offset),
                                               QSize(item_width, line_height)))
                        x_offset += item_width + spacing
                else:
                    x_offset = rect.x()
                    for item in line:
                        item.setGeometry(QRect(QPoint(x_offset, y_offset),
                                         item.sizeHint()))
                        x_offset += item.sizeHint().width() + spacing
            y_offset += line_height + spacing
        return y_offset - spacing - rect.y()
