import sys
import os
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QGraphicsScene, QGraphicsView,
    QGraphicsPixmapItem, QApplication, QListWidgetItem, QMessageBox, QLabel
)
from PySide6.QtGui import QIcon, QPixmap, QImage, QCursor
from PySide6.QtCore import QSize, QSettings, Qt, QEvent, QObject, QPoint
from sg_reader import SgFileReader
from ui_empire_editor import Ui_MainWindow


class ProgramState:
    def __init__(self):
        self.images = {}
        self.selected_empire_image = None
        self.city_icons_map = {}
        self.init_failed = False
        self.c3_main_path = ""

    def init(self):
        if not self.load_c3_folder():
            self.init_failed = True
            return False
        self.load_images()
        return not self.init_failed

    def load_c3_folder(self):
        config_path = os.path.join(os.path.dirname(__file__), "empire_editor.cfg")
        settings = QSettings(config_path, QSettings.IniFormat)
        self.c3_main_path = settings.value("c3_main_folder", type=str)

        if not self.c3_main_path:
            folder = QFileDialog.getExistingDirectory(
                None,
                "Select Caesar 3 Main Directory",
                "",
                QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )
            if folder and self.validate_c3_directory(folder):
                settings.setValue("c3_main_folder", folder)
                self.c3_main_path = folder
                return True
            else:
                QMessageBox.critical(
                    None, "Invalid Folder", "Please select a valid Caesar 3 directory.", QMessageBox.Ok
                )
                return False
        return True

    def validate_c3_directory(self, path: str) -> bool:
        required_files = ["C3.sg2", "augustus.exe"]
        missing = [file for file in required_files if not os.path.isfile(os.path.join(path, file))]
        if missing:
            QMessageBox.critical(
                None,
                "Missing Files",
                "The following required files are missing:\n" + "\n".join(missing),
                QMessageBox.Ok
            )
            return False
        return True

    def load_images(self):
        if self.c3_main_path:
            c3_sg_path = os.path.join(self.c3_main_path, "C3.sg2")
            reader = SgFileReader(c3_sg_path)
            self.images = reader.load_filtered("The_empire", "empire_bits", "empire_panels")
            self.create_city_icons_map()

    def create_city_icons_map(self):
        try:
            self.city_icons_map = {
                "Our City": self.images["empire_bits"][0],
                "Roman City": self.images["empire_bits"][7],
                "Far away city": self.images["empire_bits"][21],
                "Empire edge": self.images["empire_bits"][71],
            }
        except (KeyError, IndexError):
            self.init_failed = True
            QMessageBox.critical(None, "Error", "Error loading city icons.", QMessageBox.Ok)

    def reset_state(self):
        self.images.clear()
        self.selected_empire_image = None
        self.city_icons_map.clear()
        self.init_failed = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Data/state
        self.state = ProgramState()
        self.init_failed = False
        if not self.state.init():
            self.init_failed = True
            return

        # Scene / view
        self.scene = QGraphicsScene(self)
        self.ui.graphicsView.setScene(self.scene)
        self.ui.graphicsView.setDragMode(QGraphicsView.ScrollHandDrag)
        self.ui.graphicsView.viewport().setMouseTracking(True)

        # UI wiring
        self.add_city_icons_to_list()
        self.ui.actionSelect_background_Image.triggered.connect(self.load_background_image)
        self.ui.listWidget.itemClicked.connect(self.on_item_clicked)

        # Drag handling
        self.selected_item = None
        self.current_icon = None
        self.is_dragging = False

        # Status bar mouse position
       # self.mouse_position_label = QLabel("Mouse Position: (0, 0)")
      #  self.ui.statusbar.addPermanentWidget(self.mouse_position_label)

    # ---------- GLOBAL EVENT FILTER ----------
    def eventFilter(self, obj, event):
        et = event.type()

        # Update mouse position label globally
        if et == QEvent.MouseMove:
            # Use global position; map into the graphics view to show local coords when inside
            if hasattr(event, "globalPosition"):
                gp = event.globalPosition().toPoint()
            else:
                gp = QCursor.pos()

            view = self.ui.graphicsView
            vp = view.viewport()
            vp_pos = vp.mapFromGlobal(gp)
            if vp.rect().contains(vp_pos):
                self.ui.mouse_position_label.setText(f"Mouse Position: ({vp_pos.x()}, {vp_pos.y()})")

            # If showing a floating preview label, keep it under the cursor (optional)
            if self.is_dragging and self.current_icon is not None:
                # Position the helper label around the cursor (relative to the main window)
                local = self.mapFromGlobal(gp)
                offset = QPoint(self.current_icon.width() // 2, self.current_icon.height() // 2)
                self.current_icon.move(local - offset)

            # Never consume move events
            return False

        # Only intercept clicks while dragging
        if self.is_dragging and et in (QEvent.MouseButtonPress, QEvent.MouseButtonRelease):
            # It will be a QMouseEvent, so these are safe:
            gp = event.globalPosition().toPoint()
            btn = event.button()

            # Boundaries
            view = self.ui.graphicsView
            vp = view.viewport()
            inside_view = vp.rect().contains(vp.mapFromGlobal(gp))

            if et == QEvent.MouseButtonPress:
                # Clicking outside while dragging cancels
                if btn in (Qt.LeftButton, Qt.RightButton) and not inside_view:
                    self.deselect_item()
                    return False  # allow widget to process too

            elif et == QEvent.MouseButtonRelease:
                # Drop inside, cancel anywhere
                if btn in (Qt.LeftButton, Qt.RightButton):
                    if inside_view:
                        view_pos = view.mapFromGlobal(gp)
                        scene_pos = view.mapToScene(view_pos)
                        self.handle_icon_drop(scene_pos)  # pass scene coords
                    self.deselect_item()
                    return False  # let the widget also get the release

        # Optional: right-click to deselect even when not "dragging"
        if et == QEvent.MouseButtonPress and hasattr(event, "button") and event.button() == Qt.RightButton:
            if self.selected_item:
                self.deselect_item()
                return False

        # Pass everything else through (important: QObject.eventFilter to avoid recursion)
        return QObject.eventFilter(self, obj, event)

    # ---------- LIST / DRAGGING ----------
    def on_item_clicked(self, item):
        if self.selected_item == item:
            self.deselect_item()
        else:
            self.select_item(item)

    def select_item(self, item):
        self.selected_item = item
        pixmap = item.icon().pixmap(self.ui.listWidget.iconSize())

        # Optional visible follower under cursor (made transparent to mouse)
        if self.current_icon:
            self.current_icon.deleteLater()
        self.current_icon = QLabel(self)
        self.current_icon.setPixmap(pixmap)
        self.current_icon.setFixedSize(pixmap.size())
        self.current_icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        #self.current_icon.show()
        
        # Start drag
        self.is_dragging = True
        self.set_cursor_to_icon(pixmap)
        self.ui.graphicsView.setDragMode(QGraphicsView.NoDrag)

    def deselect_item(self):
        if self.current_icon:
            self.current_icon.deleteLater()
            self.current_icon = None
        self.selected_item = None
        self.is_dragging = False
        self.reset_cursor()
        self.ui.graphicsView.setDragMode(QGraphicsView.ScrollHandDrag)

    # ---------- DROP HANDLER ----------
    def handle_icon_drop(self, scene_pos):
        # scene_pos is a QPointF in scene coordinates
        print(f"Dropped at scene: ({scene_pos.x():.1f}, {scene_pos.y():.1f})")
        # TODO: Add your item to the scene here if desired

    # ---------- MISC UI ----------
    def add_city_icons_to_list(self):
        for name, pil_img in self.state.city_icons_map.items():
            item = QListWidgetItem(name)
            icon = QIcon(self.pil_to_qpixmap(pil_img))
            item.setIcon(icon)
            item.setSizeHint(QSize(100, 80))
            self.ui.listWidget.addItem(item)
        self.ui.listWidget.setIconSize(QSize(64, 64))

    def on_map_setting_changed(self, index):
        if self.ui.mapSettingsMenu.currentText() == "Default Empire Map":
            if "The_empire" in self.state.images:
                self.set_background_image(self.state.images["The_empire"])
            else:
                QMessageBox.warning(
                    self, "Missing Map",
                    "The 'Default Empire Map' is not available in the loaded images.",
                    QMessageBox.Ok
                )

    def set_background_image(self, pil_img):
        pixmap = self.pil_to_qpixmap(pil_img)
        self.state.selected_empire_image = pixmap
        self.scene.clear()
        self.scene.addItem(QGraphicsPixmapItem(pixmap))
        self.scene.setSceneRect(pixmap.rect())
        self.ui.graphicsView.setEnabled(True)
        
    def set_cursor_to_icon(self, pixmap):
        """
        Set the cursor to the custom icon.
        """
        cursor = QCursor(pixmap)
        self.setCursor(cursor)

    def reset_cursor(self):
        """
        Reset the cursor back to default.
        """
        self.setCursor(Qt.ArrowCursor)  # Reset to default arrow cursor
        
    def on_default_empire_map_selected(self):
        if "The_empire" in self.state.images:
            empire_image = self.state.images["The_empire"]
            if isinstance(empire_image, list):
                empire_image = empire_image[0]
            self.set_background_image(empire_image)
        else:
            QMessageBox.warning(self, "Missing Map",
                                "The 'Default Empire Map' is not available in the loaded images.",
                                QMessageBox.Ok)

    def pil_to_qpixmap(self, pil_img):
        if pil_img.mode != "RGBA":
            pil_img = pil_img.convert("RGBA")
        w, h = pil_img.size
        data = pil_img.tobytes("raw", "RGBA")
        qimg = QImage(data, w, h, QImage.Format_RGBA8888)
        return QPixmap.fromImage(qimg)

    def load_background_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Background Image", "", "Images (*.png *.jpg *.bmp *.gif)"
        )
        if file_path:
            pixmap = QPixmap(file_path)
            self.state.selected_empire_image = pixmap
            self.scene.clear()
            self.scene.addItem(QGraphicsPixmapItem(pixmap))
            self.scene.setSceneRect(pixmap.rect())
            self.ui.graphicsView.setEnabled(True)

    def closeEvent(self, event):
        QApplication.quit()
        event.accept()


if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    # One global filter to observe ALL widgets
    app.installEventFilter(window)
    if not window.init_failed:
        window.show()
        sys.exit(app.exec())
    sys.exit(0)
