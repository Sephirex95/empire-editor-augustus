import sys
import os
import json
import shutil
import re
from typing import List, Optional, Dict, Tuple, Any
import PySide6.QtWidgets as QWI
import PySide6.QtGui as QGU
import PySide6.QtCore as QCO
import ui_empire_editor as UIE
import graphics_objects as GRO
import program_state as PRS
from PIL import Image
import empire_data as ed
import edit_city_logic as emp_dlg
import copy
from html import escape as esc
from ui_strings import UIS
import default_cities as DC
import logging

# ---------------------------------------------
# Global references to frequently accessed objects
# These are set when MainWindow is created and updated when objects change
# ---------------------------------------------
Empire = None  # Reference to self.state.current_empire_object
Manager = None  # Reference to self.graphics_manager

# ---------------------------------------------
# Message Box Button Constants
# ---------------------------------------------
QBTN_OK = 1
QBTN_YES = 1
QBTN_NO = 2
QBTN_CANCEL = 0

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)-5.5s] : %(message)s",
    handlers=[logging.FileHandler("empire_editor.log"), logging.StreamHandler()],
)

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)  # full debug for main program

# Load settings before creating QApplication
s = QCO.QSettings("empire_editor.cfg", QCO.QSettings.IniFormat)
if s.value("graphics/disable_high_dpi_scaling", True, bool):
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "0"
    os.environ["QT_SCALE_FACTOR"] = "1"
    os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

# ---------------------------------------------
# MainWindow class
# ---------------------------------------------


class MainWindow(QWI.QMainWindow):
    def __init__(self):
        super().__init__()
        # ==============================================
        # 1. BASIC UI SETUP
        # ==============================================
        self.ui = UIE.Ui_MainWindow()
        self.ui.setupUi(self)
        self.program_editor_version = ed.get_editor_version()

        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "editor.ico")
        if os.path.exists(icon_path):
            icon = QGU.QIcon(icon_path)
            self.setWindowIcon(icon)
            QWI.QApplication.instance().setWindowIcon(icon)

        # ==============================================
        # 2. STATE AND DATA MANAGEMENT
        # ==============================================
        self.state = PRS.ProgramState()
        self.init_failed = False
        if not self.state.init():
            self.init_failed = True
            return

        # File tracking for title bar
        self.current_file_path = None
        self.has_unsaved_changes = False

        # ==============================================
        # 3. GRAPHICS AND SCENE SETUP
        # ==============================================
        # Background and scene
        self.scene = QWI.QGraphicsScene(self)
        self.ui.graphicsView.setScene(self.scene)
        self.no_bg_item = None
        self.bg_item = None
        self.bg_type = ed.EmpBackgroundTypes.NONE
        self._current_image_path = None

        # Graphics object management (NEW SYSTEM)
        self.graphics_manager = GRO.GraphicsObjectManager()
        self.selectable_elements: List[GRO.SelectableElement] = []
        self.selected_list_element = None

        # City tracking (needed for direct access)
        self.city_items = {}  # maps City -> QGraphicsPixmapItem
        self.city_labels = {}  # maps City -> QGraphicsTextItem

        # Default cities management
        self.default_cities_manager = DC.DefaultCitiesManager(self, log)  # pass the logger

        # Update global references after state and scene are initialized
        self._update_global_references()

        # ==============================================
        # 4. DRAWING MODES AND INTERACTION STATE
        # ==============================================
        # Edge/border drawing state
        self.edge_drawing_active = False
        self.edge_points_img = []
        self.edge_point_items = []
        self.edge_line_items = []
        self.edge_temp_line_item = None
        self.edge_hit_epsilon = 10
        self.empire_border = False

        # Trade route drawing state
        self.trade_drawing_active = False
        self.trade_is_land = True
        self.trade_drawing_points = []
        self.trade_drawing_point_items = []
        self.trade_drawing_line_items = []
        self.trade_temp_line_item = None
        self.trade_route_city = None

        # Vertex editing state (simplified - graphics objects now handle details)
        self.vertex_editing_active = False
        self.editing_vertex_index = None
        self.editing_vertex_handle = None

        # Selection and dragging state
        self.selected_item = None
        self.is_dragging = False
        self.moving_city = None
        self.selected_edge_index = None
        self.return_to_dialog = False

        # Cursor management
        self._win_cursor_applied = False
        self._win_cursor_sig = None

        # ==============================================
        # 5. VIEW CONFIGURATION
        # ==============================================
        self.ui.graphicsView.setDragMode(QWI.QGraphicsView.DragMode.NoDrag)
        self.ui.graphicsView.setViewportMargins(10, 10, 10, 10)
        self.ui.graphicsView.viewport().setMouseTracking(True)
        self.ui.graphicsView.setRenderHint(QGU.QPainter.RenderHint.SmoothPixmapTransform, False)
        self.ui.mouse_position_label.setVisible(False)

        # ==============================================
        # 6. INITIALIZE COMPONENTS
        # ==============================================
        self._init_cursor_pixmaps()
        self.show_no_background_message()
        self.add_city_icons_to_list()

        # ==============================================
        # 7. EVENT CONNECTIONS
        # ==============================================
        # File menu
        self.ui.actionNew.triggered.connect(self.on_new_empire)
        self.ui.actionOpen.triggered.connect(self.open_empire_xml)
        self.ui.actionSave.triggered.connect(self.save_empire_xml)
        self.ui.actionSelect_background_Image.triggered.connect(lambda: self.set_background_image(None, True))

        # Empire menu
        self.ui.actionEmpireProperties.triggered.connect(self.on_empire_properties)
        self.ui.actionEmpireSnap.triggered.connect(lambda: self.refresh_map(True))

        # View menu
        self.ui.actionViewOption1.toggled.connect(self.toggle_cities_visibility)
        self.ui.actionViewOption2.triggered.connect(self.toggle_trade_routes_visibility)
        self.ui.actionViewOption3.toggled.connect(self.toggle_border_visibility)
        self.ui.actionViewOption4.toggled.connect(self.update_all_city_labels_from_toggles)
        self.ui.actionViewOption5.toggled.connect(self.update_all_city_labels_from_toggles)
        self.ui.actionRefreshMap.triggered.connect(self.refresh_map)

        # Settings and Help
        self.ui.menuSettings.triggered.connect(self._open_settings)
        self.ui.actionAbout.triggered.connect(lambda: UIE.show_about_dialog(self))

        # GitHub links
        self.ui.actionGitHub_Augustus.triggered.connect(self._open_github_augustus)
        self.ui.actionGitHub_Editor.triggered.connect(self._open_github_editor)
        self.ui.actionGitHub_Custom.triggered.connect(self._open_github_custom)

        # List widget
        self.ui.listWidget.itemClicked.connect(self.on_item_clicked)

        # ==============================================
        # 8. FINAL INITIALIZATION
        # ==============================================
        self.default_cities_manager.populate_menu()
        self.update_ui_state()
        self.default_cities_manager.update_menu_state()
        self.update_window_title()

    # %% Message box helper method
    def show_message(self, title: str, message: str, msg_type: int = 0, buttons: int = 0, default_button: int = 0):
        """
        Unified message box function to replace all QMessageBox calls.

        Args:
            title: Window title
            message: Message text
            msg_type: 0=Information, 1=Warning, 2=Critical, 3=Question
            buttons: 0=Ok only, 1=Yes|No, 2=Yes|No|Cancel
            default_button: 0=Ok, 1=Yes, 2=No, 3=Cancel

        Returns:
            int: QBTN_CANCEL/QBTN_NO, QBTN_OK/QBTN_YES, or QBTN_NO (for Yes|No|Cancel)
        """
        # Define button combinations
        btn_ok = QWI.QMessageBox.StandardButton.Ok
        btn_yes = QWI.QMessageBox.StandardButton.Yes
        btn_no = QWI.QMessageBox.StandardButton.No
        btn_cancel = QWI.QMessageBox.StandardButton.Cancel

        if buttons == 0:  # Ok only
            button_flags = btn_ok
            default_flag = btn_ok
        elif buttons == 1:  # Yes | No
            button_flags = btn_yes | btn_no
            if default_button == 1:  # Yes
                default_flag = btn_yes
            else:  # No (default_button == 2 or anything else)
                default_flag = btn_no
        elif buttons == 2:  # Yes | No | Cancel
            button_flags = btn_yes | btn_no | btn_cancel
            if default_button == 1:  # Yes
                default_flag = btn_yes
            elif default_button == 2:  # No
                default_flag = btn_no
            else:  # Cancel (default_button == 3 or anything else)
                default_flag = btn_cancel
        else:
            # Fallback to Ok only
            button_flags = btn_ok
            default_flag = btn_ok

        # Call appropriate message box type
        if msg_type == 0:  # Information
            result = QWI.QMessageBox.information(self, title, message, button_flags, default_flag)
        elif msg_type == 1:  # Warning
            result = QWI.QMessageBox.warning(self, title, message, button_flags, default_flag)
        elif msg_type == 2:  # Critical
            result = QWI.QMessageBox.critical(self, title, message, button_flags, default_flag)
        elif msg_type == 3:  # Question
            result = QWI.QMessageBox.question(self, title, message, button_flags, default_flag)
        else:
            # Fallback to information
            result = QWI.QMessageBox.information(self, title, message, button_flags, default_flag)

        # Return consistent values using our constants
        if buttons == 2:  # Yes|No|Cancel - return specific values
            if result == btn_yes:
                return QBTN_YES
            elif result == btn_no:
                return QBTN_NO
            else:  # Cancel
                return QBTN_CANCEL
        else:  # Ok only or Yes|No
            if result in (btn_ok, btn_yes):
                return QBTN_OK  # or QBTN_YES (same value)
            else:
                return QBTN_NO  # or QBTN_CANCEL (same value)

    # %% Private helpers for actions
    def _open_github_augustus(self):
        url = UIS.GITHUB_AUGUSTUS
        QGU.QDesktopServices.openUrl(QCO.QUrl(url))

    def _open_github_editor(self):
        url = UIS.GITHUB_EDITOR
        QGU.QDesktopServices.openUrl(QCO.QUrl(url))

    def _open_github_custom(self):
        url = UIS.GITHUB_CUSTOM
        QGU.QDesktopServices.openUrl(QCO.QUrl(url))

    def _get_city_index(self, city) -> int | None:
        """Get the index of a city in the current empire's cities list."""
        if not Empire:
            return None
        try:
            return Empire.cities.index(city)
        except ValueError:
            return None

    def _open_settings(self):
        dlg = UIE.SettingsDialog(self, settings=self.state.settings)
        if dlg.exec():
            self.state.apply_settings_from_store()
            # react to changes if needed (e.g., reload images if c3_main_folder changed)

    # %% setup-related functions
    def _update_global_references(self):
        """Update global references to frequently accessed objects."""
        global Empire, Manager
        Manager = self.graphics_manager
        # Empire is updated separately when it changes
        self._update_empire_reference()

    def _update_empire_reference(self):
        """Update global Empire reference."""
        global Empire
        Empire = self.state.current_empire_object if self.state else None

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.center_no_background_message()  # now harmless if item was deleted

    def _init_cursor_pixmaps(self):
        """Initialize cursor pixmaps once at startup for drawing modes."""
        # Edge drawing cursor - use empire edge icon
        edge_pm = self._get_empire_edge_pixmap()
        if edge_pm.isNull():
            # Fallback: create a simple red square
            edge_pm = QGU.QPixmap(8, 8)
            edge_pm.fill(QCO.Qt.red)
        self.edge_cursor_pixmap = edge_pm

        # Trade drawing cursors - use trade dot icons
        land_pm = self._get_trade_dot_pixmap(True)
        if land_pm.isNull():
            # Fallback: create a simple orange dot
            land_pm = QGU.QPixmap(8, 8)
            land_pm.fill(QGU.QColor(255, 140, 0))
        self.land_cursor_pixmap = land_pm

        sea_pm = self._get_trade_dot_pixmap(False)
        if sea_pm.isNull():
            sea_pm = QGU.QPixmap(8, 8)
            sea_pm.fill(QCO.Qt.cyan)
        self.sea_cursor_pixmap = sea_pm

    def _check_before_discarding(self, title=UIS.UNSAVED_CHANGES):
        """Check for unsaved changes before discarding current work."""
        if not (self.state.check_if_empire() and self.state.has_any_data()):
            return True
        if not self.has_unsaved_changes:
            return True
        message = UIS.UNSAVED_PROGRESS
        return self.show_message(title, message, 3, 1, 2) == QBTN_YES  # Question, Yes|No, default No

    def closeEvent(self, event):
        """Handle window close event to prevent unsaved data loss."""

        if self._check_before_discarding("Close Application"):
            event.accept()
        else:
            event.ignore()

    # %% Main user-facing functions
    def open_empire_xml(self):
        """Open and load empire from XML file."""
        # Check if we have unsaved changes
        if not self._check_before_discarding("load"):
            return
        file_path, _ = QWI.QFileDialog.getOpenFileName(self, UIS.OPEN_XML, "", UIS.XML_FILES)
        if not file_path:
            return  # User cancelled

        try:
            # Read the XML file
            with open(file_path, "r", encoding="utf-8") as f:
                xml_content = f.read()
            self.clear_empire_data()
            # Load empire from XML
            empire_obj = ed.Empire.from_xml_string(xml_content)
            self.state.current_empire_object = empire_obj
            self._update_empire_reference()  # Update global reference

            # Handle map loading and validation
            xml_dir = os.path.dirname(file_path)
            success = self._load_and_validate_empire_map(empire_obj, xml_dir)
            if not success:
                return  # User cancelled map loading

            # Clear existing visuals and render loaded empire
            self._render_loaded_empire()

            # Update UI state after loading empire
            self.update_ui_state()

            # Update file state and window title
            self.current_file_path = file_path
            self.has_unsaved_changes = False
            self.update_window_title()

            self.show_message(UIS.INFO, UIS.EMP_LOADED.format(file_path=file_path), 0)  # Information, Ok only

        except FileNotFoundError:
            log.error(f"File not found: {file_path}")
            self.show_message(UIS.ERROR, UIS.FILE_NOT_FOUND.format(file_path=file_path), 2)  # Critical, Ok only
        except Exception as e:
            log.error(e)
            self.show_message(UIS.ERROR, UIS.LOAD_ERROR.format(error=str(e)), 2)  # Critical, Ok only
        finally:
            self.update_ui_state()

    def save_empire_xml(self):
        """Save current empire to XML file, optionally into Augustus user folders if configured."""

        # Warn about 'Our City' but let the user decide
        our_city_exists, _ = self.state.has_our_city()
        if not our_city_exists:
            if self.show_message(UIS.WARNING, UIS.OUR_CITY_NOT_SET, 3, 1, 2) != QBTN_YES:
                return

        if not self.state.check_if_empire():
            self.show_message(UIS.WARNING, UIS.NO_EMP_SAVE, 1)  # Warning, Ok only
            return

        # Read default folder from settings (fallback to CWD)

        settings = self.state.settings
        default_folder = settings.value("default_save_folder", type=str) or os.getcwd()
        if not os.path.exists(default_folder):
            default_folder = os.getcwd()

        # Detect Augustus user folders (set by your earlier flow)
        aug_user = self.state.augustus_user_path
        aug_emp_dir = self.state.augustus_editor_empires_path
        aug_img_dir = self.state.augustus_community_image_path

        use_augustus_dirs = False
        if aug_user and os.path.isdir(aug_user) and aug_emp_dir and aug_img_dir:
            use_augustus_dirs = self.show_message(UIS.SAVE_AUGUSTUS, UIS.AUGUSTUS_PROMPT, 3, 1, 1) == QBTN_YES

        # Choose the folder the file dialog should open in
        initial_dir = aug_emp_dir if use_augustus_dirs else default_folder

        # Suggest a sensible filename
        if getattr(self, "current_file_path", None):
            suggested_name = os.path.splitext(os.path.basename(self.current_file_path))[0] + ".xml"
        else:
            # Use the empire's name if available
            name = ""
            try:
                name = getattr(self.state.current_empire_object, "name", "") or ""
            except Exception:
                pass
            name = re.sub(r"[^A-Za-z0-9_\-]+", "_", name).strip("_") if name else "empire"
            suggested_name = f"{name}.xml"

        suggested_path = os.path.join(initial_dir, suggested_name)

        # Save As dialog (still allows user to rename/choose)
        file_path, _ = QWI.QFileDialog.getSaveFileName(
            self, "Save Empire XML", suggested_path, "XML Files (*.xml);;All Files (*)"
        )
        if not file_path:
            return  # User cancelled

        # Ensure .xml
        if not file_path.lower().endswith(".xml"):
            file_path += ".xml"

        # Guarantee the folder exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        try:
            # Prepare map info; if saving in Augustus mode, put images in aug_img_dir
            # Use global Empire reference instead of self.state.current_empire_object
            img_dir_override = aug_img_dir if use_augustus_dirs else ""
            self._prepare_empire_map_info_for_save(Empire, file_path, img_dir_override)
            # Write XML
            Empire.write_xml(file_path)
            # Update state/UI
            self.current_file_path = file_path
            self.has_unsaved_changes = False
            self.update_window_title()
            self.show_message(UIS.SUCCESS, UIS.EMP_SAVED_MSG.format(file_path=file_path), 0)  # Information, Ok only
        except Exception as e:
            log.error(e)
            self.show_message(UIS.SAVE_ERROR, UIS.SAVE_ERROR_MSG.format(error=str(e)), 2)  # Critical, Ok only

    def remove_city(self, city):
        """Remove a city from the empire and scene."""
        # Check if this city should be unticked in the default cities menu
        self.default_cities_manager.untick_city_if_removed(city)

        # Use global Empire reference
        if Empire and city in Empire.cities:
            city_index = self._get_city_index(city)
            if city_index is not None:
                # Remove trade route through graphics manager
                Manager.remove_trade_route(city)
            Empire.cities.remove(city)
            self.mark_unsaved_changes()  # Mark as unsaved after removing city
        Manager.remove_city(city)
        if self.selected_item and self.selected_item.data(QCO.Qt.ItemDataRole.UserRole) == ed.CityType.OURS:
            self.deselect_item()

    def move_city(self, city_obj):
        """Enter drag mode to move an existing city."""
        self.moving_city = city_obj
        pm = Manager.get_city_pixmap(city_obj.city_type, self)

        # Cache the pixmap for cursor
        self.drag_pixmap = pm
        self.is_dragging = True
        self.ui.graphicsView.setInteractive(False)
        self.ui.graphicsView.setDragMode(QWI.QGraphicsView.DragMode.NoDrag)
        self._set_all_cities_interactive(False)

        # Set cursor immediately and also after context menu closes
        self.set_drawing_cursor(True, pm)
        QCO.QTimer.singleShot(0, lambda: self.set_drawing_cursor(True, pm))

    def _set_all_cities_interactive(self, enable: bool):
        """Set interactivity for all city items through graphics manager."""
        for city_obj in Manager.city_objects.values():
            city_obj.update_interactivity(enable)

    def edit_city(self, city_obj):
        snapshot = copy.deepcopy(city_obj)
        dlg = emp_dlg.CityPropertiesDialog(city_obj, self)
        result = None
        try:
            result = dlg.exec()
        finally:
            dlg.deleteLater()  # deleted when control returns to the main event loop
        if result != QWI.QDialog.Accepted:
            return  # cancel -> no changes
        if dlg.requested_route_draw:
            if city_obj.trade_route and len(city_obj.trade_route.trade_points) > 0:
                if self.show_message(UIS.TR_EXISTS, UIS.TR_EXISTS_MSG, 1, 1, 2) != QBTN_YES:
                    QCO.QTimer.singleShot(100, lambda: self.edit_city(city_obj))
                    return
                else:
                    # Clear both model and visuals for this specific city
                    city_index = self._get_city_index(city_obj)
                    if city_index is not None:
                        Manager.remove_trade_route(city_obj)
                    city_obj.trade_route.trade_points = []
            self.start_trade_route(city_obj)
            self.return_to_dialog = True
            return

        # Check if city type changed from trade to non-trade
        old_type = snapshot.city_type
        new_type = city_obj.city_type

        # If city type changed from trade to non-trade, remove trade route
        if old_type == ed.CityType.TRADE and new_type != ed.CityType.TRADE:
            # Clear trade route for non-trade cities
            city_index = self._get_city_index(city_obj)
            if self.delete_trade_route_from_item(None, city=city_obj):
                if city_index is not None:
                    Manager.remove_trade_route(city_obj)
                if city_obj.trade_route:
                    city_obj.trade_route.trade_points = []
                    city_obj.trade_route = None

        # validations
        if city_obj.city_type == ed.CityType.OURS:
            has_ours, ours = self.state.has_our_city()
            if has_ours and ours is not city_obj:
                self.show_message(UIS.DUP_OUR_CITY, UIS.DUP_OUR_CITY_MSG, 1)  # Warning, Ok only
                # revert and reopen
                city_obj.__dict__.clear()
                city_obj.__dict__.update(copy.deepcopy(snapshot.__dict__))
                return  # Exit early after revert

        # Check if trade route type changed and re-render if needed
        old_route_type = snapshot.trade_route.r_type if snapshot.trade_route else None
        new_route_type = city_obj.trade_route.r_type if city_obj.trade_route else None

        if old_route_type != new_route_type and city_obj.trade_route and city_obj.trade_route.trade_points:
            # Re-render trade route with new type colors
            Manager.add_trade_route(city_obj, self)

        # valid -> update visuals
        if not self.trade_drawing_active:
            key = id(city_obj)
            if key in self.city_items:
                it = self.city_items[key]
                pm = Manager.get_city_pixmap(city_obj.city_type, self)
                it.setPixmap(pm)
                it.setData(QCO.Qt.ItemDataRole.UserRole, city_obj.city_type)
        self.refresh_map()

    # %% ui and drawing
    def update_ui_state(self):
        """Update UI elements based on current empire state."""
        has_empire = self.state and self.state.current_empire_object is not None and self.state.has_any_data()

        # Enable/disable Empire Properties action based on whether we have an empire

        self.ui.menuEmpireProperties.setEnabled(has_empire)
        self.ui.actionSave.setEnabled(has_empire)

    def _validate_empire_bounds(self, width, height, empire=None, remove_invalid=False):
        """
        Validate that empire elements fit within the given dimensions.

        Args:
            width: Map width
            height: Map height
            empire: Empire object to validate (defaults to global Empire)
            remove_invalid: If True, remove invalid elements and return count.
                           If False, return list of invalid element descriptions.

        Returns:
            If remove_invalid=True: int (count of removed elements)
            If remove_invalid=False: list[str] (descriptions of invalid elements)
        """
        empire = empire or Empire
        if not empire:
            return 0 if remove_invalid else []

        invalid_elements = []
        removed_count = 0

        def is_out_of_bounds(x, y):
            return not (0 <= x < width and 0 <= y < height)

        # Check cities
        if empire.cities:
            cities_to_remove = []
            for city in empire.cities:
                if is_out_of_bounds(city.x, city.y):
                    if remove_invalid:
                        cities_to_remove.append(city)
                        log.debug(f"Removing city '{city.name}' at ({city.x}, {city.y}) - outside map bounds")
                    else:
                        invalid_elements.append(f"City '{city.name}' at ({city.x}, {city.y})")

            if remove_invalid:
                for city in cities_to_remove:
                    empire.cities.remove(city)
                    removed_count += 1

        # Check border edges
        if empire.border and empire.border.edges:
            edges_to_remove = []
            for i, edge in enumerate(empire.border.edges):
                if is_out_of_bounds(edge.x, edge.y):
                    if remove_invalid:
                        edges_to_remove.append(edge)
                        log.debug(f"Removing border edge at ({edge.x}, {edge.y}) - outside map bounds")
                    else:
                        invalid_elements.append(f"Border edge {i + 1} at ({edge.x}, {edge.y})")

            if remove_invalid:
                for edge in edges_to_remove:
                    empire.border.edges.remove(edge)
                    removed_count += 1

        # Check trade route points
        if empire.cities:
            for city in empire.cities:
                if city.trade_route and city.trade_route.trade_points:
                    points_to_remove = []
                    for i, point in enumerate(city.trade_route.trade_points):
                        if is_out_of_bounds(point.x, point.y):
                            if remove_invalid:
                                points_to_remove.append(point)
                                log.debug(f"Removing trade route point at ({point.x}, {point.y}) - outside map bounds")
                            else:
                                invalid_elements.append(
                                    f"Trade route point {i + 1} for '{city.name}' at ({point.x}, {point.y})"
                                )

                    if remove_invalid:
                        for point in points_to_remove:
                            city.trade_route.trade_points.remove(point)
                            removed_count += 1

        # Check invasion paths (only in remove mode, as this wasn't in the original report function)
        if remove_invalid and empire.invasion_paths:
            for invasion_path in empire.invasion_paths:
                if invasion_path.battles:
                    battles_to_remove = []
                    for battle in invasion_path.battles:
                        if is_out_of_bounds(battle.x, battle.y):
                            battles_to_remove.append(battle)
                            log.debug(f"Removing invasion battle at ({battle.x}, {battle.y}) - outside map bounds")

                    for battle in battles_to_remove:
                        invasion_path.battles.remove(battle)
                        removed_count += 1

        # Check distant battle paths (only in remove mode, as this wasn't in the original report function)
        if remove_invalid and empire.distant_battle_paths:
            for path in empire.distant_battle_paths:
                if path.battles:
                    battles_to_remove = []
                    for battle in path.battles:
                        if is_out_of_bounds(battle.x, battle.y):
                            battles_to_remove.append(battle)
                            log.debug(f"Removing distant battle at ({battle.x}, {battle.y}) - outside map bounds")

                    for battle in battles_to_remove:
                        path.battles.remove(battle)
                        removed_count += 1

        return removed_count if remove_invalid else invalid_elements

    def _update_empire_map_info(self, image_path=None, pixmap=None):
        """Update the current empire's map information with background details."""
        if not Empire:
            return

        # Ensure we have a map_info object (upgrade to version 2 if needed)
        if Empire.version == 1 or Empire.map_info is None:
            Empire.version = 2
            Empire.map_info = ed.Map()

        # Update map information
        if image_path:
            Empire.map_info.image = image_path
        if pixmap and not pixmap.isNull():
            Empire.map_info.width = pixmap.width()
            Empire.map_info.height = pixmap.height()
            # Reset offsets for new background
            Empire.map_info.x_offset = 0
            Empire.map_info.y_offset = 0
            Empire.map_info.coordinates_x_offset = 0
            Empire.map_info.coordinates_y_offset = 0

    def _prepare_empire_map_info_for_save(self, empire, file_path, img_path: str = "", xml_path: str = ""):
        """Update empire map_info based on current background before saving.

        If img_path is provided, images are written there (e.g., Augustus 'community/image').
        Otherwise they go to '<xml_dir>/image'.
        """
        if not self.bg_item or self.bg_type == ed.EmpBackgroundTypes.LEGACY:
            # For legacy backgrounds or no background, keep version 1 format
            empire.version = 1
            empire.map_info = None
            return

        empire.version = 2  # For custom backgrounds, set up map_info for version 2+

        pixmap = self.bg_item.pixmap()
        if pixmap.isNull():
            empire.map_info = None
            return

        # Where the XML will live
        xml_dir = os.path.dirname(file_path)
        images_dir = img_path if img_path else os.path.join(xml_dir, "image")
        if not os.path.exists(images_dir):  # Create images directory if it doesn't exist
            os.makedirs(images_dir, exist_ok=True)

        # Determine the filename of the source image we're currently using
        if hasattr(self, "_current_image_path") and self._current_image_path:
            image_filename = os.path.basename(self._current_image_path)
            source_path = self._current_image_path
        else:
            image_filename = "background.png"
            source_path = None

        # Target path in the chosen images folder
        target_path = os.path.join(images_dir, image_filename)

        # Copy the image file if we have a source and target doesn't exist
        if source_path and os.path.exists(source_path) and not os.path.exists(target_path):
            try:
                shutil.copy2(source_path, target_path)
                log.debug(f"Copied background image to: {target_path}")
            except Exception as e:
                log.error(f"Warning: Could not copy image file: {e}")

        # Create or update map_info
        if empire.map_info is None:
            empire.map_info = ed.Map()

        # Game engine requirement: just the filename
        empire.map_info.image = image_filename
        empire.map_info.width = pixmap.width()
        empire.map_info.height = pixmap.height()
        empire.map_info.x_offset = 0
        empire.map_info.y_offset = 0
        empire.map_info.coordinates_relative = False
        empire.map_info.coordinates_x_offset = 0
        empire.map_info.coordinates_y_offset = 0

        log.debug(f"Updated empire map_info: {image_filename} ({pixmap.width()}x{pixmap.height()})")

    def _render_loaded_empire(self):
        """Render the loaded empire data onto the scene."""
        if not Empire:
            return

        try:  # Clear existing city markers and visual state
            self.city_items.clear()
        except Exception as e:
            log.error(e)
        try:
            self._clear_scene_state()
        except Exception as e:
            log.error(e)

        # If scene has items, clear and reset (but keep background)
        if self.scene and self.bg_item:
            # Remove all items except background
            for item in list(self.scene.items()):
                if item != self.bg_item:
                    self.scene.removeItem(item)
        elif self.bg_item == None:
            if Empire.version > 1:
                log.debug("Loading background image from empire map info")
            else:
                log.debug("loading default empire map")
                self.on_default_empire_map_selected()

        # Place cities on scene
        if Empire and Empire.cities:
            for city in Empire.cities:
                Manager.add_city(city, main_window=self)
                if city.trade_route is not None:
                    # Use graphics manager to handle trade route rendering
                    graphics_obj = Manager.add_trade_route(city, self)
            graphics_obj.render_trade_route()

        # Render empire border if it exists
        if Empire and Empire.border:
            self.empire_border = True
            Manager.add_border(Empire.border, self)

        # Repopulate Default Cities menu after loading empire
        self.default_cities_manager.populate_menu()
        # Update Default Cities menu state based on current background
        self.default_cities_manager.update_menu_state()

    def _load_and_validate_empire_map(self, empire, xml_dir):
        """Load & validate the empire map.
        Returns:
            True  -> map set (custom or default/legacy fallback)
            False -> user cancelled file selection when asked to locate a missing image
        """

        def use_default(title, msg):
            self.show_message(title, msg, 1)
            self.on_default_empire_map_selected()
            return True

        try:
            while True:
                # Legacy or no map selected
                if getattr(empire, "version", None) == 1 or not getattr(empire, "map_info", None):
                    title, msg = (
                        (UIS.LEGACY_EMP, UIS.LEGACY_EMP_MSG) if empire.version == 1 else (UIS.NO_MAP, UIS.NO_MAP_MSG)
                    )
                    return use_default(title, msg)

                map_info = empire.map_info
                image_path = map_info.image
                if not image_path:
                    return use_default(UIS.NO_IMAGE, UIS.NO_IMAGE_MSG)

                # Try to resolve path, otherwise prompt user
                found_path = self._find_map_image(image_path, xml_dir)
                if not found_path:
                    self.show_message(UIS.IMG_NOT_FOUND, UIS.IMG_NOT_FOUND_PROMPT.format(image_path), 0)
                    found_path, _ = QWI.QFileDialog.getOpenFileName(
                        self, f"Locate Map Image: {os.path.basename(image_path)}", xml_dir, UIS.IMAGE_FILES
                    )
                    if not found_path:
                        self.show_message(UIS.NO_IMG_SEL, UIS.NO_IMG_SEL_MSG, 1)
                        return False

                # Load image and validate contents
                try:
                    pil_image = Image.open(found_path)
                    iw, ih = pil_image.size
                    if (map_info.width, map_info.height) != (iw, ih):
                        log.debug(f"UPDATE: {map_info.width}x{map_info.height} to {iw}x{ih}")
                        map_info.width, map_info.height = iw, ih

                    self._current_image_path = found_path
                    self.set_background_image(pil_image)
                    self.bg_type = self._get_background_type_from_image_path(found_path)
                    self.default_cities_manager.update_menu_state()
                    return True

                except Exception as e:
                    log.error(e)
                    self.show_message(
                        UIS.IMG_LOAD_ERR, UIS.IMG_LOAD_FAIL.format(found_image_path=found_path, error=str(e)), 2
                    )
                    return use_default(UIS.NO_IMAGE, UIS.NO_IMAGE_MSG)

        except Exception as e:
            log.error(e)
            self.show_message(UIS.MAP_LOAD_ERR, UIS.MAP_LOAD_FAIL.format(error=str(e)), 2)
            return use_default(UIS.NO_IMAGE, UIS.NO_IMAGE_MSG)

    def _find_map_image(self, image_path, xml_dir):
        """Try to find the map image in various locations relative to the XML file."""
        filename = os.path.basename(image_path)
        if os.path.isabs(image_path) and os.path.exists(image_path):
            return image_path

        # Try relative to XML directory
        rel_path = os.path.join(xml_dir, image_path)
        if os.path.exists(rel_path):
            return rel_path

        if getattr(sys, "frozen", False):
            base_path = sys._MEIPASS
        else:
            base_path = os.path.dirname(os.path.abspath(__file__))

        maps_path = os.path.join(base_path, "augustus_assets", "Areldir_maps", filename)
        if os.path.exists(maps_path):
            return maps_path
        # Try in images subdirectory
        images_path = os.path.join(xml_dir, "images", image_path)
        if os.path.exists(images_path):
            return images_path

        # Try just the filename in XML directory

        filename_path = os.path.join(xml_dir, filename)
        if os.path.exists(filename_path):
            return filename_path

        # Try filename in images subdirectory
        filename_images_path = os.path.join(xml_dir, "images", filename)
        if os.path.exists(filename_images_path):
            return filename_images_path

        return None

    def _get_background_type_from_image_path(self, image_path):
        """Get the EmpBackgroundTypes enum value for a given image path."""
        if not image_path:
            return ed.EmpBackgroundTypes.CUSTOM

        filename = os.path.basename(image_path)

        default_map_types = {
            "Orbis_Terrarum_Empire_Map.png": ed.EmpBackgroundTypes.BIG_MAP,
            "Occidentalis_Empire_Map.png": ed.EmpBackgroundTypes.NORTH_MAP,
            "Orientalis_Empire_Map.png": ed.EmpBackgroundTypes.SOUTH_MAP,
        }

        # Check filename first
        if filename in default_map_types:
            return default_map_types[filename]

        # Check if the path contains the characteristic folder structure
        normalized_path = image_path.replace("\\", "/")
        for default_filename, bg_type in default_map_types.items():
            if f"augustus_assets/Areldir_maps/{default_filename}" in normalized_path:
                return bg_type

        return ed.EmpBackgroundTypes.CUSTOM

    def delete_trade_route_from_item(self, item, city=None):
        """Delete trade route path from context menu selection."""
        if city is None:
            city_index = item.data(QCO.Qt.ItemDataRole.UserRole + 1)
            city = self._get_city_by_index(city_index)
        else:
            city_index = self._get_city_index(city)
        if city and city.trade_route and city.trade_route.trade_points:
            if self.show_message(UIS.DEL_TR, UIS.DEL_TR_CONFIRM.format(city_name=city.name), 3, 1, 2) == QBTN_YES:
                # Clear selection if this was the selected route
                Manager.deselect_all()
                # Clear only the plotted path, keep the trade route object
                city.trade_route.trade_points.clear()
                self.mark_unsaved_changes()  # Mark as unsaved after deleting trade route
                Manager.remove_trade_route(city)
                return True
        else:
            try:
                Manager.remove_trade_route(city)
            except Exception as ex:
                log.error(f"Error clearing trade route visuals: {ex}")
        return False

    def edit_city_from_trade_route_item(self, item):
        """Edit city from trade route context menu selection."""
        city_index = item.data(QCO.Qt.ItemDataRole.UserRole + 1)
        city = self._get_city_by_index(city_index)
        if city:
            self.edit_city(city)

    def _trade_route_ends_at_city(self, trade_route, city):
        """Check if a trade route ends at the specified city (last point within city bounds)."""
        if not trade_route or not trade_route.trade_points or len(trade_route.trade_points) < 1:
            return False

        # Get the last trade point
        last_point = trade_route.trade_points[-1]

        # Get city bounds (coordinates are center-based)
        city_pixmap = Manager.get_city_pixmap(city.city_type, self)
        city_half_width = city_pixmap.width() // 2
        city_half_height = city_pixmap.height() // 2

        # Check if last point is within city icon bounds (center-based)
        return (
            city.x - city_half_width <= last_point.x <= city.x + city_half_width
            and city.y - city_half_height <= last_point.y <= city.y + city_half_height
        )

    def _get_city_by_index(self, index: int):
        """Get city by index from current empire's cities list."""
        if not Empire or index < 0 or index >= len(Empire.cities):
            return None
        return Empire.cities[index]

    def set_drawing_cursor(self, enable: bool, pixmap=None):
        if not enable:
            QWI.QApplication.restoreOverrideCursor()
            self._win_cursor_applied = False
            self._win_cursor_sig = None
            return

        # Decide pixmap from mode if not provided
        if pixmap is None:
            if getattr(self, "edge_drawing_active", False):
                pixmap = self.edge_cursor_pixmap
            elif getattr(self, "trade_drawing_active", False):
                pixmap = self.land_cursor_pixmap if getattr(self, "trade_is_land", False) else self.sea_cursor_pixmap

        # If still none, fall back to default (unset)
        if pixmap is None:
            QWI.QApplication.restoreOverrideCursor()

            self._win_cursor_applied = False
            self._win_cursor_sig = None
            return

        hsx, hsy = pixmap.width() // 2, pixmap.height() // 2
        sig = (pixmap.cacheKey(), hsx, hsy)

        if not self._win_cursor_applied or self._win_cursor_sig != sig:
            QWI.QApplication.setOverrideCursor(QGU.QCursor(pixmap, hsx, hsy))

            self._win_cursor_applied = True
            self._win_cursor_sig = sig

    def update_window_title(self):
        """Update the window title to show current file and unsaved changes status."""
        base_title = f"Empire Editor v{self.program_editor_version}"

        if self.current_file_path:
            filename = os.path.basename(self.current_file_path)
            title = f"{filename} - {base_title}"
        else:
            title = f"New Empire - {base_title}"

        if self.has_unsaved_changes:
            title = f"*{title}"

        self.setWindowTitle(title)

    def mark_unsaved_changes(self):
        """Mark that the empire has unsaved changes and update the title."""
        if not self.has_unsaved_changes:
            self.has_unsaved_changes = True
            self.update_window_title()

    # %% GLOBAL EVENT FILTER
    def eventFilter(self, obj, event):
        et = event.type()

        # 1) Always ignore modal dialogs
        if QWI.QApplication.activeModalWidget() or QWI.QApplication.activePopupWidget():
            return False

        # 2) Dispatch by event type
        if et == QCO.QEvent.Type.MouseMove:
            return self._handle_mouse_move(event)

        elif et in (QCO.QEvent.Type.MouseButtonPress, QCO.QEvent.Type.MouseButtonRelease):
            return self._handle_mouse_click(event)

        elif et == QCO.QEvent.Type.KeyPress:
            return self._handle_key_press(event)

        return QCO.QObject.eventFilter(self, obj, event)

    def _handle_key_press(self, event):
        """Handle keyboard events for vertex editing and other shortcuts."""
        key = event.key()

        # Escape key cancels various operations
        if key == QCO.Qt.Key.Key_Escape:
            if self.vertex_editing_active:
                self.cancel_vertex_editing()
                return True
            elif self.edge_drawing_active:
                self._edge_prompt_incomplete()
                return True
            elif self.trade_drawing_active:
                self._abort_trade_drawing()
                return True

        # Backspace/Delete for undo in drawing modes
        elif key in (QCO.Qt.Key.Key_Backspace, QCO.Qt.Key.Key_Delete):
            if self.trade_drawing_active:
                self._trade_undo_last_point()
                return True

        return False  # Don't consume other keys

    # =========================
    # HELPER HANDLERS
    # =========================

    def _handle_mouse_move(self, event):
        """Mouse move: update label, dragging icon, vertex editing, and edge preview."""
        gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else QGU.QCursor.pos()
        view = self.ui.graphicsView
        vp = view.viewport()
        vp_pos = vp.mapFromGlobal(gp)

        # Update position label
        if vp.rect().contains(vp_pos):
            scene_pos = view.mapToScene(vp_pos)

            # Handle vertex editing
            if self.vertex_editing_active:
                self.update_vertex_position(scene_pos)
            elif self.edge_drawing_active:
                self._edge_update_temp_line(scene_pos)
            elif self.trade_drawing_active:
                self._trade_update_temp_line(scene_pos)

            self._update_mouse_position_label(scene_pos)

        return False  # don't consume

    def _handle_mouse_click(self, event):
        """Mouse clicks: route to drag, edge drawing, vertex editing, or selection logic."""
        gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else QGU.QCursor.pos()
        view = self.ui.graphicsView
        vp = view.viewport()
        inside_view = vp.rect().contains(vp.mapFromGlobal(gp))
        btn = event.button()
        et = event.type()

        # Vertex editing mode - handle both press and release
        if self.vertex_editing_active:
            if et == QCO.QEvent.Type.MouseButtonPress:
                if btn == QCO.Qt.MouseButton.RightButton:
                    # Right-click cancels vertex editing
                    self.cancel_vertex_editing()
                    return True
                elif btn == QCO.Qt.MouseButton.LeftButton:
                    # Left-click finishes vertex editing (click-to-drop)
                    scene_pos = view.mapToScene(vp.mapFromGlobal(gp))
                    self.finish_vertex_editing(scene_pos)
                    return True
                # Other buttons continue editing
                return True

        # Dragging mode
        if self.is_dragging:
            return self._handle_drag_click(event, gp, inside_view)

        # Edge drawing mode
        if self.edge_drawing_active and et == QCO.QEvent.Type.MouseButtonPress:
            return self._handle_edge_click(event, gp, inside_view)

        # Trade drawing mode
        if self.trade_drawing_active and et == QCO.QEvent.Type.MouseButtonPress:
            return self._handle_trade_click(event, gp, inside_view)

        # Normal mode selection
        if not self.is_dragging and not self.edge_drawing_active and et == QCO.QEvent.Type.MouseButtonPress:
            return self._handle_normal_click(event, gp, inside_view)

        return False

    # =========================
    # SUB-MODE HANDLERS
    # =========================

    def _handle_drag_click(self, event, gp, inside_view):
        # cancel move/drag on right click (press or release), anywhere
        if event.button() == QCO.Qt.MouseButton.RightButton:
            self.moving_city = None
            self.deselect_item()
            return True

        if event.type() == QCO.QEvent.Type.MouseButtonPress:
            if event.button() == QCO.Qt.MouseButton.LeftButton and not inside_view:
                self.deselect_item()
                return True

        elif event.type() == QCO.QEvent.Type.MouseButtonRelease:
            if event.button() == QCO.Qt.MouseButton.LeftButton:
                if inside_view:
                    view = self.ui.graphicsView
                    vp = view.viewport()
                    vp_pos = vp.mapFromGlobal(gp)  # viewport coords
                    scene_pos = view.mapToScene(vp_pos)

                    # Check if we're moving a city - if so, handle_drop will reset state
                    was_moving_city = self.moving_city is not None
                    self.handle_drop(scene_pos)

                    # Only deselect if we weren't moving a city (city move handles its own state reset)
                    if not was_moving_city:
                        self.deselect_item()
                else:
                    # Clicked outside view, always deselect
                    self.deselect_item()
                return True

        return False

    def _handle_edge_click(self, event, gp, inside_view):
        if event.button() == QCO.Qt.MouseButton.RightButton or not inside_view:
            self._edge_prompt_incomplete()
            return True
        if event.button() == QCO.Qt.MouseButton.LeftButton:
            scene_pos = self.ui.graphicsView.mapToScene(self.ui.graphicsView.viewport().mapFromGlobal(gp))
            xy = self._scene_to_image_xy(scene_pos)
            if xy is None:
                self._edge_prompt_incomplete()
                return True
            x, y = xy
            close_idx = self._edge_hit_existing_point(x, y)
            if close_idx is not None:
                self._finalize_edge(success=True, close_to_index=close_idx)
            else:
                self._edge_append_point(x, y)
            return True
        return False

    def _handle_normal_click(self, event, gp, inside_view):
        # --- RIGHT CLICK ---
        if event.button() == QCO.Qt.MouseButton.RightButton and inside_view:
            scene_pos = self.ui.graphicsView.mapToScene(self.ui.graphicsView.viewport().mapFromGlobal(gp))
            items = self.scene.items(scene_pos)

            for it in items:
                if it.flags() & QWI.QGraphicsItem.ItemIsSelectable:
                    # Optional: auto-select before showing menu
                    self._select_scene_item(it)
                    self._show_context_menu_for_item(it, gp)
                    return True

            # No selectable item -> clear selection
            self.deselect_all()
            return True

        # --- LEFT CLICK ---
        if event.button() == QCO.Qt.MouseButton.LeftButton and inside_view:
            scene_pos = self.ui.graphicsView.mapToScene(self.ui.graphicsView.viewport().mapFromGlobal(gp))
            items = self.scene.items(scene_pos)

            for it in items:
                if it.flags() & QWI.QGraphicsItem.ItemIsSelectable:
                    self._select_scene_item(it)
                    return True

            # Clicked empty spot → clear selection
            self.deselect_all()
            return True

        return False

    # %% Input adjacent Functions
    # %%% Selection handling:
    def _select_scene_item(self, item):
        """
        Handle selecting any selectable object on the scene using the new graphics system.
        Only one selection can be active at a time.
        """
        # Check if this is a vertex handle first
        if item.data(QCO.Qt.ItemDataRole.UserRole) == "VERTEX_HANDLE":
            self.start_vertex_editing(item)
            return

        # Try to find a graphics object for this scene item, including nested objects
        graphics_obj = Manager.get_graphics_object_for_scene_item(item)

        if graphics_obj:
            # Check if this is an edge hit item and select the edge
            edge_index = item.data(QCO.Qt.ItemDataRole.UserRole + 1)
            if edge_index is not None and hasattr(graphics_obj, "select_edge"):
                graphics_obj.select_edge(edge_index)

            # Use graphics manager to select
            Manager.select_object(graphics_obj)
            self.selected_item = item

            # Handle specific object types
            if isinstance(graphics_obj, GRO.CityGraphicsObject):
                return
            elif isinstance(graphics_obj, GRO.TradeRouteGraphicsObject):
                # Handle trade route selection - graphics objects now handle overlay
                Manager.select_object(graphics_obj)
                return
            elif isinstance(graphics_obj, GRO.BorderGraphicsObject):
                # Handle border selection - use graphics manager
                Manager.select_object(graphics_obj)
                return
            elif isinstance(graphics_obj, GRO.EmpireEdgeGraphicsObject):
                # Handle individual edge selection - use graphics manager
                Manager.select_object(graphics_obj)
                return
        self.deselect_all()

    # ---------- LIST / DRAGGING ----------
    def _update_mouse_position_label(self, scene_pos):
        pm_item = self.bg_item
        if pm_item is not None:
            img_pos = pm_item.mapFromScene(scene_pos)
            x, y = int(img_pos.x()), int(img_pos.y())
            pm = pm_item.pixmap()
            if 0 <= x < pm.width() and 0 <= y < pm.height():
                self.ui.mouse_position_label.setText(f"Mouse Position: ({x}, {y})")
            else:
                self.ui.mouse_position_label.setText("")
        return

    def on_item_clicked(self, item):
        if self.selected_item == item:  # already selected -> deselect
            self.deselect_item()
        else:
            self.select_item(item)  # visually mark it selected in the list
            self.ui.listWidget.setCurrentItem(item)

    def select_item(self, item):
        """Select an item from the list widget using the new graphics system."""
        self.deselect_all()  # clear current selections first

        # Get the selectable element
        element_index = item.data(QCO.Qt.ItemDataRole.UserRole)
        if element_index is None or element_index >= len(self.selectable_elements):
            return

        selectable_element = self.selectable_elements[element_index]

        # Store references to both the list item and the selectable element
        self.selected_item = item
        self.selected_list_element = selectable_element  # The selectable element from list

        pixmap = selectable_element.pixmap
        self.ui.graphicsView.setInteractive(False)

        # cache the exact pixmap used for drag
        self.drag_pixmap = pixmap

        # Don't create a floating icon - use cursor instead
        self.is_dragging = True
        self.set_drawing_cursor(True, pixmap)
        self.ui.graphicsView.setDragMode(QWI.QGraphicsView.DragMode.NoDrag)

        self._set_all_cities_interactive(False)

    def deselect_item(self):
        self.selected_item = None
        self.selected_list_element = None
        self.is_dragging = False
        self.set_drawing_cursor(False)
        self.ui.graphicsView.setInteractive(True)
        self.ui.graphicsView.setDragMode(QWI.QGraphicsView.DragMode.NoDrag)  # not ScrollHandDrag
        # FIX: also clear the QListWidget’s selection so it’s not visually highlighted
        self.ui.listWidget.clearSelection()
        self._set_all_cities_interactive(True)

    # ===================================================================
    # CORE VISUAL STATE MANAGEMENT
    # ===================================================================

    def deselect_all(self):
        """Clear all selection states using the new graphics system."""
        # Use graphics manager to deselect
        Manager.deselect_all()

        # Clear other selection states
        self.clear_vertex_handles()
        self.selected_item = None
        self.selected_list_element = None
        self.selected_edge_index = None

    def _clear_selection_overlay(self, overlay_type):
        """Generic function to clear selection overlays."""
        if overlay_type == "trade_route":
            # Trade route selection now handled by graphics objects
            pass
        elif overlay_type == "vertex":
            # Vertex handles now handled by graphics objects
            self.vertex_editing_active = False

    def clear_vertex_handles(self):
        """Remove vertex editing handles."""
        self._clear_selection_overlay("vertex")

    # ===================================================================
    # UNIFIED MESSAGE BOXES & UTILITIES
    # ===================================================================

    def _clear_scene_state(self):
        """Clear all scene-related state when scene is cleared or reset using the new graphics system."""
        # Clear graphics manager
        Manager.clear_all()

        # Clear selection state
        self.selected_item = None
        self.selected_edge_index = None

        # Clear city items tracking (items will be removed from scene by scene.clear())
        try:
            self.city_items.clear()
            self.city_labels.clear()

        except Exception as e:
            log.error(f"{e}")
        # Clear drawing states
        self.edge_drawing_active = False
        self.edge_points_img = []
        self.edge_point_items = []
        self.edge_line_items = []
        self.edge_temp_line_item = None

        self.trade_drawing_active = False
        self.trade_drawing_points = []
        self.trade_drawing_point_items = []
        self.trade_drawing_line_items = []
        self.trade_temp_line_item = None
        self.trade_route_city = None

        self.vertex_editing_active = False

    # ===================================================================
    # CITY & ENTITY MANAGEMENT
    # ===================================================================

    def clear_empire_border_visual(self):
        """Clear empire border visuals."""
        Manager.remove_border()

    # ===================================================================
    # TRADE ROUTE CLICK HANDLING & DRAWING OPERATIONS
    # ===================================================================

    def _handle_trade_click(self, event, gp, inside_view):
        """Handle mouse clicks during trade route drawing."""
        if event.button() == QCO.Qt.MouseButton.RightButton or not inside_view:
            self._abort_trade_drawing()
            return True

        if event.button() == QCO.Qt.MouseButton.LeftButton:
            scene_pos = self.ui.graphicsView.mapToScene(self.ui.graphicsView.viewport().mapFromGlobal(gp))
            xy = self._scene_to_image_xy(scene_pos)
            if xy is None:
                self._finalize_trade_route(success=False)
                return True
            x, y = xy

            # Add the point
            self._trade_append_point(x, y)

            # Check if clicked on "Our City" to finish
            for city in self.state.current_empire_object.cities:
                if city.city_type == ed.CityType.OURS:
                    city_pixmap = Manager.get_city_pixmap(city.city_type, self)
                    city_half_width = city_pixmap.width() // 2
                    city_half_height = city_pixmap.height() // 2
                    # Check if click is within city bounds (center-based coordinates)
                    if (
                        city.x - city_half_width <= x <= city.x + city_half_width
                        and city.y - city_half_height <= y <= city.y + city_half_height
                    ):
                        self._trade_undo_last_point()
                        self._finalize_trade_route(success=True, reopen_dialog=True)
                        return True
                    break

            # Check for closing on existing point
            hit_idx = self._trade_hit_existing_point(x, y)
            if hit_idx == len(self.trade_drawing_points) - 2 and len(self.trade_drawing_points) >= 2:
                resp = self.show_message(UIS.INCOMPLETE_TR, UIS.INCOMPLETE_TR_MSG, 0, 2, 3)
                if resp == QBTN_YES:
                    self._trade_undo_last_point()
                    self._finalize_trade_route(success=True)
                elif resp == QBTN_NO:
                    self._abort_trade_drawing()
                else:
                    self._trade_undo_last_point()
            return True
        return False

    def start_trade_route(self, city):
        """Start drawing a trade route for a specific city."""
        if self.bg_item is None:
            self.show_message(UIS.NO_BG, UIS.NO_BG_MSG, 1)  # Warning, Ok only
            return

        self._abort_trade_drawing()
        self.trade_drawing_active = True
        self.trade_is_land = bool(city.trade_route and city.trade_route.r_type == ed.TradeRouteType.LAND)
        self.trade_route_city = city
        self.trade_drawing_points = []
        self.trade_drawing_point_items = []
        self.trade_drawing_line_items = []
        self.trade_temp_line_item = None

        self.ui.graphicsView.setInteractive(False)
        self.set_drawing_cursor(True)

    def _trade_update_temp_line(self, cursor_scene_pos):
        """Update the rubber-band line during trade route drawing."""
        self._update_temp_line("trade", cursor_scene_pos)

    def _trade_create_temp_line(self):
        """Create the rubber-band line for trade route drawing."""
        self._create_temp_line("trade")

    def _trade_append_point(self, x_img: int, y_img: int, make_segment: bool = True):
        """Add a point to the trade route being drawn."""
        self._append_drawing_point(x_img, y_img, "trade", make_segment)

    def _trade_undo_last_point(self):
        """Remove the last trade point and its visual elements."""
        if not self.trade_drawing_points:
            return

        self.trade_drawing_points.pop()

        if self.trade_drawing_point_items:
            dot_item = self.trade_drawing_point_items.pop()
            self.scene.removeItem(dot_item)

        if self.trade_drawing_line_items:
            line_item = self.trade_drawing_line_items.pop()
            self.scene.removeItem(line_item)

        self._trade_create_temp_line()

    def _trade_hit_existing_point(self, x_img: int, y_img: int):
        """Check if click is near an existing trade route point."""
        return self._hit_existing_point(x_img, y_img, self.trade_drawing_points)

    def _finalize_trade_route(self, success: bool, reopen_dialog: bool = False):
        """Finalize the current trade route drawing."""
        city = self.trade_route_city

        if success and len(self.trade_drawing_points) >= 2 and city:
            pts = [ed.TradePoint(x=int(x), y=int(y)) for (x, y) in self.trade_drawing_points]
            ttype = ed.TradeRouteType.LAND if self.trade_is_land else ed.TradeRouteType.SEA

            if city.trade_route is None:
                city.trade_route = ed.TradeRoute(type=ttype, trade_points=pts)
            else:
                city.trade_route.r_type = ttype
                city.trade_route.trade_points = pts

            self.mark_unsaved_changes()  # Mark as unsaved after creating/updating trade route
            self._abort_trade_drawing()
            Manager.add_trade_route(city, self)
        else:
            self._abort_trade_drawing()

        self.ui.graphicsView.setInteractive(True)

        if reopen_dialog and city:
            QCO.QTimer.singleShot(100, lambda: self.edit_city(city))

    def _abort_trade_drawing(self):
        """Abort current trade route drawing session."""
        self._abort_drawing("trade", erase=True)

    # %%% other input-adjacent
    def _show_context_menu_for_item(self, item, global_pos):
        """Show context menu using the new graphics system."""
        # Try to get graphics object first, including nested objects
        graphics_obj = Manager.get_graphics_object_for_scene_item(item)

        if graphics_obj:
            # Check if this is an edge hit item and select the edge
            edge_index = item.data(QCO.Qt.ItemDataRole.UserRole + 1)
            if edge_index is not None and hasattr(graphics_obj, "select_edge"):
                graphics_obj.select_edge(edge_index)

            # Use new graphics system
            menu_actions = graphics_obj.get_context_menu_actions()
            if menu_actions:
                menu = QWI.QMenu(self)

                # Add edge-specific actions first if edge is selected
                edge_actions = []
                parent_actions = []

                if hasattr(graphics_obj, "selected_edge_index") and graphics_obj.selected_edge_index is not None:
                    # Separate edge-specific from parent actions
                    for label, callback in menu_actions:
                        if any(keyword in label.lower() for keyword in ["vertex", "edge", "point", "hidden", "toggle"]):
                            edge_actions.append((label, callback))
                        else:
                            parent_actions.append((label, callback))
                else:
                    parent_actions = menu_actions

                # Add edge actions first
                for label, callback in edge_actions:
                    if label == "---":  # Handle separator
                        menu.addSeparator()
                    else:
                        act = QGU.QAction(label, self)
                        act.triggered.connect(lambda checked=False, cb=callback: cb())
                        menu.addAction(act)

                # Add separator if we have both types
                if edge_actions and parent_actions:
                    menu.addSeparator()

                # Add parent actions
                for label, callback in parent_actions:
                    if label == "---":  # Handle separator
                        menu.addSeparator()
                    else:
                        act = QGU.QAction(label, self)
                        act.triggered.connect(lambda checked=False, cb=callback: cb())
                        menu.addAction(act)

                menu.exec(global_pos)

    # ===================================================================
    # COORDINATE & GEOMETRY HELPERS
    # ===================================================================

    def _img_to_scene(self, x: float, y: float):
        """Convert image coordinates to scene coordinates."""
        return self.bg_item.mapToScene(x, y) if self.bg_item else None

    def _scene_to_image_xy(self, scene_pos):
        """Convert scene position to image coordinates with bounds checking."""
        if self.bg_item is None:
            return None
        img_pos = self.bg_item.mapFromScene(scene_pos)
        x, y = int(img_pos.x()), int(img_pos.y())
        pm = self.bg_item.pixmap()
        if 0 <= x < pm.width() and 0 <= y < pm.height():
            return x, y
        return None

    def _is_near(self, x1: float, y1: float, x2: float, y2: float, epsilon: float) -> bool:
        """Check if two points are within epsilon distance of each other."""
        return abs(x1 - x2) <= epsilon and abs(y1 - y2) <= epsilon

    def handle_drop(self, scene_pos):
        """Unified drop handler that delegates to specific case handlers."""
        # Handle moving existing city first
        if self.moving_city is not None:
            self._handle_city_move(scene_pos)
            return
        # Determine drop type and delegate to appropriate handler
        graphics_type = None
        # Check if we have a selected element from the list widget
        if self.selected_list_element and isinstance(self.selected_list_element, GRO.SelectableElement):
            graphics_type = self.selected_list_element.graphics_type

        # Delegate to specific handlers
        if graphics_type == GRO.GraphicsObjectType.CITY:
            self._handle_city_drop(scene_pos)
        elif graphics_type == GRO.GraphicsObjectType.BORDER_EDGE:
            self._handle_empire_edge_drop(scene_pos)
        elif graphics_type == GRO.GraphicsObjectType.TRADE_ROUTE:
            self._handle_trade_route_drop(scene_pos)
        elif graphics_type == GRO.GraphicsObjectType.TRADE_POINT:
            self._handle_trade_point_drop(scene_pos)
        elif graphics_type == GRO.GraphicsObjectType.EMPIRE_EDGE:
            self._handle_empire_edge_drop(scene_pos)
        elif graphics_type == GRO.GraphicsObjectType.ORNAMENT:
            self._handle_ornament_drop(scene_pos)
        elif graphics_type == GRO.GraphicsObjectType.INVASION_PATH:
            self._handle_invasion_path_drop(scene_pos)
        elif graphics_type == GRO.GraphicsObjectType.DISTANT_BATTLE_PATH:
            self._handle_distant_battle_path_drop(scene_pos)
        else:
            log.debug(f"Unknown graphics type: {graphics_type}")

    def _handle_city_move(self, scene_pos):
        """Handle moving an existing city."""
        xy = self._scene_to_image_xy(scene_pos)
        city = self.moving_city
        self.moving_city = None

        # Reset dragging state and cursor immediately
        self.is_dragging = False
        self.set_drawing_cursor(False)
        self.ui.graphicsView.setInteractive(True)
        self._set_all_cities_interactive(True)

        if xy is not None:
            x, y = xy
            Manager.remove_city(city)

            # Convert scene position to center coordinates (city coordinates are centers)
            city.x, city.y = x, y

            # Update name label position if it exists
            key = id(city)
            if key in self.city_labels:
                city_item = self.city_items.get(key)
                if city_item:
                    self._create_city_label(city)  # Recreate in new position

            # Update trade route if city has one
            if city.trade_route:
                Manager.add_trade_route(city, self)

            Manager.add_city(city, main_window=self)
            self.refresh_map()  # handle all route updates and stuff

    # ==== CONSOLIDATED DRAWING HELPERS =====================================
    def _hit_existing_point(self, x_img: int, y_img: int, points_list: list) -> int:
        """Generic function to check if click is near an existing point."""
        eps = self.edge_hit_epsilon
        for idx, (px, py) in enumerate(points_list):
            if abs(px - x_img) <= eps and abs(py - y_img) <= eps:
                return idx
        return -1

    def _append_drawing_point(self, x_img: int, y_img: int, drawing_type: str, make_segment: bool = True):
        """Generic function to append a point during drawing (trade route or border)."""
        if self.bg_item is None:
            return

        if drawing_type == "trade":
            self.trade_drawing_points.append((x_img, y_img))

            # Visual marker
            p = self.bg_item.mapToScene(x_img, y_img)
            color = QGU.QColor(255, 140, 0) if self.trade_is_land else QCO.Qt.cyan
            dot_item = self.scene.addEllipse(p.x() - 2, p.y() - 2, 4, 4, QGU.QPen(QCO.Qt.NoPen), QGU.QBrush(color))
            dot_item.setZValue(90)
            self.trade_drawing_point_items.append(dot_item)

            # Segment line
            if make_segment and len(self.trade_drawing_points) >= 2:
                x0, y0 = self.trade_drawing_points[-2]
                p0 = self.bg_item.mapToScene(x0, y0)
                line_item = self.scene.addLine(p0.x(), p0.y(), p.x(), p.y(), QGU.QPen(color, 2))
                line_item.setZValue(80)
                self.trade_drawing_line_items.append(line_item)

            self._create_temp_line("trade")

        elif drawing_type == "edge":
            # Prevent duplicate consecutive points
            if self.edge_points_img and self.edge_points_img[-1] == (x_img, y_img):
                return

            self.edge_points_img.append((x_img, y_img))

            # Red vertex dot
            dot_item = self.scene.addEllipse(
                x_img - 5.0, y_img - 5.0, 10.0, 10.0, QGU.QPen(QCO.Qt.NoPen), QGU.QBrush(QCO.Qt.red)
            )
            dot_item.setZValue(90)
            if dot_item:
                self.edge_point_items.append(dot_item)

            # Segment line
            if make_segment and len(self.edge_points_img) >= 2:
                x0, y0 = self.edge_points_img[-2]
                line_item = self.scene.addLine(x0, y0, x_img, y_img, QGU.QPen(QCO.Qt.red, 2))
                line_item.setZValue(80)
                if line_item:
                    self.edge_line_items.append(line_item)

            self._update_temp_line("edge")

    def _abort_drawing(self, drawing_type: str, erase: bool = True):
        """Generic function to abort drawing operations."""
        if drawing_type == "trade":
            if self.trade_temp_line_item:
                self.scene.removeItem(self.trade_temp_line_item)
                self.trade_temp_line_item = None

            if erase:
                for item in self.trade_drawing_line_items + self.trade_drawing_point_items:
                    self.scene.removeItem(item)

            self.trade_drawing_line_items.clear()
            self.trade_drawing_point_items.clear()
            self.trade_drawing_points = []
            self.trade_drawing_active = False
            self.trade_route_city = None

        elif drawing_type == "edge":
            if self.edge_temp_line_item is not None:
                self.scene.removeItem(self.edge_temp_line_item)
                self.edge_temp_line_item = None

            if erase:
                for it in self.edge_line_items + self.edge_point_items:
                    self.scene.removeItem(it)

            self.edge_line_items.clear()
            self.edge_point_items.clear()
            self.edge_points_img = []
            self.edge_drawing_active = False

        # Common cleanup for both types
        self.set_drawing_cursor(False)
        self.ui.graphicsView.setInteractive(True)

    def _update_temp_line(self, drawing_type: str, cursor_scene_pos=None):
        """Generic function to update temp lines during drawing."""
        if drawing_type == "trade":
            if not (
                self.trade_drawing_active and self.trade_temp_line_item and self.trade_drawing_points and self.bg_item
            ):
                return
            last_x, last_y = self.trade_drawing_points[-1]
            p0 = self.bg_item.mapToScene(last_x, last_y)
            if cursor_scene_pos:
                line = self.trade_temp_line_item.line()
                line.setP1(p0)
                line.setP2(cursor_scene_pos)
                self.trade_temp_line_item.setLine(line)
            if self.trade_drawing_active:
                self.set_drawing_cursor(True)

        elif drawing_type == "edge":
            if not (self.edge_drawing_active and self.edge_points_img and self.bg_item):
                return
            last_x, last_y = self.edge_points_img[-1]
            p_last = self._img_to_scene(last_x, last_y)
            if p_last is None:
                return

            if self.edge_temp_line_item is None:
                self.edge_temp_line_item = self.scene.addLine(
                    p_last.x(), p_last.y(), p_last.x(), p_last.y(), QGU.QPen(QCO.Qt.red, 2)
                )
                self.edge_temp_line_item.setZValue(100)

            if cursor_scene_pos is None:
                self.edge_temp_line_item.setLine(p_last.x(), p_last.y(), p_last.x(), p_last.y())
            else:
                self.edge_temp_line_item.setLine(p_last.x(), p_last.y(), cursor_scene_pos.x(), cursor_scene_pos.y())
            if self.edge_drawing_active:
                self.set_drawing_cursor(True)

    def _create_temp_line(self, drawing_type: str):
        """Generic function to create temp lines for drawing."""
        if drawing_type == "trade":
            if not self.trade_drawing_points or self.bg_item is None:
                return
            last_x, last_y = self.trade_drawing_points[-1]
            p0 = self.bg_item.mapToScene(last_x, last_y)
            pen = QGU.QPen(QGU.QColor(255, 140, 0) if self.trade_is_land else QCO.Qt.cyan, 2)
            if self.trade_temp_line_item is None:
                self.trade_temp_line_item = self.scene.addLine(p0.x(), p0.y(), p0.x(), p0.y(), pen)
                self.trade_temp_line_item.setZValue(100)
            else:
                self.trade_temp_line_item.setLine(p0.x(), p0.y(), p0.x(), p0.y())
        elif drawing_type == "edge":
            # Edge temp line creation is handled in _update_temp_line
            self._update_temp_line("edge")

    # %% Edge drawing
    # ==== small shared helpers ================================================
    # Vertex editing methods are now delegated to graphics objects

    def start_vertex_editing(self, handle_item):
        """Start editing a vertex by making it stick to the mouse."""
        if self.vertex_editing_active:
            return  # Already editing

        # Get vertex information from the handle
        graphics_object = handle_item.data(QCO.Qt.ItemDataRole.UserRole + 3)
        vertex_index = handle_item.data(QCO.Qt.ItemDataRole.UserRole + 2)

        if not graphics_object or vertex_index is None:
            return

        self.vertex_editing_active = True
        self.editing_vertex_index = vertex_index
        self.editing_vertex_handle = handle_item
        self.editing_graphics_object = graphics_object

        # Delegate to the graphics object
        graphics_object.start_vertex_editing(vertex_index, handle_item)

        # Disable view interaction during editing
        self.ui.graphicsView.setInteractive(False)

    def update_vertex_position(self, scene_pos):
        """Update vertex position during dragging."""
        if not self.vertex_editing_active or not self.editing_vertex_handle:
            return

        # Move the handle visually
        rect = self.editing_vertex_handle.rect()
        rect.moveCenter(scene_pos)
        self.editing_vertex_handle.setRect(rect)

        # Delegate to graphics object if available
        if hasattr(self, "editing_graphics_object") and self.editing_graphics_object:
            self.editing_graphics_object.update_vertex_position(self.editing_vertex_index, scene_pos)

    def finish_vertex_editing(self, scene_pos):
        """Finish vertex editing and save changes."""
        if not self.vertex_editing_active:
            return

        success = False

        # Delegate to graphics object if available
        if hasattr(self, "editing_graphics_object") and self.editing_graphics_object:
            success = self.editing_graphics_object.finish_vertex_editing(self.editing_vertex_index, scene_pos)

        if not success:
            self.cancel_vertex_editing()
            return

        # Reset editing state
        self._reset_vertex_editing_state()

    def cancel_vertex_editing(self):
        """Cancel vertex editing without saving changes."""
        if not self.vertex_editing_active:
            return

        # Delegate to graphics object if available
        if hasattr(self, "editing_graphics_object") and self.editing_graphics_object:
            self.editing_graphics_object.cancel_vertex_editing(self.editing_vertex_index)

        # Restore original handle color
        if self.editing_vertex_handle:
            self.editing_vertex_handle.setBrush(QGU.QBrush(QCO.Qt.blue))

        # Reset editing state
        self._reset_vertex_editing_state()

    def _reset_vertex_editing_state(self):
        """Reset vertex editing state."""
        self.vertex_editing_active = False
        self.editing_vertex_index = None
        self.editing_vertex_handle = None
        if hasattr(self, "editing_graphics_object"):
            self.editing_graphics_object = None
        self.ui.graphicsView.setInteractive(True)

    def _get_trade_dot_pixmap(self, is_land: bool) -> QGU.QPixmap:
        """Get the appropriate dot pixmap for trade routes."""
        key = "land_dot" if is_land else "sea_dot"
        pil = self.state.images.get(key)
        pm = self.pil_to_qpixmap(pil)
        pm.setDevicePixelRatio(1.0)
        return pm

    def _get_empire_edge_pixmap(self) -> QGU.QPixmap:
        """Get the empire edge pixmap for border rendering."""
        for el in self.state.elements:
            if el["kind"] == PRS.EmpObjTypes.EMPIRE_EDGE:
                return self.pil_to_qpixmap(el["pil"])
        return QGU.QPixmap()

    # ==== edge/border drawing (temp) ===========================================

    def _begin_edge_drawing(self, x_img: int, y_img: int):
        """Start edge drawing mode by clearing any existing state and adding the first point."""
        # Clear any leftovers and (re)start state
        self._edge_abort(erase=True)
        self.edge_points_img = []
        self.edge_point_items = []
        self.edge_line_items = []
        self.edge_temp_line_item = None
        self.edge_drawing_active = True

        # Set the drawing cursor immediately when edge drawing begins
        self.set_drawing_cursor(True)

        # first point (no segment yet)
        self._edge_append_point(x_img, y_img, make_segment=False)

    def _edge_update_temp_line(self, cursor_scene_pos=None):
        """Create/update the rubber-band line from the last point to the cursor."""
        self._update_temp_line("edge", cursor_scene_pos)

    def _edge_append_point(self, x_img: int, y_img: int, make_segment: bool = True):
        """Append a point, draw its red dot, and optionally the connecting segment."""
        self._append_drawing_point(x_img, y_img, "edge", make_segment)

    def _edge_hit_existing_point(self, x_img: int, y_img: int) -> int | None:
        """Check if (x_img, y_img) is close to any existing point. Return the index or None."""
        result = self._hit_existing_point(x_img, y_img, self.edge_points_img)
        return result if result != -1 else None

    def _edge_prompt_incomplete(self):
        """Handle incomplete border: offer to save, discard, or continue drawing."""
        if not self.edge_points_img:
            self._edge_abort(erase=True)
            return

        resp = self.show_message(UIS.INCOMPLETE_BORDER, UIS.INCOMPLETE_BORDER_MSG, 1, 2, 3)
        if resp == QBTN_YES:
            self._finalize_edge(success=True, close_to_index=0)
        elif resp == QBTN_NO:
            self._edge_abort(erase=True)
        # Cancel -> continue drawing (do nothing)

    def _finalize_edge(self, success: bool, close_to_index: int | None = None):
        """Finalize the edge drawing by saving to model and rendering permanent border."""
        if not success or len(self.edge_points_img) < 2:
            self._edge_abort(erase=True)
            self.empire_border = False
            return

        pts = list(self.edge_points_img)

        # If we know which vertex we clicked to close, draw the closing segment visually
        if close_to_index is not None and self.bg_item is not None:
            x_last, y_last = pts[-1]
            x_close, y_close = pts[close_to_index]
            close_item = self.scene.addLine(x_last, y_last, x_close, y_close, QGU.QPen(QCO.Qt.red, 2))
            close_item.setZValue(80)
            if close_item:
                self.edge_line_items.append(close_item)

            # Rotate so the first vertex becomes the clicked/closed one (canonical order)
            if close_to_index != 0:
                pts = pts[close_to_index:] + pts[:close_to_index]

        # Clean consecutive duplicates (defensive)
        cleaned = []
        for x, y in pts:
            if not cleaned or cleaned[-1] != (x, y):
                cleaned.append((x, y))

        # Save to model with default density=28
        self._save_border_shape(cleaned, density=28)

        # Erase temporary red dots/lines and stop drawing mode
        self._edge_abort(erase=True)

        # Mark border present and create border graphics object
        self.empire_border = True
        if Empire and Empire.border:
            Manager.add_border(Empire.border, self)

    def _save_border_shape(self, points_img_xy: list[tuple[int, int]], density: int = 28):
        """Persist the border polyline to the model as ed.Border with ed.Edge entries."""
        if Empire is None:
            return

        try:
            edges = [ed.Edge(x=int(x), y=int(y), hidden=False) for (x, y) in points_img_xy]
            border_obj = ed.Border(density=int(density), edges=edges)
            Empire.border = border_obj  # single border only
            self.mark_unsaved_changes()  # Mark as unsaved after creating border
        except Exception as e:
            log.error(f"Failed to create ed.Border dataclass instance: {e}")
            # Fallback if dataclasses not available for some reason
            border_obj = type("Border", (), {})()
            border_obj.density = int(density)
            border_obj.edges = [
                type("Edge", (), {"x": int(x), "y": int(y), "hidden": False})() for (x, y) in points_img_xy
            ]
            Empire.border = border_obj

    def _edge_abort(self, erase: bool):
        """Stop drawing; optionally erase temp items; always reset cursor consistently."""
        self._abort_drawing("edge", erase=erase)

    # ==== border rendering (uses the same stamping helpers) ====================

    def delete_empire_border(self, force=False):
        """Delete the empire border with optional confirmation."""
        if not force:
            if (
                self.show_message(UIS.DEL_BORDER, UIS.DEL_BORDER_CONFIRM, 3, 1, 2) != QBTN_YES
            ):  # Question, Yes|No, default No
                return

        # Clear from model
        if Empire:
            Empire.border = None

        # Clear visuals
        self.clear_empire_border_visual()
        self.empire_border = False

    def _handle_empire_edge_drop(self, scene_pos):
        """Handle dropping an empire edge to start border drawing."""
        # If we already have a border, ask first
        if self.empire_border and Empire.border:
            if (
                not self.show_message(UIS.START_NEW_BORDER, UIS.START_NEW_BORDER_MSG, 3, 1, 2) == QBTN_YES
            ):  # Question, Yes|No, default No
                return
            # erase model + visuals
            self.delete_empire_border(force=True)

        xy = self._scene_to_image_xy(scene_pos)
        if xy is None:
            self.show_message(UIS.NO_BG, UIS.NO_BG_MSG, 1)  # Warning, Ok only
            return
        x, y = xy

        if not self.state.check_if_empire():
            # Create empire and update with current background info if available
            self.state.new_empire()
            if self.bg_item and hasattr(self, "_current_image_path"):
                # Update with current background information
                pixmap = self.bg_item.pixmap()
                if self.bg_type == ed.EmpBackgroundTypes.CUSTOM:
                    self.state.current_empire_object.version = 2
                    self.state.current_empire_object.map_info = ed.Map(
                        image=os.path.basename(self._current_image_path),
                        width=pixmap.width(),
                        height=pixmap.height(),
                    )
                    self.state.current_empire_object.show_ireland = False

        # Start edge drawing immediately
        self._begin_edge_drawing(x, y)

    # %% Everything else

    # ---------- ROUTER ----------

    def add_city_icons_to_list(self):
        """Populate the list widget with selectable elements using the new graphics system."""
        self.ui.listWidget.clear()
        self.selectable_elements.clear()

        for el in self.state.elements:
            # Skip disabled elements
            if not el.get("enabled", True):
                continue

            # Create GRO.SelectableElement from the old format
            pixmap = self.pil_to_qpixmap(el["pil"])

            # Determine graphics type based on data type
            if isinstance(el["kind"], ed.CityType):
                graphics_type = GRO.GraphicsObjectType.CITY
            elif el["kind"] == PRS.EmpObjTypes.EMPIRE_EDGE:
                graphics_type = GRO.GraphicsObjectType.BORDER_EDGE
            else:
                # For now, skip unknown types
                continue

            selectable_element = GRO.SelectableElement(
                name=el["name"],
                pixmap=pixmap,
                data_type=el["kind"],
                graphics_type=graphics_type,
                enabled=el.get("enabled", True),
            )

            self.selectable_elements.append(selectable_element)

            # Create list widget item
            item = QWI.QListWidgetItem(el["name"])
            item.setIcon(QGU.QIcon(pixmap))
            item.setSizeHint(QCO.QSize(100, 80))
            # Store reference to our GRO.SelectableElement
            item.setData(QCO.Qt.ItemDataRole.UserRole, len(self.selectable_elements) - 1)
            self.ui.listWidget.addItem(item)

        # Note: Empire edges and trade points are selectable when they're drawn on the scene
        # but they don't need separate template items in the list widget since they're
        # created as part of borders and trade routes respectively

        self.ui.listWidget.setIconSize(QCO.QSize(64, 64))

    # %% No-background message
    def show_no_background_message(self):
        """Show the placeholder text when no background is set."""
        self.no_bg_item = self.scene.addText("No Empire background image selected.")
        self.center_no_background_message()
        self.ui.mouse_position_label.setVisible(False)

    def remove_no_background_message(self):
        """Remove the placeholder text when a background is set."""
        if self.no_bg_item is not None:
            try:
                self.scene.removeItem(self.no_bg_item)
            except Exception as e:
                log.error(f"Failed to remove no-background message item: {e}")
        self.no_bg_item = None  # clear stale reference
        self.ui.mouse_position_label.setVisible(True)

    def center_no_background_message(self):
        if self.no_bg_item is None:
            return
        view = self.ui.graphicsView
        vp = view.viewport()
        br = self.no_bg_item.boundingRect()
        x = (vp.width() - br.width()) / 2
        y = (vp.height() - br.height()) / 2
        self.no_bg_item.setPos(view.mapToScene(int(x), int(y)))

    # %% Other

    def _get_current_map_name(self):
        """Get the current map name based on background type."""
        if self.bg_type == ed.EmpBackgroundTypes.BIG_MAP:
            return "Orbis Terrarum"
        elif self.bg_type == ed.EmpBackgroundTypes.NORTH_MAP:
            return "Occidentalis"
        elif self.bg_type == ed.EmpBackgroundTypes.SOUTH_MAP:
            return "Orientalis"
        else:
            if self.bg_item is not None:
                return ed.EmpBackgroundTypes.CUSTOM
            else:
                return ed.EmpBackgroundTypes.NONE

    def set_background_image(self, pil_img=None, open_dialog=False, skip_validation=False) -> bool:
        """Set the background image.
        Returns:
            True  -> background applied (custom or memory-loaded)
            False -> user cancelled or operation failed (no changes applied)
        """
        try:

            def confirm_elements_fit(pm) -> bool:
                """Ask user to confirm if any elements would fall out of bounds."""
                oob = self._validate_empire_bounds(pm.width(), pm.height(), remove_invalid=False)
                if not oob:
                    return True
                items_text = "\n".join(f"• {item}" for item in oob)
                message = UIS.ELEMENTS_OOB_MSG.format(elements=items_text)
                resp = self.show_message(UIS.ELEMENTS_OOB, message, 3, 1, 2)  # Question, Yes|No, default No
                return resp == QBTN_YES

            pixmap = None
            image_path = None
            error = "Unsupported or empty image"
            while True:
                if open_dialog:  # Path A: user chooses an image from disk
                    if not self._check_before_discarding("Background Image"):
                        return False
                    file_path, _ = QWI.QFileDialog.getOpenFileName(self, "Select Background Image", "", UIS.IMAGE_FILES)
                    if not file_path:
                        return False  # user cancelled

                    temp_pm = QGU.QPixmap(file_path)
                    if temp_pm.isNull():
                        self.show_message(UIS.IMG_LOAD_ERR, UIS.IMG_LOAD_FAIL.format(file_path, error), 2)
                        return False
                    if not skip_validation:
                        if not confirm_elements_fit(temp_pm):
                            return False  # user said "No"

                    pixmap = temp_pm
                    image_path = file_path
                    break

                # Path B: image provided as PIL object
                if pil_img is None:
                    return False  # nothing to do
                temp_pm = self.pil_to_qpixmap(pil_img)
                if temp_pm.isNull():
                    self.show_message(UIS.IMG_LOAD_ERR, UIS.IMG_LOAD_FAIL.format(file_path, error), 2)
                    return False
                if not skip_validation:
                    if not confirm_elements_fit(temp_pm):
                        return False

                pixmap = temp_pm
                break

            # --- Apply background ---
            self.state.selected_empire_image = pixmap
            if open_dialog:
                self._current_image_path = image_path  # track disk path for custom images

            # Reset scene and place background
            self.bg_item = None
            self._clear_scene_state()
            self.no_bg_item = None
            self.bg_item = QWI.QGraphicsPixmapItem(pixmap)
            self.bg_item.setZValue(-1000)  # keep it behind markers
            self.scene.addItem(self.bg_item)
            self.scene.setSceneRect(pixmap.rect())
            self.ui.graphicsView.setEnabled(True)
            self.remove_no_background_message()

            # Background type & menus
            if open_dialog and not hasattr(self, "_bg_type_set_by_dialog"):
                self.bg_type = ed.EmpBackgroundTypes.CUSTOM
                self.default_cities_manager.update_menu_state()
            self.default_cities_manager.populate_menu()

            # Persist map info (only pass a file path if chosen via dialog)
            self._update_empire_map_info(image_path=image_path if open_dialog else pil_img.filename, pixmap=pixmap)
            # Re-render existing empire elements, if any

            if Empire:
                if hasattr(Empire, "cities"):
                    for city in Empire.cities:
                        try:
                            Manager.add_city(city, main_window=self)
                        except Exception as e:
                            log.error(f"Failed to add city {city.name} at ({city.x},{city.y}): {e}")
                        if city.trade_route is not None:
                            try:
                                Manager.add_trade_route(city, self)
                            except Exception as e:
                                log.error(f"Failed to add trade route {e}")
                if self.empire_border and getattr(Empire, "border", None):
                    try:
                        Manager.add_border(Empire.border, self)
                    except Exception as e:
                        log.error(f"Failed to render empire border: {e}")

            return True

        except Exception as e:
            self.show_message(UIS.IMG_LOAD_ERR, UIS.IMG_LOAD_FAIL.format(image_path, error=str(e)), 2)
            log.error(e)
            return False

    def _configure_empire_for_background(self, selected_image, selected_type, pixmap):
        """Configure empire settings based on background type."""
        if selected_type != ed.EmpBackgroundTypes.LEGACY:
            Empire.version = 2  # Upgrade to version 2 and set map info for custom backgrounds
            Empire.map_info = ed.Map(
                image=os.path.basename(selected_image), width=pixmap.width(), height=pixmap.height()
            )
            Empire.show_ireland = False
        else:
            Empire.show_ireland = True  # For legacy backgrounds, keep default settings

    def _setup_new_empire_background(self, selected_image, selected_type):
        """Set up background for new empire, handling scene and pixmap creation."""
        pixmap = QGU.QPixmap(selected_image)
        if pixmap.isNull():
            self.show_message(UIS.INVALID_IMG, UIS.INVALID_IMG_MSG.format(selected_image=selected_image), 1)
            return None

        # Store image info
        self._current_image_path = selected_image
        self.state.selected_empire_image = pixmap

        # Set up scene
        self.scene.clear()
        self._clear_scene_state()
        self.bg_item = QWI.QGraphicsPixmapItem(pixmap)
        self.bg_type = selected_type
        self.bg_item.setZValue(-1000)
        self.scene.addItem(self.bg_item)
        self.scene.setSceneRect(pixmap.rect())
        self.ui.graphicsView.setEnabled(True)
        return pixmap

    def on_new_empire(self):
        """Handle the New Empire action by showing the image selection dialog."""
        # Check if we have unsaved changes
        if not self._check_before_discarding("new"):
            return

        dialog = UIE.ImageSelectionDialog(self)
        if dialog.exec() != QWI.QDialog.Accepted:
            return

        selected_image = dialog.get_selected_image()
        selected_type = dialog.get_selected_image_type()
        if not selected_image:
            return

        # Set up background and validate image
        pixmap = self._setup_new_empire_background(selected_image, selected_type)
        if pixmap is None:
            return

        # Clear current empire and create new one
        self.clear_empire_data()
        self.state.new_empire()
        self._update_empire_reference()

        # Configure empire based on background type
        self._configure_empire_for_background(selected_image, selected_type, pixmap)

        # Update UI state
        self.default_cities_manager.populate_menu()
        self.default_cities_manager.update_menu_state()
        self.current_file_path = None
        self.has_unsaved_changes = False
        self.update_window_title()
        self.update_ui_state()

    def clear_empire_data(self):
        """Clear all current empire data for a new empire."""
        # Clear the empire data
        if self.state.current_empire_object:
            self.state.current_empire_object = None
            self._update_empire_reference()  # Update global reference

        # Clear scene state and graphics
        self._clear_scene_state()

        # Clear the list widget and re-add template icons
        self.ui.listWidget.clear()
        self.add_city_icons_to_list()  # Re-add the template icons

        # Update UI state after clearing empire
        self.update_ui_state()

    def on_empire_properties(self):
        """Handle the Empire Properties action by showing the properties dialog."""
        dialog = UIE.EmpirePropertiesDialog(self)
        dialog.set_border_spacing(Empire.border.density)
        dialog.set_show_ireland(Empire.show_ireland)
        # Load ornaments setting (check if ornaments list is not empty)
        ornaments_enabled = bool(hasattr(Empire, "ornaments") and Empire.ornaments and len(Empire.ornaments) > 0)
        dialog.set_ornaments_enabled(ornaments_enabled)

        if dialog.exec() == QWI.QDialog.Accepted:
            # Get the values from the dialog
            border_spacing = dialog.get_border_spacing()
            show_ireland = dialog.get_show_ireland()
            ornaments_enabled = dialog.get_ornaments_enabled()

            # Ensure empire has a border object for border spacing
            if Empire.border is None:  # Create a new Border object
                Empire.border = ed.Border(density=border_spacing)
            else:  # Update existing border object
                Empire.border.density = border_spacing
            Empire.show_ireland = show_ireland

            if ornaments_enabled:  # If ornaments is empty and we're enabling, add a placeholder
                if not Empire.ornaments:
                    Empire.ornaments = [1]  # Add a default ornament value
            else:  # Clear ornaments if disabled
                Empire.ornaments = []
            # Update UI to reflect changes if needed
            self.update_ui_state()
            if Manager.border_object:
                Manager.border_object.render_border()

    def on_default_empire_map_selected(self):
        if "The_empire" in self.state.images:
            empire_image = self.state.images["The_empire"]
            if isinstance(empire_image, list):
                empire_image = empire_image[0]

            self.set_background_image(empire_image)
            self.bg_type = ed.EmpBackgroundTypes.LEGACY
            self.default_cities_manager.update_menu_state()
        else:
            self.show_message(UIS.MISSING_MAP, UIS.MISSING_MAP_MSG, 1)

    def pil_to_qpixmap(self, pil_img):
        if pil_img.mode != "RGBA":
            pil_img = pil_img.convert("RGBA")
        w, h = pil_img.size
        data = pil_img.tobytes("raw", "RGBA")
        qimg = QGU.QImage(data, w, h, QGU.QImage.Format.Format_RGBA8888)
        return QGU.QPixmap.fromImage(qimg)

    # -------------------------------------------------------
    # New "city" drop handler (generalized), keeps old name too
    # -------------------------------------------------------
    def add_city_to_empire(self, city, create_label=True):
        """
        Unified method to add a city to the empire and scene.
        This is the only method that should be used to add cities.
        """
        if not self.state.check_if_empire():  # Ensure there's an empire
            return
        if city not in Empire.cities:  # Add to empire cities list if not already there
            Empire.cities.append(city)
            self.mark_unsaved_changes()

        Manager.add_city(city, main_window=self)  # Use graphics manager to create visual representation
        if create_label:  # Create name label if requested
            self._create_city_label(city)
        self.default_cities_manager.update_menu_state()  # Update default cities menu state

        return city

    def _handle_city_drop(self, scene_pos):
        """Handle dropping a city using the new graphics system."""
        xy = self._scene_to_image_xy(scene_pos)
        if xy is None:
            self.show_message(UIS.NO_BG, UIS.NO_BG_MSG, 1)  # Warning, Ok only
            return
        x, y = xy

        if self.selected_list_element:  # Get city type from selected graphics object
            ctype = self.selected_list_element.data_type
        else:
            log.debug("Warning: No selected element found for city drop")
            return

        if ctype == ed.CityType.OURS:  # OUR city: single instance with move-confirmation
            has_ours, ours = self.state.has_our_city()
            if has_ours:
                message = UIS.MOVE_OUR_CITY_MSG.format(old_x=ours.x, old_y=ours.y, new_x=x, new_y=y)
                resp = self.show_message(UIS.MOVE_OUR_CITY, message, 3, 1, 2)  # Question, Yes|No, default No
                if resp == QBTN_NO:
                    return
                Manager.remove_city(ours)  # Remove old city and update position
                ours.x, ours.y = x, y
                self.mark_unsaved_changes()
            else:
                ours = ed.City(name="Our City", x=x, y=y, city_type=ed.CityType.OURS, sells=[])  # Create new "Our City"
            self.add_city_to_empire(ours, create_label=True)

        else:
            default_name = ed.CityType(ctype).value  # Other city types: create freely
            city = ed.City(name=default_name, x=x, y=y, city_type=ctype)
            if ctype in (ed.CityType.TRADE, ed.CityType.FUTURE_TRADE):
                city.trade_route = ed.TradeRoute(cost=500, r_type=ed.TradeRouteType.LAND)
            self.add_city_to_empire(city, create_label=True)
            Manager.add_trade_route(city, self)
        # Clear drawing state
        self.set_drawing_cursor(False)
        self.is_dragging = False
        self.deselect_all()
        return

    # -------------------------------------------------------
    # City Name Label Management
    # -------------------------------------------------------

    def _get_city_label_mode(self) -> str:
        n = self.ui.actionViewOption4.isChecked()
        t = self.ui.actionViewOption5.isChecked()
        return "both" if n and t else ("name" if n else ("trade" if t else "off"))

    def _create_city_label(self, city, mode: str | None = None):
        """Create (or update) a single label for this city and lay it out."""
        mode = mode or self._get_city_label_mode()
        key = id(city)
        if key not in self.city_items:
            return

        # --- compute texts once ---
        name_text = city.name or ""

        def _fmt_res(r, omit_amount=False):
            nm = getattr(r.resource_type, "value", r.resource_type)
            nm = str(nm).replace("_", " ").title()
            return f"{nm}[{r.amount}]" if (not omit_amount and r.amount not in (None, 1)) else nm

        sells = ", ".join(_fmt_res(r, omit_amount=(city.city_type == ed.CityType.OURS)) for r in (city.sells or []))
        buys = ", ".join(_fmt_res(r) for r in (city.buys or []))
        trade = ("S: " + sells if sells else "") + (" | " if sells and buys else "") + ("B: " + buys if buys else "")

        # --- get or create the label items (idempotent) ---
        if not hasattr(self, "city_labels"):
            self.city_labels = {}

        item = self.city_labels.get(key)
        if item is None:
            item = QWI.QGraphicsTextItem()
            font = QGU.QFont("Bookman Old Style", pointSize=8)
            item.setFont(font)
            item.setDefaultTextColor(QCO.Qt.GlobalColor.black)

            bg = QWI.QGraphicsRectItem()
            bg.setBrush(QGU.QBrush(QCO.Qt.GlobalColor.white))
            bg.setPen(QGU.QPen(QCO.Qt.GlobalColor.black, 1))
            bg.setZValue(100)

            item.bg_rect = bg
            self.scene.addItem(bg)
            self.scene.addItem(item)
            self.city_labels[key] = item

        # cache strings on the item and layout
        item._name_text = name_text
        item._trade_text = trade
        self._apply_city_label_mode(city, mode)

    def _apply_city_label_mode(self, city, mode: str | None = None):
        """Recompose text (bold name, normal trade) and re-center above icon; avoid overlaps."""
        mode = mode or self._get_city_label_mode()
        key = id(city)
        item = getattr(self, "city_labels", {}).get(key)
        if not item:
            return

        name_text, trade_text = item._name_text, item._trade_text
        fam = "Bookman Old Style"

        # Compose HTML with real paragraphs (Qt-friendly line breaks). Center both lines.
        parts = []
        if mode in ("name", "both") and name_text:
            parts.append(
                f"<p style=\"font-family:'{fam}'; font-size:8pt; font-weight:600; "
                f'color:#000; text-align:center; margin:0;">{esc(name_text)}</p>'
            )
        if mode in ("trade", "both") and trade_text:
            parts.append(
                f"<p style=\"font-family:'{fam}'; font-size:8pt; font-weight:400; "
                f'color:#000; text-align:center; margin:0;">{esc(trade_text)}</p>'
            )
        html = "".join(parts)

        show = (mode != "off") and bool(html)
        item.setVisible(show)
        item.bg_rect.setVisible(show)
        if not show:
            return

        # Lay out naturally (no fixed text width), then size background with padding.
        item.setHtml(html)
        doc = item.document()
        doc.setDocumentMargin(0)

        r = item.boundingRect()
        padding = 2
        item.bg_rect.setRect(r.x() - padding, r.y() - padding, r.width() + 2 * padding, r.height() + 2 * padding)

        # Preferred position (above icon, centered)
        city_item = self.city_items[key]
        city_pos, city_rect = city_item.pos(), city_item.boundingRect()
        x = city_pos.x() + city_rect.width() / 2 - r.width() / 2
        y = city_pos.y() - r.height() + 6

        # Overlap-avoid: bump up, else down
        def overlaps(yv: float) -> bool:
            test = QCO.QRectF(x, yv, r.width(), r.height())
            for ok, other in self.city_labels.items():
                if ok == key or not other.isVisible():
                    continue
                orr = other.boundingRect()
                op = other.pos()
                if test.intersects(QCO.QRectF(op.x(), op.y(), orr.width(), orr.height())):
                    return True
            return False

        sr = self.scene.sceneRect()
        step, margin = 4, 2
        if overlaps(y):
            y_up = y
            while overlaps(y_up) and y_up - step >= sr.top() + margin:
                y_up -= step
            if overlaps(y_up):
                y_dn = y
                while overlaps(y_dn) and y_dn + r.height() + step <= sr.bottom() - margin:
                    y_dn += step
                y = y_dn
            else:
                y = y_up

        # Apply
        item.setPos(x, y)
        item.setZValue(101)
        item.bg_rect.setPos(x, y)

    def _remove_city_label(self, city):
        """Remove the name label for a city."""
        key = id(city)
        if key in self.city_labels:
            text_item = self.city_labels[key]
            try:
                # Remove background rectangle
                self.scene.removeItem(text_item.bg_rect)
                self.scene.removeItem(text_item)
            except RuntimeError:
                pass
            del self.city_labels[key]

    def _remove_all_city_labels(self):
        for key in self.city_labels:
            text_item = self.city_labels[key]
            self.scene.removeItem(text_item.bg_rect)
            self.scene.removeItem(text_item)
            del self.city_labels[key]

    # -------------------------------------------------------
    # View Options Toggle Methods
    # -------------------------------------------------------

    def toggle_cities_visibility(self):
        """Toggle visibility of all city markers using the new graphics system."""
        if Empire is None:
            return
        visible = self.ui.actionViewOption1.isChecked()
        Manager.set_cities_visibility(visible)
        log.debug(f"Cities visibility: {'ON' if visible else 'OFF'}")

    def toggle_trade_routes_visibility(self):
        """Toggle visibility of all trade routes using graphics manager."""
        if Empire is None:
            return
        visible = self.ui.actionViewOption2.isChecked()
        Manager.set_trade_routes_visibility(visible)
        log.debug(f"Trade routes visibility: {'ON' if visible else 'OFF'}")

    def toggle_border_visibility(self):
        """Toggle visibility of empire border."""
        if Empire is None:
            return
        visible = self.ui.actionViewOption3.isChecked()
        Manager.set_border_visibility(visible)

        if hasattr(self, "edge_temp_line_item") and self.edge_temp_line_item:
            try:
                self.edge_temp_line_item.setVisible(visible)
            except RuntimeError:
                pass

        log.debug(f"Empire border visibility: {'ON' if visible else 'OFF'}")

    def update_all_city_labels_from_toggles(self):
        if Empire is None:
            return
        mode = self._get_city_label_mode()
        for city in Empire.cities:
            self._apply_city_label_mode(city, mode)

    def align_trade_points(self, alignment_radius: int) -> int:
        """
        Snap nearby trade points (pixel units) to a shared integer coordinate.
        Returns:
            int: number of points whose coordinates changed.
        """
        if Empire is None:
            return 0
        # Collect a global list of all trade-point objects
        all_points = []
        for city in Empire.cities:
            tr = city.trade_route
            if tr and tr.trade_points is not None:
                all_points.extend(tr.trade_points)

        if not all_points or alignment_radius <= 0:
            return 0

        r2 = alignment_radius * alignment_radius
        moved = 0

        # Representatives (int coords)
        reps: list[tuple[int, int]] = []

        for p in all_points:
            # Ensure integer coords locally (we'll also coerce p if needed)
            px = int(p.x)
            py = int(p.y)

            snapped = False
            for rx, ry in reps:
                dx = px - rx
                dy = py - ry
                if dx * dx + dy * dy <= r2:
                    # Snap to representative if different
                    if p.x != rx or p.y != ry:
                        p.x = rx
                        p.y = ry
                        moved += 1
                    snapped = True
                    break

            if not snapped:
                # New representative; also coerce point to integer coords if needed
                reps.append((px, py))
                if p.x != px or p.y != py:
                    p.x = px
                    p.y = py
                    moved += 1
        return moved

    def refresh_map(self, snap=False):
        """Refresh and re-render all map elements (F5)."""
        log.debug("Refreshing map...")

        if not self.state.check_if_empire():
            log.debug("No empire to refresh")
            return

        # Clear all visual elements except background
        if self.scene and self.bg_item:
            # Remove all items except background

            for item in list(self.scene.items()):
                if item != self.bg_item:
                    self.scene.removeItem(item)

        if self.state.snap_enabled or snap:
            moved = self.align_trade_points(self.state.snap_distance)

        # Clear internal state
        self.city_items.clear()
        self.city_labels.clear()
        self._clear_scene_state()

        # 1. Re-render cities

        for city in Empire.cities:
            Manager.add_city(city, main_window=self)
            # Always create name labels (visibility will be controlled by toggle)
            self._create_city_label(city)

            # Re-render trade routes
            if city.trade_route is not None:
                Manager.add_trade_route(city, self)

        # 2. Re-render empire border if enabled
        if Empire.border:
            self.empire_border = True
            Manager.add_border(Empire.border, self)

        # 3. Update visibility states based on current toggle settings
        self.update_all_city_labels_from_toggles()
        self.toggle_cities_visibility()
        self.toggle_trade_routes_visibility()
        self.toggle_border_visibility()

        # 4. Repopulate Default Cities menu
        self.default_cities_manager.populate_menu()
        if moved > 0:
            self.has_unsaved_changes = True
            self.show_message(UIS.TR_ALIGNED, UIS.TR_ALIGNED_MSG.format(moved=moved), 0)
        log.debug("Map refresh completed")


if __name__ == "__main__":
    app = QWI.QApplication.instance() or QWI.QApplication([])
    window = MainWindow()
    # One global filter to observe ALL widgets
    app.installEventFilter(window)
    if not window.init_failed:
        window.show()
        sys.exit(app.exec())
    sys.exit(0)
