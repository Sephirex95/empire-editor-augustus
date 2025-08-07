# graphics_view.py
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent
from PySide6.QtCore import Qt


class GraphicsView(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)

        # 🔧 Don't override built-in .scene() method
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        label = event.mimeData().text()

        pixmap = QPixmap(50, 50)
        pixmap.fill(Qt.red)

        item = QGraphicsPixmapItem(pixmap)
        item.setOffset(-25, -25)
        item.setPos(self.mapToScene(event.position().toPoint()))
        self.scene().addItem(item)  # ✅ this still works, because setScene() is correct
        event.acceptProposedAction()
