import numpy as np
from PySide6.QtWidgets import QGraphicsPixmapItem
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPixmap, QPainter, QImage, QColor


class BrushPreviewItem(QGraphicsPixmapItem):
    def __init__(self):
        super().__init__()
        self.setVisible(False)
        self.setZValue(1000)
        self.setTransformationMode(Qt.SmoothTransformation)

    def update_preview(self, editor, pos, size):
        try:
            # Verifica preliminare
            if (editor.current_stack is None or 
                not hasattr(editor, 'image_viewer') or 
                size <= 0):
                self.setVisible(False)
                return

            # Calcolo posizione con offset corretto
            radius = size // 2
            if isinstance(pos, QPointF):
                scene_pos = pos
            else:
                # Correzione chiave: aggiustiamo l'offset del cursore
                cursor_pos = editor.image_viewer.mapFromGlobal(pos)
                scene_pos = editor.image_viewer.mapToScene(cursor_pos)
            
            # Coordinate intere per il ritaglio
            x = int(scene_pos.x() - radius)
            y = int(scene_pos.y() - radius)
            w = h = size

            # Verifica layer
            if (editor.current_layer < 0 or 
                editor.current_layer >= len(editor.current_stack)):
                self.setVisible(False)
                return

            layer = editor.current_stack[editor.current_layer]
            if not isinstance(layer, np.ndarray):
                self.setVisible(False)
                return

            height, width = layer.shape[:2]
            x_start, y_start = max(0, x), max(0, y)
            x_end, y_end = min(width, x + w), min(height, y + h)
            
            if x_end <= x_start or y_end <= y_start:
                self.setVisible(False)
                return

            # Area dell'immagine (assicurati che sia contigua)
            area = np.ascontiguousarray(layer[y_start:y_end, x_start:x_end])
            
            # Conversione immagine
            if area.ndim == 2:  # Scala di grigi
                area = np.ascontiguousarray(np.stack([area]*3, axis=-1))
            elif area.shape[2] == 4:  # RGBA
                area = np.ascontiguousarray(area[..., :3])  # RGB
            
            # Normalizzazione valori
            if area.dtype != np.uint8:
                if area.dtype.kind == 'f':
                    area = (area * 255).clip(0, 255).astype(np.uint8)
                else:
                    area = area.astype(np.uint8)

            # Creazione QImage
            qimage = QImage(
                area.data, 
                area.shape[1], 
                area.shape[0], 
                area.strides[0], 
                QImage.Format_RGB888
            )

            # Creazione maschera circolare
            mask = QPixmap(w, h)
            mask.fill(Qt.transparent)
            painter = QPainter(mask)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(Qt.NoPen)
            painter.setBrush(Qt.black)
            painter.drawEllipse(0, 0, w, h)
            painter.end()

            # Composizione finale
            pixmap = QPixmap.fromImage(qimage)
            final_pixmap = QPixmap(w, h)
            final_pixmap.fill(Qt.transparent)
            
            painter = QPainter(final_pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.drawPixmap(0, 0, pixmap)
            painter.setCompositionMode(QPainter.CompositionMode_DestinationIn)
            painter.drawPixmap(0, 0, mask)
            painter.end()

            # Impostazione posizione con offset corretto
            self.setPixmap(final_pixmap)
            self.setPos(x_start, y_start)
            self.setVisible(True)

        except Exception as e:
            print(f"Preview error: {str(e)}")
            import traceback
            traceback.print_exc()
            self.setVisible(False)

