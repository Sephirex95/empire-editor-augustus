# main_window.py

import sys
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QGraphicsScene, QGraphicsPixmapItem, QApplication,  QListWidgetItem,  QMessageBox
)
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import QSize, QSettings
import os

from ui_empire_editor import Ui_MainWindow


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.init_failed = False
        
        if not self.check_or_prompt_for_c3_folder():
            self.init_failed = True
            return  # Stop further setup
            
        self.selected_empire_image = None
        # Set up a basic QGraphicsScene
        self.scene = QGraphicsScene(self)
        self.ui.graphicsView.setScene(self.scene)
        self.ui.graphicsView.setDragMode(self.ui.graphicsView.DragMode.ScrollHandDrag)
        
        
        items = ["House", "Tree", "Soldier"]
        for name in items:
            item = QListWidgetItem(name)
            icon = QIcon(QPixmap(64, 64))  # Placeholder blank icon
            item.setIcon(icon)
            item.setSizeHint(QSize(100, 80))  # Width doesn’t matter much here
            self.ui.listWidget.addItem(item)
        
        # Set global icon size for the list view
        self.ui.listWidget.setIconSize(QSize(64, 64))

        # ✅ Hook up background image loader
        self.ui.actionSelect_background_Image.triggered.connect(self.load_background_image)
        self.ui.graphicsView.setEnabled(False)
        self.scene.addText("No map loaded. Use the menu to load a background image.")
    def load_background_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", "", "Images (*.png *.jpg *.bmp *.gif)"
        )
        if file_path:
            pixmap = QPixmap(file_path)
            self.selected_empire_image = pixmap
            # Clear current scene and add background
            self.scene.clear()
            self.scene.addItem(QGraphicsPixmapItem(pixmap))
            self.scene.setSceneRect(pixmap.rect())
            self.ui.graphicsView.setEnabled(True)
                
    def check_or_prompt_for_c3_folder(self):
        config_path = os.path.join(os.path.dirname(__file__), "empire_editor.cfg")
        settings = QSettings(config_path, QSettings.IniFormat)
    
        c3_path = settings.value("c3_main_folder", type=str)
    
        if not c3_path:
            # Show initial info
            QMessageBox.information(
                self,
                "C3 Files Required",
                "AugustusEmpireEditor requires original Caesar 3 files to work.\n\n"
                "Please select the path to your main Caesar 3 directory.",
                QMessageBox.Ok
            )
    
            # Show folder picker
            folder = QFileDialog.getExistingDirectory(
                self,
                "Select Caesar 3 Main Directory",
                "",
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )
    
            # If user selected something
            if folder:
                is_valid, missing = self.validate_c3_directory(folder)
                if is_valid:
                    settings.setValue("c3_main_folder", folder)
                    return True
                else:
                    # ❌ Clear invalid setting and exit
                    settings.remove("c3_main_folder")
                    QMessageBox.critical(
                        self,
                        "Missing Required Files",
                        "The selected folder is missing the following required files:\n\n"
                        + "\n".join(f"- {file}" for file in missing),
                        QMessageBox.Ok
                    )
                    return False
            else:
                # ❌ User canceled, clear and exit
                settings.remove("c3_main_folder")
                QMessageBox.critical(
                    self,
                    "Missing Files",
                    "You must select a valid Caesar 3 directory to continue.",
                    QMessageBox.Ok
                )
                return False
        else:
            return True #dont miss it!

    def validate_c3_directory(self, path: str) -> tuple[bool, list[str]]:
        required_files = ["C3.sg2", "augustus.exe"]
        missing = []
    
        for filename in required_files:
            full_path = os.path.join(path, filename)
            if not os.path.isfile(full_path):
                missing.append(filename)
    
        return (len(missing) == 0, missing)



    def closeEvent(self, event):
        QApplication.quit()
        event.accept()


if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance()
    if not app:
        app = QApplication([])

    window = MainWindow()
    if not window.init_failed:
        window.show()
        sys.exit(app.exec())
    else:
        # Clean exit if startup failed
        sys.exit(0)


