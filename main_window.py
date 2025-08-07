# main_window.py

import sys
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QGraphicsScene, QGraphicsPixmapItem, QApplication
)
from PySide6.QtGui import QPixmap
from ui_empire_editor import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # ✅ Set up a basic QGraphicsScene
        self.scene = QGraphicsScene(self)
        self.ui.graphicsView.setScene(self.scene)
        self.ui.graphicsView.setDragMode(self.ui.graphicsView.DragMode.ScrollHandDrag)

        # ✅ Add example items to the sidebar
        self.ui.listWidget.addItems(["House", "Tree", "Soldier"])

        # ✅ Hook up background image loader
        self.ui.actionSelect_background_Image.triggered.connect(self.load_background_image)

    def load_background_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", "", "Images (*.png *.jpg *.bmp *.gif)"
        )
        if file_path:
            pixmap = QPixmap(file_path)

            # Clear current scene and add background
            self.scene.clear()
            self.scene.addItem(QGraphicsPixmapItem(pixmap))
            self.scene.setSceneRect(pixmap.rect())

    def closeEvent(self, event):
        QApplication.quit()
        event.accept()


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if not app:
        app = QApplication([])

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

