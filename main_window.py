# -*- coding: utf-8 -*-
"""
Created on Fri Jul 18 10:29:50 2025

@author: sephirex95
"""

# main_window.py
from PySide6.QtWidgets import QMainWindow, QFileDialog, QGraphicsScene, QGraphicsPixmapItem, QGraphicsView, QApplication
from PySide6.QtGui import QPixmap
from ui_empire_editor import Ui_MainWindow
import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Init scene
        self.scene = QGraphicsScene(self)
        self.ui.graphicsView.setScene(self.scene)

        # Hook up actions
        self.ui.actionSelect_background_Image.triggered.connect(self.load_background_image)
        
        self.ui.graphicsView.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)

    def load_background_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", "", "Images (*.png *.jpg *.bmp *.gif)"
        )
        if file_path:
            pixmap = QPixmap(file_path)
            self.scene.clear()
            self.scene.addItem(QGraphicsPixmapItem(pixmap))
            self.scene.setSceneRect(pixmap.rect())

    def closeEvent(self, event):
        """Ensure QApplication exits completely when window is closed."""
        QApplication.quit()
        event.accept()


if __name__ == "__main__":
    app = QApplication.instance()
    if app is None: #spyder debugging hack
        app = QApplication(sys.argv) 
    widget = MainWindow()
    widget.show()
    sys.exit(app.exec())
    app.quit()
