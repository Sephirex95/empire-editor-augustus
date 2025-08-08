import sys
import os
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QGraphicsScene, QGraphicsView,
    QGraphicsPixmapItem, QApplication, QListWidgetItem, QMessageBox, QLabel
)
from PySide6.QtGui import QIcon, QPixmap, QImage, QCursor, QPainter
from PySide6.QtCore import QSize, QSettings, Qt, QEvent, QObject, QPoint
from sg_reader import SgFileReader
from ui_empire_editor import Ui_MainWindow
# top of main_window.py (with your other imports)
import empire_data as ed

from enum import Enum, auto

class EmpireObjectsList(Enum):
    OUR_CITY = auto()
    ENEMY_CITY = auto()
    TRADE_CITY = auto()
    EMPIRE_EDGE = auto()


class ProgramState:
    def __init__(self):
        self.images = {}
        self.selected_empire_image = None
        self.city_icons_map = {}
        self.init_failed = False
        self.c3_main_path = ""
        self.current_empire_object  = None
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
            self.create_selectable_elements()
    
    def create_selectable_elements(self):
        try:
            bits = self.images["empire_bits"]
            self.elements = [
                {"name": "Our City",      "pil": bits[0],  "kind": EmpireObjectsList.OUR_CITY},
                {"name": "Roman City",    "pil": bits[7],  "kind": EmpireObjectsList.TRADE_CITY},
                {"name": "Far away city", "pil": bits[21], "kind": EmpireObjectsList.ENEMY_CITY},
                {"name": "Empire edge",   "pil": bits[71], "kind": EmpireObjectsList.EMPIRE_EDGE},
            ]
        except (KeyError, IndexError):
            self.init_failed = True
            QMessageBox.critical(None, "Error", "Error loading selectable elements.", QMessageBox.Ok)


    def reset_state(self):
        self.images.clear()
        self.selected_empire_image = None
        self.city_icons_map.clear()
        self.init_failed = False

    def has_our_city(self):
        """Return (True, city) if an 'ours' city exists, else (False, None)."""
        e = self.current_empire_object
        if not e:
            return False, None
        for c in getattr(e, "cities", []):
            if getattr(c, "type", None) == ed.CityType.OURS:
                return True, c
        return False, None

    def has_any_data(self):
        """Rough check if current empire has any content worth warning about."""
        e = self.current_empire_object
        if not e:
            return False
        if getattr(e, "cities", []):
            return True
        if getattr(e, "ornaments", []):
            return True
        if getattr(e, "invasion_paths", []):
            return True
        if getattr(e, "distant_battle_paths", []):
            return True
        b = getattr(e, "border", None)
        if b and getattr(b, "edges", []):
            return True
        return False

    def check_if_empire(self):
        return self.current_empire_object is not None

    def new_empire(self):
        self.current_empire_object = ed.Empire()
        
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.no_bg_item = None
        self.bg_item = None  # the background QGraphicsPixmapItem

        self.ui.mouse_position_label.setVisible(False)  # hidden until a map is set
        self.city_items = {}  # maps City -> QGraphicsPixmapItem

        # Data/state
        self.state = ProgramState()
        self.init_failed = False
        if not self.state.init():
            self.init_failed = True
            return

        # Scene / view
        self.scene = QGraphicsScene(self)
        self.ui.graphicsView.setScene(self.scene)

        self.ui.graphicsView.setDragMode(QGraphicsView.NoDrag)

        self.ui.graphicsView.viewport().setMouseTracking(True)
        
        self.ui.graphicsView.setRenderHint(QPainter.SmoothPixmapTransform, False)

        self.show_no_background_message()               # show placeholder on startup

        # UI wiring
        self.add_city_icons_to_list()
        self.ui.actionSelect_background_Image.triggered.connect(self.load_background_image)
        self.ui.listWidget.itemClicked.connect(self.on_item_clicked)

        # Drag handling
        self.selected_item = None
        self.current_icon = None
        self.is_dragging = False

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
                # 1) Viewport -> Scene (accounts for scroll/zoom/transform)
                scene_pos = view.mapToScene(vp_pos)
            
                ## 2) Scene -> image pixel coords using the background item
                pm_item = self.bg_item
                if pm_item is not None:
                    img_pos = pm_item.mapFromScene(scene_pos)
                    x, y = int(img_pos.x()), int(img_pos.y())
                    pm = pm_item.pixmap()
                    if 0 <= x < pm.width() and 0 <= y < pm.height():
                        self.ui.mouse_position_label.setText(f"Mouse Position: ({x}, {y})")
                    else:
                        self.ui.mouse_position_label.setText("Mouse Position: (—)")
                else:
                    self.ui.mouse_position_label.setText(f"Mouse Position: ({scene_pos.x():.1f}, {scene_pos.y():.1f})")


            # If showing a floating preview label, keep it under the cursor (optional)
            # in eventFilter, MouseMove branch
            if self.is_dragging and self.current_icon is not None:
                local = self.mapFromGlobal(gp)
                self.current_icon.move(local)   # <- no half-width/height offset


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
                    return True  # dont allow widget to process too

            elif et == QEvent.MouseButtonRelease:
                if btn in (Qt.LeftButton, Qt.RightButton):
                    # hand off the exact dragged pixmap to the drop
                    self.pending_drop_pixmap = getattr(self, "drag_pixmap", None)
            
                    self.deselect_item()
                    if inside_view:
                        view_pos = view.mapFromGlobal(gp)
                        scene_pos = view.mapToScene(view_pos)
                        self.handle_icon_drop(scene_pos)
                    # clear after use
                    self.pending_drop_pixmap = None
                    return False


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
            # already selected -> deselect
            self.deselect_item()
        else:
            self.select_item(item)
            # visually mark it selected in the list
            self.ui.listWidget.setCurrentItem(item)


    def select_item(self, item):
        self.selected_item = item
        self.selected_kind = item.data(Qt.UserRole)
        pixmap = item.icon().pixmap(self.ui.listWidget.iconSize())
        self.ui.graphicsView.setInteractive(False)

        # cache the exact pixmap used for drag
        self.drag_pixmap = pixmap
    
        if self.current_icon:
            self.current_icon.deleteLater()
        self.current_icon = QLabel(self)
        self.current_icon.setPixmap(pixmap)
        self.current_icon.setFixedSize(pixmap.size())
        self.current_icon.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.is_dragging = True
        self.set_cursor_to_icon(pixmap)
        self.ui.graphicsView.setDragMode(QGraphicsView.NoDrag)
        
        self._apply_interactivity_to_all(False)

    def deselect_item(self):
        if self.current_icon:
            self.current_icon.deleteLater()
            self.current_icon = None
        # keep self.selected_kind intact so drop handler knows what was chosen
        self.selected_item = None
        self.is_dragging = False
        self.reset_cursor()
        self.ui.graphicsView.setInteractive(True)


        self.ui.graphicsView.setDragMode(QGraphicsView.NoDrag)  # not ScrollHandDrag

    
        # FIX: also clear the QListWidget’s selection so it’s not visually highlighted
        self.ui.listWidget.clearSelection()
        self._apply_interactivity_to_all(True)

    # ---------- DROP HANDLER ----------
    def handle_icon_drop(self, scene_pos):
        kind = getattr(self, "selected_kind", None)
        if kind is None:
            return
        
        if kind == EmpireObjectsList.OUR_CITY:
            self.handle_drop_city(scene_pos)
        elif kind == EmpireObjectsList.EMPIRE_EDGE:
            self.handle_drop_empire_edge(scene_pos)
        else:
            print(f"No handler for kind: {kind}")


    def add_city_icons_to_list(self):
        self.ui.listWidget.clear()
        for el in self.state.elements:
            item = QListWidgetItem(el["name"])
            item.setIcon(QIcon(self.pil_to_qpixmap(el["pil"])))
            item.setSizeHint(QSize(100, 80))
            item.setData(Qt.UserRole, el["kind"])   # store the enum directly
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
    def _no_bg_item_alive(self):
        # alive iff we have an object AND it still belongs to a scene
        return self.no_bg_item is not None and self.no_bg_item.scene() is not None
        
    def _scene_to_image_xy(self, scene_pos):
        if self.bg_item is None:
            return None
        img_pos = self.bg_item.mapFromScene(scene_pos)
        x, y = int(img_pos.x()), int(img_pos.y())
        pm = self.bg_item.pixmap()
        if 0 <= x < pm.width() and 0 <= y < pm.height():
            return x, y
        return None

    def _pixmap_for_city(self, city) -> QPixmap:
        size = self.ui.listWidget.iconSize()
    
        # 0) If we have a pending drop pixmap, use it EXACTLY
        pm = getattr(self, "pending_drop_pixmap", None)
        if pm is not None and not pm.isNull():
            return pm
    
        # 1) Otherwise, try the currently selected item (if any)
        if self.selected_item is not None:
            try:
                return self.selected_item.icon().pixmap(size)
            except Exception:
                pass

        # 2) Fallback by city.type -> EmpireObjectsList kind
        kind = None
        ct = getattr(city, "type", None)
        try:
            if ct == ed.CityType.OURS:
                kind = EmpireObjectsList.OUR_CITY
            elif hasattr(ed.CityType, "TRADE") and ct == ed.CityType.TRADE:
                kind = EmpireObjectsList.TRADE_CITY
            elif hasattr(ed.CityType, "ENEMY") and ct == ed.CityType.ENEMY:
                kind = EmpireObjectsList.ENEMY_CITY
        except Exception:
            kind = None

        # Find matching element
        if kind is None and self.state.elements:
            # last resort: default to first element ("Our City")
            kind = self.state.elements[0]["kind"]

        for el in getattr(self.state, "elements", []):
            if el["kind"] == kind:
                pm = self.pil_to_qpixmap(el["pil"])
                # scale to icon size similar to QListWidget’s icon rendering
                return pm.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # Ultimate fallback: empty pixmap of icon size (avoids crashes)
        fallback = QPixmap(size)
        fallback.fill(Qt.transparent)
        return fallback

    def _place_city_marker(self, city, x, y):
        pm = self._pixmap_for_city(city)
        if self.bg_item is None:
            return
        scene_pt = self.bg_item.mapToScene(x, y)
    
        key = id(city)
        if key in self.city_items:
            item = self.city_items[key]
            item.setPixmap(pm)
            item.setOffset(0, 0)      # top-left anchor
            item.setPos(scene_pt)
        else:
            item = QGraphicsPixmapItem(pm)
            item.setZValue(10)
            item.setOffset(0, 0)
            item.setPos(scene_pt)
            item.setFlag(QGraphicsPixmapItem.ItemIsSelectable, True)
            item.setFlag(QGraphicsPixmapItem.ItemIsMovable, False)
            item.setData(0, key)
            item.setData(1, city)
            self.scene.addItem(item)
            self.city_items[key] = item
    
        # Apply current interactivity state (pointer on hover only when not dragging)
        self._apply_item_interactivity(item, enable=not self.is_dragging)
    def _apply_item_interactivity(self, item, enable: bool):
        item.setAcceptHoverEvents(enable)
        item.setCursor(Qt.PointingHandCursor if enable else Qt.ArrowCursor)
    
    def _apply_interactivity_to_all(self, enable: bool):
        for it in self.city_items.values():
            self._apply_item_interactivity(it, enable)


    def _remove_city_marker(self, city):
        """Remove the scene item for this city, if it exists."""
        key = id(city)
        item = self.city_items.pop(key, None)
        if item is not None:
            self.scene.removeItem(item)
            # let Qt delete C++ object; don't keep stale refs

    def show_no_background_message(self):
        """Show the placeholder text when no background is set."""
        if not self._no_bg_item_alive():
            # if we had a stale pointer (e.g., scene.clear() deleted it), drop it
            self.no_bg_item = None
            self.no_bg_item = self.scene.addText("No Empire background image selected.")
        self.center_no_background_message()
        self.ui.mouse_position_label.setVisible(False)
    
    def remove_no_background_message(self):
        """Remove the placeholder text when a background is set."""
        if self._no_bg_item_alive():
            self.scene.removeItem(self.no_bg_item)
        self.no_bg_item = None  # important: clear stale reference
        self.ui.mouse_position_label.setVisible(True)
    
    def center_no_background_message(self):
        if not self._no_bg_item_alive():
            return
        view = self.ui.graphicsView
        vp = view.viewport()
        br = self.no_bg_item.boundingRect()
        x = (vp.width() - br.width()) / 2
        y = (vp.height() - br.height()) / 2
        self.no_bg_item.setPos(view.mapToScene(int(x), int(y)))

            
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.center_no_background_message()  # now harmless if item was deleted
    
    def set_background_image(self, pil_img):
        # Ask/prepare a new empire first
        if not self._ensure_new_empire_for_new_background():
            return
    
        pixmap = self.pil_to_qpixmap(pil_img)
        self.state.selected_empire_image = pixmap
    
        self.scene.clear()
        self.bg_item = None

        self.no_bg_item = None
        self.bg_item = QGraphicsPixmapItem(pixmap)
        self.bg_item.setZValue(-1000)  # keep it behind markers
        self.scene.addItem(self.bg_item)
        self.scene.setSceneRect(pixmap.rect())
        self.ui.graphicsView.setEnabled(True)
        self.remove_no_background_message()

    def set_cursor_to_icon(self, pixmap):
        """
        Set the cursor to the custom icon on *all* relevant widgets so the
        viewport can't revert it to Arrow while dragging.
        """
        cursor = QCursor(pixmap, 0, 0)  # hotspot at (0,0)
    
        # Apply to the main window, view, and the viewport
        self.setCursor(cursor)
        self.ui.graphicsView.setCursor(cursor)
        self.ui.graphicsView.viewport().setCursor(cursor)
    
    def reset_cursor(self):
        """
        Reset cursors back to default on all widgets touched above.
        Use unsetCursor() so they inherit normally again.
        """
        for w in (self, self.ui.graphicsView, self.ui.graphicsView.viewport()):
            try:
                w.unsetCursor()
            except Exception:
                pass

        
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
        if not file_path:
            return
    
        # Ask/prepare a new empire first
        if not self._ensure_new_empire_for_new_background():
            return
    
        pixmap = QPixmap(file_path)
        self.state.selected_empire_image = pixmap
        self.scene.clear()
        self.no_bg_item = None
        self.bg_item = QGraphicsPixmapItem(pixmap)
        self.bg_item.setZValue(-1000)  # keep it behind markers
        self.scene.addItem(self.bg_item)
        self.scene.setSceneRect(pixmap.rect())
        self.ui.graphicsView.setEnabled(True)
        self.remove_no_background_message()

            
    def _ensure_new_empire_for_new_background(self) -> bool:
        """
        Returns True if it's OK to proceed (new empire created or none existed).
        Returns False if the user cancels.
        """
        # If there is data, warn
        if self.state.check_if_empire() and self.state.has_any_data():
            resp = QMessageBox.question(
                self,
                "Create New Empire?",
                "You have unsaved work in the current empire.\n"
                "Create a new one and discard current progress?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if resp != QMessageBox.Yes:
                return False
    
        # Create a fresh empire (always on new background as requested)
        self.state.new_empire()
        # Clear any old markers
        self.city_items.clear()
        return True
    
    def remove_city(self, city):
        empire = self.state.current_empire_object
        if empire and city in empire.cities:
            empire.cities.remove(city)
        self._remove_city_marker(city)
        if self.selected_item and self.selected_item.data(Qt.UserRole) == EmpireObjectsList.OUR_CITY:
            self.deselect_item()
            
    def handle_drop_city(self, scene_pos):
        xy = self._scene_to_image_xy(scene_pos)
        if xy is None:
            QMessageBox.warning(self, "No background", "Drop onto the background image area.", QMessageBox.Ok)
            return
        x, y = xy
    
        # Ensure there's an empire
        if not self.state.check_if_empire():
            self.state.new_empire()
        empire = self.state.current_empire_object
    
        # Do we already have an 'ours' city?
        has_ours, ours = self.state.has_our_city()
        # in handle_drop_city, for moving:
        if has_ours:
            resp = QMessageBox.question(
                self,
                "Move Our City?",
                f"Move 'Our City' from ({ours.x}, {ours.y}) to ({x}, {y})?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if resp == QMessageBox.No:
                return
            # Move only: remove marker, update coords, re-place marker
            self._remove_city_marker(ours)
            ours.x, ours.y = x, y
            self._place_city_marker(ours, x, y)

        else:
            # Create it fresh
            ours = ed.City(name="Our City", x=x, y=y, type=ed.CityType.OURS, sells=[])
            empire.cities.append(ours)
            self._place_city_marker(ours, x, y)


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
