# pylint: disable=E0611, R0917, R0913
from PySide6.QtCore import QObject, Signal


class ProjectUndoManager(QObject):
    set_enabled_undo_action_requested = Signal(bool, str)
    set_enabled_redo_action_requested = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._undo_buffer = []
        self._redo_buffer = []

    def add(self, item, description, action_type=None, old_position=None, new_position=None):
        entry = {
            'item': item,
            'description': description,
            'action_type': action_type if action_type else '',
            'old_position': old_position if old_position else (-1, -1, -1),
            'new_position': new_position if new_position else (
                old_position if old_position else (-1, -1, -1))
        }
        self._undo_buffer.append(entry)
        self.clear_redo()
        self.set_enabled_undo_action_requested.emit(True, description)

    def pop(self):
        entry = self._undo_buffer.pop()
        if len(self._undo_buffer) == 0:
            self.set_enabled_undo_action_requested.emit(False, '')
        else:
            self.set_enabled_undo_action_requested.emit(True, self._undo_buffer[-1]['description'])
        return entry

    def peek(self):
        if self._undo_buffer:
            return self._undo_buffer[-1]
        return None

    def last_entry(self):
        return self.peek()

    def filled(self):
        return len(self._undo_buffer) != 0

    def reset(self):
        self._undo_buffer = []
        self._redo_buffer = []
        self.set_enabled_undo_action_requested.emit(False, '')
        self.set_enabled_redo_action_requested.emit(False, '')

    def clear_redo(self):
        self._redo_buffer = []
        self.set_enabled_redo_action_requested.emit(False, '')

    def add_to_undo(self, entry):
        self._undo_buffer.append(entry)
        self.set_enabled_undo_action_requested.emit(True, entry['description'])

    def add_to_redo(self, entry):
        self._redo_buffer.append(entry)
        self.set_enabled_redo_action_requested.emit(True, entry['description'])

    def pop_redo(self):
        entry = self._redo_buffer.pop()
        if len(self._redo_buffer) == 0:
            self.set_enabled_redo_action_requested.emit(False, '')
        else:
            self.set_enabled_redo_action_requested.emit(True, self._redo_buffer[-1]['description'])
        return entry

    def peek_redo(self):
        if self._redo_buffer:
            return self._redo_buffer[-1]
        return None

    def filled_redo(self):
        return len(self._redo_buffer) != 0
