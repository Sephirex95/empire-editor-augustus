import sys
import os
import json
import shutil
from PySide6.QtWidgets import (
    QMainWindow, QFileDialog, QGraphicsScene, QGraphicsView,
    QGraphicsPixmapItem, QApplication, QListWidgetItem, QMessageBox, QDialog, QGraphicsLineItem,
    QGraphicsItemGroup,  QGraphicsItem,  QMenu, QGraphicsTextItem, QGraphicsRectItem

)
from PySide6.QtGui import (QIcon,QFont, QPixmap, QImage, QCursor, QPainter,
    QPen, QBrush, QPainterPath, QAction, QColor, QDesktopServices)
from PySide6.QtCore import QSize, QSettings, Qt, QEvent, QObject, QRectF, QSizeF, QTimer, QUrl
from ui_empire_editor import Ui_MainWindow, ImageSelectionDialog, EmpirePropertiesDialog, show_about_dialog, SettingsDialog
from PIL import Image
import empire_data as ed
import edit_city_logic as emp_dlg
from enum import Enum, auto
import copy
from html import escape as esc
from program_state import ProgramState
# ---------------------------------------------
# separated enums
# ---------------------------------------------
class EmpObjTypes(Enum):
    EMPIRE_EDGE = auto()
    LAND_DOT = auto()
    SEA_DOT = auto()
    TRADE_FLAG = auto()
    ROMAN_FLAG = auto()
    DISTANT_FLAG = auto()
    OUR_FLAG = auto()
    OUR_LEGION = auto()
    NATIVES = auto()
    DISTANT_BATTLE = auto()
    
# ---------------------------------------------

    
class PaddedHitPixmapItem(QGraphicsPixmapItem):
    """
    QGraphicsPixmapItem with an enlarged hit area (for hover/selection).
    'hitpad' is padding in pixels added on all sides around the icon.
    """
    def __init__(self, pixmap, hitpad=6, parent=None):
        super().__init__(pixmap, parent)
        self._hitpad = float(hitpad)

    def shape(self) -> QPainterPath:
        # Local rect in item coords must include the current offset
        # because we call setOffset(-w/2, -h/2) when centering.
        pm = self.pixmap()
        r = QRectF(self.offset(), QSizeF(pm.width(), pm.height()))
        r.adjust(-self._hitpad, -self._hitpad, self._hitpad, self._hitpad)

        path = QPainterPath()
        path.addRect(r)
        return path

        
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.program_editor_version = ed.get_editor_version()
        # Set window icon
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "editor.ico")
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
            self.setWindowIcon(icon)
            # Also set application icon (for taskbar grouping)
            QApplication.instance().setWindowIcon(icon)

        self.no_bg_item = None
        self.bg_item = None  # the background QGraphicsPixmapItem
        self.bg_type = ed.EmpBackgroundTypes.NONE  # type of background currently set
        self.cities_data = {}  # Store loaded cities data from JSON
        self._current_image_path = None  # Track current background image file path
        # Edge drawing state
        self.edge_drawing_active = False           # are we in the border drawing mode?
        self.edge_points_img = []                  # [(x_img, y_img), ...]
        self.edge_point_items = []                 # [QGraphicsEllipseItem,...] small red dots
        self.edge_line_items = []                  # [QGraphicsLineItem,...] finalized segments
        self.edge_temp_line_item = None            # QGraphicsLineItem rubber-band
        self.edge_hit_epsilon = 10                # pixels in image coords to detect closing click
        self.border_edge_hit_items = []   # selectable hit proxies for each segment
        self.selected_edge_index = None   # index i for edge i -> i+1
        self.return_to_dialog = False
        # permanent empire border overlay (icon-based)
        self.empire_border = False
        self.border_visual_group = None          # QGraphicsItemGroup for the icon overlay
        self.border_icon_items = []              # QGraphicsPixmapItem[] belonging to the group

        # selection overlay (dotted stroke + square handles)
        self.border_sel_line_items = []      # QGraphicsLineItem[]
        self.border_sel_handle_items = []    # QGraphicsRectItem[]
        self.border_selected = False
        self.moving_city = None  # when set, a drop moves this city

        self.ui.mouse_position_label.setVisible(False)  # hidden until a map is set
        self.city_items = {}  # maps City -> QGraphicsPixmapItem
        self.city_labels = {}  # maps City -> QGraphicsTextItem for name labels

        # trade-route drawing state
        self.trade_drawing_active = False
        self.trade_is_land = True
        self.trade_drawing_points = []          # temp points during drawing
        self.trade_drawing_point_items = []     # temp visual dots during drawing
        self.trade_drawing_line_items = []      # temp visual lines during drawing
        self.trade_temp_line_item = None        # rubber band line
        self.trade_route_city = None            # city being edited

        # Trade route selection state (similar to border selection)
        self.trade_route_selected = False
        self.selected_trade_route_city = None
        self.trade_route_sel_line_items = []      # QGraphicsLineItem[] for dotted lines
        self.trade_route_sel_handle_items = []    # QGraphicsRectItem[] for white squares
        self.trade_route_hit_items = []           # Invisible hit areas for trade route segments
        # Permanent rendered trade routes (keyed by city index)
        self._trade_route_groups = {}  # {city_index: QGraphicsItemGroup}
        
        # Vertex editing state - unified for both trade routes and empire borders
        self.vertex_editing_active = False      # True when dragging a vertex
        self.editing_vertex_type = None         # "TRADE_ROUTE" or "EMPIRE_BORDER"
        self.editing_vertex_index = None        # Index of the vertex being edited
        self.editing_vertex_city = None         # City object (for trade routes only)
        self.editing_vertex_handle = None       # The handle item being dragged
        self.vertex_handle_items = []           # List of active vertex handles
        self._trade_dot_reps = []               # list[(ix, iy)] used to dedupe dots across all routes

        # Data/state
        self.state = ProgramState()
        self.init_failed = False
        if not self.state.init():
            self.init_failed = True
            return
        
        # File state tracking for title bar
        self.current_file_path = None  # Path to currently open file
        self.has_unsaved_changes = False  # Track if there are unsaved changes

        # Initialize cursor pixmaps once at startup
        self._init_cursor_pixmaps()

        # Scene / view
        # Set scene rect with a small margin to ensure proper scrollbar behavior        
        self.scene = QGraphicsScene(self)
        self.ui.graphicsView.setScene(self.scene)

        self.ui.graphicsView.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.ui.graphicsView.setViewportMargins(10,10,10,10)

        self.ui.graphicsView.viewport().setMouseTracking(True)
        
        self.ui.graphicsView.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        self.show_no_background_message()               # show placeholder on startup

        # UI wiring
        self.add_city_icons_to_list()
        self.ui.actionSelect_background_Image.triggered.connect(lambda: self.set_background_image(None, True))
        self.ui.actionEmpireProperties.triggered.connect(self.on_empire_properties)
        self.ui.actionNew.triggered.connect(self.on_new_empire)
        # Connect XML file operations
        self.ui.actionOpen.triggered.connect(self.open_empire_xml)
        self.ui.actionSave.triggered.connect(self.save_empire_xml)
        
        # Connect view options
        self.ui.actionViewOption1.toggled.connect(self.toggle_cities_visibility)
        self.ui.actionViewOption2.triggered.connect(self.toggle_trade_routes_visibility)
        self.ui.actionViewOption3.toggled.connect(self.toggle_border_visibility)
        self.ui.actionViewOption4.toggled.connect(self.update_all_city_labels_from_toggles)
        self.ui.actionViewOption5.toggled.connect(self.update_all_city_labels_from_toggles)
        self.ui.actionRefreshMap.triggered.connect(self.refresh_map)
        
        self.ui.menuSettings.triggered.connect(self._open_settings)
        # Connect help menu
        self.ui.actionAbout.triggered.connect(lambda: show_about_dialog(self))
        
        self.ui.listWidget.itemClicked.connect(self.on_item_clicked)
            # Populate Default Cities menu
        self.populate_default_cities_menu()
        # Update UI state
        self.update_ui_state()
        
        # Update Default Cities menu state based on initial background type
        self._update_default_cities_menu_state()

        # Drag handling
        self.selected_item = None
        self.selected_kind = None        # can be EmpCityTypes or EmpObjTypes
        self.is_dragging = False
        self._init_context_menus()
        self.ui.actionGitHub_Augustus.triggered.connect(self._open_github_augustus)
        self.ui.actionGitHub_Editor.triggered.connect(self._open_github_editor)
        self.ui.actionGitHub_Custom.triggered.connect(self._open_github_custom)
        # Set initial window title
        self.update_window_title()
        
# %% Private helpers for actions
    def _open_github_augustus(self):
        url = "https://github.com/Keriew/augustus/tree/master?tab=readme-ov-file"  # Replace with actual Augustus GitHub URL
        QDesktopServices.openUrl(QUrl(url))

    def _open_github_editor(self):
        url = "https://github.com/Sephirex95/empire-editor-augustus"  
        QDesktopServices.openUrl(QUrl(url))

    def _open_github_custom(self):
        url = "https://github.com/Keriew/augustus/discussions/734"  
        QDesktopServices.openUrl(QUrl(url))
    def _get_city_index(self, city) -> int | None:
        """Get the index of a city in the current empire's cities list."""
        empire = self.state.current_empire_object
        if not empire or not hasattr(empire, 'cities'):
            return None
        try:
            return empire.cities.index(city)
        except ValueError:
            return None
    def _open_settings(self):
        dlg = SettingsDialog(self, settings=self.state.settings)
        if dlg.exec():
            self.state.apply_settings_from_store()
            # react to changes if needed (e.g., reload images if c3_main_folder changed)

# %% setup-related functions
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.center_no_background_message()  # now harmless if item was deleted
        
    def _init_context_menus(self):
        city_common_menu = [
            ("Move City", lambda it: self.move_city(it.data(1))),
            ("Delete City", lambda it: self.remove_city(it.data(1))),
            ("Properties", lambda it: self.edit_city(it.data(1))),
        ]

        self.context_menu_options = {
            ed.CityType.OURS: city_common_menu,
            ed.CityType.DISTANT: city_common_menu,
            ed.CityType.TRADE: city_common_menu,
            ed.CityType.ROMAN: city_common_menu,  # Add Roman cities to context menu
            ed.CityType.FUTURE_TRADE: city_common_menu,
            EmpObjTypes.EMPIRE_EDGE: [
                ("Toggle Edge Hidden", lambda it: self.toggle_edge_hidden_from_item(it)),
                ("Delete Border", self.delete_empire_border),
            ],
            
            # Add trade route context menu
            "TRADE_ROUTE": [
                ("Delete Trade Route Path", lambda it: self.delete_trade_route_from_item(it)),
                ("Edit City", lambda it: self.edit_city_from_trade_route_item(it)),
            ],
        }
    def _init_cursor_pixmaps(self):
        """Initialize cursor pixmaps once at startup for drawing modes."""
        # Edge drawing cursor - use empire edge icon
        edge_pm = self._get_empire_edge_pixmap()
        if edge_pm.isNull():
            # Fallback: create a simple red square
            edge_pm = QPixmap(8, 8)
            edge_pm.fill(Qt.red)
        self.edge_cursor_pixmap = edge_pm
        
        # Trade drawing cursors - use trade dot icons
        land_pm = self._get_trade_dot_pixmap(True)
        if land_pm.isNull():
            # Fallback: create a simple orange dot
            land_pm = QPixmap(8, 8)
            land_pm.fill(QColor(255, 140, 0))
        self.land_cursor_pixmap = land_pm
        
        sea_pm = self._get_trade_dot_pixmap(False)
        if sea_pm.isNull():
            # Fallback: create a simple cyan dot
            sea_pm = QPixmap(8, 8)
            sea_pm.fill(Qt.cyan)
        self.sea_cursor_pixmap = sea_pm
    def _check_before_discarding(self, context="load"):
        """Check for unsaved changes before discarding current work.
        
        Args:
            context: The context for the dialog. Options:
                - "load": Loading a new empire
                - "new": Creating a new empire
                - "close": Closing the application
                - "background": Changing background image
        """
        if not (self.state.check_if_empire() and self.state.has_any_data()):
            return True
        if not self.has_unsaved_changes:
            return True    
        context_info = {
            "load": ("Load Empire", "You have unsaved work in the current empire.\nYou will lose your progress, continue?"),
            "new": ("New Empire", "You have unsaved work in the current empire.\nYou will lose your progress, continue?"),
            "close": ("Close Application", "You have unsaved work in the current empire.\nYou will lose your progress if you close now, continue?"),
            "background": ("Change Background", "You have unsaved work in the current empire.\nChanging background may affect your work, continue?")
        }
        
        title, message = context_info.get(context, context_info["load"])
        
        resp = QMessageBox.question(
            self, title, message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return resp == QMessageBox.StandardButton.Yes
    
    def _show_elements_wont_fit_dialog(self, out_of_bounds_items):
        """Show dialog warning about elements that won't fit in the selected background.

        """
        if not out_of_bounds_items:
            return True
            
        items_text = "\n".join(f"• {item}" for item in out_of_bounds_items)
        message = (
            "Some elements do not fit in the selected background:\n\n"
            f"{items_text}\n\n"
            "These elements will be removed or hidden. Are you sure you want to continue?"
        )
        
        resp = QMessageBox.question(
            self, "Elements Won't Fit", message,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        return resp == QMessageBox.StandardButton.Yes

    def closeEvent(self, event):
        """Handle window close event to prevent unsaved data loss."""

        if self._check_before_discarding("close"):
            event.accept()
        else:
            event.ignore()
# %% Main user-facing functions
    def open_empire_xml(self):
        """Open and load empire from XML file."""
        # Check if we have unsaved changes
        if not self._check_before_discarding("load"):
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Empire XML", "", "XML Files (*.xml);;All Files (*)"
        )
        if not file_path:
            return  # User cancelled
        
        try:
            # Read the XML file
            with open(file_path, 'r', encoding='utf-8') as f:
                xml_content = f.read()
            self.clear_empire_data()
            #self.clear
            # Load empire from XML
            empire = ed.Empire.from_xml_string(xml_content)
            self.state.current_empire_object = empire
            
            # Handle map loading and validation
            xml_dir = os.path.dirname(file_path)
            success = self._load_and_validate_empire_map(empire, xml_dir)
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
            
            QMessageBox.information(
                self, "Success", f"Empire loaded from {file_path}",
                QMessageBox.StandardButton.Ok
            )
            
        except FileNotFoundError:
            QMessageBox.critical(
                self, "File Error", f"File not found: {file_path}",
                QMessageBox.StandardButton.Ok
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Load Error", f"Failed to load empire:\n{str(e)}",
                QMessageBox.StandardButton.Ok
            )
                
    def save_empire_xml(self):
        """Save current empire to XML file, optionally into Augustus user folders if configured."""
        import re
    
        # Warn about 'Our City' but let the user decide
        our_city_exists, _ = self.state.has_our_city()
        if not our_city_exists:
            reply = QMessageBox.question(
                self,
                "Our City",
                "'Our City' is not set; the empire may function incorrectly.\n\nAre you sure you want to save?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
    
        if not self.state.check_if_empire():
            QMessageBox.warning(
                self, "No Empire", "No empire to save. Create an empire first.",
                QMessageBox.StandardButton.Ok
            )
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
            reply = QMessageBox.question(
                self,
                "Save to Augustus directory",
                "Augustus user directory is set.\n\n"
                "Would you like to save to the Augustus user directories?\n"
                "• XML → editor/empires\n"
                "• Image → community/image",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes
            )
            if reply == QMessageBox.StandardButton.Yes:
                use_augustus_dirs = True
    
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
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Empire XML",
            suggested_path,
            "XML Files (*.xml);;All Files (*)"
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
            empire = self.state.current_empire_object
            img_dir_override = aug_img_dir if use_augustus_dirs else ""
            self._prepare_empire_map_info_for_save(empire, file_path, img_dir_override)
    
            # Write XML
            empire.write_xml(file_path)
    
            # Update state/UI
            self.current_file_path = file_path
            self.has_unsaved_changes = False
            self.update_window_title()
    
            QMessageBox.information(
                self, "Success", f"Empire saved to {file_path}",
                QMessageBox.StandardButton.Ok
            )
    
        except Exception as e:
            QMessageBox.critical(
                self, "Save Error", f"Failed to save empire:\n{str(e)}",
                QMessageBox.StandardButton.Ok
            )

            
    def remove_city(self, city):
        """Remove a city from the empire and scene."""
        # Check if this city should be unticked in the default cities menu
        self._untick_default_city_if_removed(city)
        
        empire = self.state.current_empire_object
        if empire and city in empire.cities:
            city_index = self._get_city_index(city)
            if city_index is not None:
                self.clear_trade_route_visuals(city_index)
            empire.cities.remove(city)
            self.mark_unsaved_changes()  # Mark as unsaved after removing city
        self._remove_city_marker(city)
        if self.selected_item and self.selected_item.data(Qt.ItemDataRole.UserRole) == ed.CityType.OURS:
            self.deselect_item() 
            
    def move_city(self, city_obj):
        """Enter drag mode to move an existing city."""
        self.moving_city = city_obj
        pm = self._pixmap_for_city(city_obj.city_type)
    
        # Cache the pixmap for cursor
        self.drag_pixmap = pm
    
        self.is_dragging = True
        self.ui.graphicsView.setInteractive(False)
        self.ui.graphicsView.setDragMode(QGraphicsView.DragMode.NoDrag)
        self._apply_interactivity_to_all(False)
    
        # ensure cursor persists after the context menu closes
        QTimer.singleShot(0, lambda: self.set_drawing_cursor(True, pm))     
        
    def edit_city(self, city_obj):

        snapshot = copy.deepcopy(city_obj)

        dlg = emp_dlg.CityPropertiesDialog(city_obj, self)
        result = None
        try:
            result = dlg.exec()
        finally:
            dlg.deleteLater()  # deleted when control returns to the main event loop
        if result != QDialog.Accepted:
            return  # cancel -> no changes
        if dlg.requested_route_draw:
            #self._apply_drawing_cursor(True)
            #self.is_dragging = False #cancel dragging
            if city_obj.trade_route and len(city_obj.trade_route.trade_points) > 0:
                result = QMessageBox.warning(
                    self, "Trade Route already exists",
                    "There is already a trade route plotted for this city. Would you like to remove it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No
                )
                if result == QMessageBox.StandardButton.No:
                    QTimer.singleShot(100, lambda: self.edit_city(city_obj))
                    return
                else:
                    # Clear both model and visuals for this specific city
                    city_index = self._get_city_index(city_obj)
                    if city_index is not None:
                        self.clear_trade_route_visuals(city_index)
                    city_obj.trade_route.trade_points = []
            self.start_trade_route(city_obj)
            self.return_to_dialog = True
            return
            
        # Check if city type changed from trade to non-trade
        old_type = snapshot.city_type
        new_type = city_obj.city_type
        
        # If city type changed from trade to non-trade, remove trade route
        if (old_type == ed.CityType.TRADE and new_type != ed.CityType.TRADE):
            # Clear trade route for non-trade cities
            city_index = self._get_city_index(city_obj)
            if self.delete_trade_route_from_item(None,city=city_obj):
                if city_index is not None:
                    self.clear_trade_route_visuals(city_index)
                if city_obj.trade_route:
                    city_obj.trade_route.trade_points = []
                    city_obj.trade_route = None 

        
        # validations
        if city_obj.city_type == ed.CityType.OURS: 
            has_ours, ours = self.state.has_our_city()
            if has_ours and ours is not city_obj:
                QMessageBox.warning(
                    self, "Duplicate 'Our City'",
                    "There is already an 'Our City'. Remove it first.", QMessageBox.StandardButton.Ok
                )
                # revert and reopen
                city_obj.__dict__.clear()
                city_obj.__dict__.update(copy.deepcopy(snapshot.__dict__))
                return  # Exit early after revert

        # Check if trade route type changed and re-render if needed
        old_route_type = snapshot.trade_route.r_type if snapshot.trade_route else None
        new_route_type = city_obj.trade_route.r_type if city_obj.trade_route else None
        
        if old_route_type != new_route_type and city_obj.trade_route and city_obj.trade_route.trade_points:
            # Re-render trade route with new type colors
            self.render_trade_route(city_obj)

        # valid -> update visuals
        if not self.trade_drawing_active:
            key = id(city_obj)
            if key in self.city_items:
                it = self.city_items[key]
                it.setPixmap(self._pixmap_for_city(city_obj))
                it.setData(Qt.ItemDataRole.UserRole, city_obj.city_type)
        self.refresh_map()

# %% ui and drawing
    def update_ui_state(self):
        """Update UI elements based on current empire state."""
        has_empire = self.state and self.state.current_empire_object is not None
        
        # Enable/disable Empire Properties action based on whether we have an empire
        if hasattr(self.ui, 'actionEmpireProperties'):
            self.ui.menuEmpireProperties.setEnabled(has_empire)

    def _validate_empire_elements_fit_background(self, new_bg_pixmap):
        """Check if current empire elements fit within the new background dimensions.
        """
        out_of_bounds = []
        
        if not new_bg_pixmap or new_bg_pixmap.isNull():
            return out_of_bounds
            
        bg_width = new_bg_pixmap.width()
        bg_height = new_bg_pixmap.height()
        empire = self.state.current_empire_object
        
        if not empire:
            return out_of_bounds
            
        # Check cities
        if hasattr(empire, 'cities'):
            for city in empire.cities:
                if hasattr(city, 'x') and hasattr(city, 'y'):
                    if not (0 <= city.x < bg_width and 0 <= city.y < bg_height):
                        out_of_bounds.append(f"City '{city.name}' at ({city.x}, {city.y})")
        
        # Check border edges
        if hasattr(empire, 'border') and empire.border and hasattr(empire.border, 'edges'):
            for i, edge in enumerate(empire.border.edges):
                if hasattr(edge, 'x') and hasattr(edge, 'y'):
                    if not (0 <= edge.x < bg_width and 0 <= edge.y < bg_height):
                        out_of_bounds.append(f"Border edge {i+1} at ({edge.x}, {edge.y})")
        
        # Check trade route points
        if hasattr(empire, 'cities'):
            for city in empire.cities:
                if (hasattr(city, 'trade_route') and city.trade_route and 
                    hasattr(city.trade_route, 'trade_points') and city.trade_route.trade_points):
                    for i, point in enumerate(city.trade_route.trade_points):
                        if hasattr(point, 'x') and hasattr(point, 'y'):
                            if not (0 <= point.x < bg_width and 0 <= point.y < bg_height):
                                out_of_bounds.append(f"Trade route point {i+1} for '{city.name}' at ({point.x}, {point.y})")
        
        return out_of_bounds

    def _update_empire_map_info(self, image_path=None, pixmap=None):
        """Update the current empire's map information with background details."""
        empire = self.state.current_empire_object
        if not empire:
            return
            
        # Ensure we have a map_info object (upgrade to version 2 if needed)
        if empire.version == 1 or empire.map_info is None:
            empire.version = 2
            empire.map_info = ed.Map()
        
        # Update map information
        if image_path:
            empire.map_info.image = image_path
        if pixmap and not pixmap.isNull():
            empire.map_info.width = pixmap.width()
            empire.map_info.height = pixmap.height()
            # Reset offsets for new background
            empire.map_info.x_offset = 0
            empire.map_info.y_offset = 0
            empire.map_info.coordinates_x_offset = 0
            empire.map_info.coordinates_y_offset = 0


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
    
        # For custom backgrounds, set up map_info for version 2+
        empire.version = 2
    
        pixmap = self.bg_item.pixmap()
        if pixmap.isNull():
            empire.map_info = None
            return
    
        # Where the XML will live
        xml_dir = os.path.dirname(file_path)

        images_dir = img_path if img_path else os.path.join(xml_dir, 'image')
    
        # Create images directory if it doesn't exist
        if not os.path.exists(images_dir):
            os.makedirs(images_dir, exist_ok=True)
    
        # Determine the filename of the source image we're currently using
        if hasattr(self, '_current_image_path') and self._current_image_path:
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
                print(f"Copied background image to: {target_path}")
            except Exception as e:
                print(f"Warning: Could not copy image file: {e}")
    
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
    
        print(f"Updated empire map_info: {image_filename} ({pixmap.width()}x{pixmap.height()})")

    def _render_loaded_empire(self):
        """Render the loaded empire data onto the scene."""
        empire = self.state.current_empire_object
        if not empire:
            return
        
        # Clear existing city markers and visual state
        try:
            self.city_items.clear()
        except Exception as e:
            print(f"{e}")
        try:
            self._clear_scene_state()
        except Exception as e:
            print(f"{e}")
        
        # If scene has items, clear and reset (but keep background)
        if self.scene and self.bg_item:
            # Remove all items except background
            self._trade_dot_reps = []
            for item in list(self.scene.items()):
                if item != self.bg_item:
                    self.scene.removeItem(item)
        elif self.bg_item == None:
            if empire.version > 1:
                print("Loading background image from empire map info")
            else:
                print("loading default empire map")
                self.on_default_empire_map_selected()
        
        # Place cities on scene
        if hasattr(empire, 'cities'):
            for city in empire.cities:
                self._place_city_on_scene(city)
                if city.trade_route is not None:
                    self.render_trade_route(city)
        
        # Render empire border if it exists
        if hasattr(empire, 'border') and empire.border:
            self.empire_border = True
            self.render_empire_border()
        
        # Repopulate Default Cities menu after loading empire
        self.populate_default_cities_menu()
        
        # Update Default Cities menu state based on current background
        self._update_default_cities_menu_state()

    def _load_and_validate_empire_map(self, empire, xml_dir):
        """Load and validate empire map, handle version compatibility and element bounds checking."""
        try:
            # Handle different empire versions
            if empire.version == 1 or empire.map_info is None:
                # Version 1 or no map specified - use default/legacy background
                if empire.version == 1:
                    QMessageBox.warning(
                        self, "Legacy Empire", 
                        "This is a version 1 empire file. Loading default empire background.",
                        QMessageBox.StandardButton.Ok
                    )
                else:
                    QMessageBox.warning(
                        self, "No Map Specified", 
                        "Empire file doesn't specify a map. Loading default empire background.",
                        QMessageBox.StandardButton.Ok
                    )
                
                # Load default empire map
                self.on_default_empire_map_selected()
                self.bg_type = ed.EmpBackgroundTypes.LEGACY
                self._update_default_cities_menu_state()
                return True
            
            # Version > 1 with map_info specified
            map_info = empire.map_info
            image_path = map_info.image
            
            if not image_path:
                QMessageBox.warning(
                    self, "No Image Specified", 
                    "Empire map doesn't specify an image file. Loading default empire background.",
                    QMessageBox.StandardButton.Ok
                )
                self.on_default_empire_map_selected()
                self.bg_type = ed.EmpBackgroundTypes.LEGACY
                self._update_default_cities_menu_state()
                return True
            
            # Try to find the image file
            found_image_path = self._find_map_image(image_path, xml_dir)
            if not found_image_path:
                # Ask user to locate the file
                QMessageBox.information(
                    self, "Map Image Not Found",
                    f"Could not find map image: {image_path}\n"
                    f"Please locate the correct image file.",
                    QMessageBox.StandardButton.Ok
                )
                
                found_image_path, _ = QFileDialog.getOpenFileName(
                    self, f"Locate Map Image: {os.path.basename(image_path)}", 
                    xml_dir, "Images (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"
                )
                
                if not found_image_path:
                    QMessageBox.warning(
                        self, "No Image Selected", 
                        "No image selected. Loading default empire background.",
                        QMessageBox.StandardButton.Ok
                    )
                    self.on_default_empire_map_selected()
                    self.bg_type = ed.EmpBackgroundTypes.LEGACY
                    self._update_default_cities_menu_state()
                    return True
            
            # Load and validate the image
            try:
                pil_image = Image.open(found_image_path)
                image_width, image_height = pil_image.size

                
                # Update map_info with actual image dimensions if they differ
                if map_info.width != image_width or map_info.height != image_height:
                    print(f"Updating map dimensions from {map_info.width}x{map_info.height} to {image_width}x{image_height}")
                    map_info.width = image_width
                    map_info.height = image_height
                
                # Validate empire elements fit within image bounds
                removed_elements = self._validate_empire_bounds(empire, image_width, image_height)
                if removed_elements:
                    QMessageBox.warning(
                        self, "Elements Outside Map Bounds",
                        f"Removed {removed_elements} elements that were outside the map boundaries.\n"
                        f"Map size: {image_width}x{image_height}",
                        QMessageBox.StandardButton.Ok
                    )
                
                # Set the background image
                self._current_image_path = found_image_path  # Track the loaded image path
                self.set_background_image(pil_image)
                # Determine if this is a default map or custom map
                self.bg_type = self._get_background_type_from_image_path(found_image_path)
                self._update_default_cities_menu_state()

                
                return True
                
            except Exception as e:
                QMessageBox.critical(
                    self, "Image Load Error",
                    f"Failed to load image {found_image_path}:\n{str(e)}\n"
                    f"Loading default empire background instead.",
                    QMessageBox.StandardButton.Ok
                )
                self.on_default_empire_map_selected()
                self.bg_type = ed.EmpBackgroundTypes.LEGACY
                self._update_default_cities_menu_state()
                return True
                
        except Exception as e:
            QMessageBox.critical(
                self, "Map Loading Error",
                f"Error loading empire map: {str(e)}\n"
                f"Loading default empire background.",
                QMessageBox.StandardButton.Ok
            )
            self.on_default_empire_map_selected()
            self.bg_type = ed.EmpBackgroundTypes.LEGACY
            self._update_default_cities_menu_state()
            return True
    
    def _find_map_image(self, image_path, xml_dir):
        """Try to find the map image in various locations relative to the XML file."""
        filename = os.path.basename(image_path)
        if os.path.isabs(image_path) and os.path.exists(image_path):
            return image_path
        
        # Try relative to XML directory
        rel_path = os.path.join(xml_dir, image_path)
        if os.path.exists(rel_path):
            return rel_path
        
        if getattr(sys, 'frozen', False):
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
            "Orientalis_Empire_Map.png": ed.EmpBackgroundTypes.SOUTH_MAP
        }
        
        # Check filename first
        if filename in default_map_types:
            return default_map_types[filename]
            
        # Check if the path contains the characteristic folder structure
        normalized_path = image_path.replace('\\', '/')
        for default_filename, bg_type in default_map_types.items():
            if f"augustus_assets/Areldir_maps/{default_filename}" in normalized_path:
                return bg_type
        
        return ed.EmpBackgroundTypes.CUSTOM
    
    def _validate_empire_bounds(self, empire, map_width, map_height):
        """Remove empire elements that are outside map bounds. Returns count of removed elements."""
        removed_count = 0
        
        # Check cities
        if hasattr(empire, 'cities'):
            cities_to_remove = []
            for city in empire.cities:
                if hasattr(city, 'x') and hasattr(city, 'y'):
                    if city.x < 0 or city.x >= map_width or city.y < 0 or city.y >= map_height:
                        cities_to_remove.append(city)
                        print(f"Removing city '{city.name}' at ({city.x}, {city.y}) - outside map bounds")
            
            for city in cities_to_remove:
                empire.cities.remove(city)
                removed_count += 1
        
        # Check border points
        if hasattr(empire, 'border') and empire.border and hasattr(empire.border, 'edge_points'):
            points_to_remove = []
            for point in empire.border.edge_points:
                if hasattr(point, 'x') and hasattr(point, 'y'):
                    if point.x < 0 or point.x >= map_width or point.y < 0 or point.y >= map_height:
                        points_to_remove.append(point)
                        print(f"Removing border point at ({point.x}, {point.y}) - outside map bounds")
            
            for point in points_to_remove:
                empire.border.edge_points.remove(point)
                removed_count += 1
        
        # Check battle points in invasion paths
        if hasattr(empire, 'invasion_paths'):
            for invasion_path in empire.invasion_paths:
                if hasattr(invasion_path, 'battles'):
                    battles_to_remove = []
                    for battle in invasion_path.battles:
                        if hasattr(battle, 'x') and hasattr(battle, 'y'):
                            if battle.x < 0 or battle.x >= map_width or battle.y < 0 or battle.y >= map_height:
                                battles_to_remove.append(battle)
                                print(f"Removing battle at ({battle.x}, {battle.y}) - outside map bounds")
                    
                    for battle in battles_to_remove:
                        invasion_path.battles.remove(battle)
                        removed_count += 1
        
        # Check distant battle paths
        if hasattr(empire, 'distant_battle_paths'):
            for path in empire.distant_battle_paths:
                if hasattr(path, 'battles'):
                    battles_to_remove = []
                    for battle in path.battles:
                        if hasattr(battle, 'x') and hasattr(battle, 'y'):
                            if battle.x < 0 or battle.x >= map_width or battle.y < 0 or battle.y >= map_height:
                                battles_to_remove.append(battle)
                                print(f"Removing distant battle at ({battle.x}, {battle.y}) - outside map bounds")
                    
                    for battle in battles_to_remove:
                        path.battles.remove(battle)
                        removed_count += 1
        
        return removed_count
                
    def _place_city_on_scene(self, city):
        """Place a city from loaded data onto the scene."""
        if not hasattr(city, 'x') or not hasattr(city, 'y'):
            return
        
        # Convert center coordinates to top-left for scene placement
        pixmap = self._pixmap_for_city(city.city_type)
        if not pixmap.isNull():
            self._place_city_marker(city, city.x, city.y)

    def delete_trade_route_from_item(self, item, city=None):
        """Delete trade route path from context menu selection."""
        if city is None:
            city_index = item.data(Qt.ItemDataRole.UserRole + 1)
            city = self._get_city_by_index(city_index)
        else:
            city_index = self._get_city_index(city) 
        if city and city.trade_route and city.trade_route.trade_points:
            resp = QMessageBox.question(self,
                "Delete Trade Route",
                f"Delete trade route path for {city.name}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if resp == QMessageBox.StandardButton.Yes:
                # Clear selection if this was the selected route
                if self.selected_trade_route_city == city:
                    self.clear_trade_route_selection_overlay()
                # Clear only the plotted path, keep the trade route object
                city.trade_route.trade_points.clear()
                self.mark_unsaved_changes()  # Mark as unsaved after deleting trade route
                self.clear_trade_route_visuals(city_index)
                return True
        else:
            try:
                self.clear_trade_route_selection_overlay()
                self.clear_trade_route_visuals(city_index)
            except Exception as ex:
                print(f"Error clearing trade route visuals: {ex}")
        return False

    def edit_city_from_trade_route_item(self, item):
        """Edit city from trade route context menu selection."""
        city_index = item.data(Qt.ItemDataRole.UserRole + 1)
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
        city_pixmap = self._pixmap_for_city(city.city_type)
        city_half_width = city_pixmap.width() // 2
        city_half_height = city_pixmap.height() // 2
        
        # Check if last point is within city icon bounds (center-based)
        return (city.x - city_half_width <= last_point.x <= city.x + city_half_width and 
                city.y - city_half_height <= last_point.y <= city.y + city_half_height)

    def _get_city_by_index(self, index: int):
        """Get city by index from current empire's cities list."""
        empire = self.state.current_empire_object
        if not empire or not hasattr(empire, 'cities') or index < 0 or index >= len(empire.cities):
            return None
        return empire.cities[index]
    
    def set_drawing_cursor(self, enable: bool, pixmap=None):
        """Unified cursor management for all modes."""
        widgets = (self, self.ui.graphicsView, self.ui.graphicsView.viewport())
        if not enable:
            for w in widgets: 
                try: w.unsetCursor()
                except: pass
            return
        
        # Use provided pixmap or determine from drawing mode
        if not pixmap:
            if self.edge_drawing_active: pixmap = self.edge_cursor_pixmap
            elif self.trade_drawing_active: pixmap = self.land_cursor_pixmap if self.trade_is_land else self.sea_cursor_pixmap
        
        if pixmap:
            try:
                # Center the cursor on the pixmap (hotspot at center)
                hotspot_x = pixmap.width() // 2
                hotspot_y = pixmap.height() // 2
                cursor = QCursor(pixmap,hotspot_x, hotspot_y )
                for w in widgets: w.setCursor(cursor)
            except:
                for w in widgets: 
                    try: w.unsetCursor()
                    except: pass

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
        if QApplication.activeModalWidget() or QApplication.activePopupWidget():
            return False

        # 2) Dispatch by event type
        if et == QEvent.Type.MouseMove:
            return self._handle_mouse_move(event)
    
        elif et in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
            return self._handle_mouse_click(event)
            
        elif et == QEvent.Type.KeyPress:
            return self._handle_key_press(event)
    
        return QObject.eventFilter(self, obj, event)
    
    def _handle_key_press(self, event):
        """Handle keyboard events for vertex editing and other shortcuts."""
        key = event.key()
        
        # Escape key cancels various operations
        if key == Qt.Key.Key_Escape:
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
        elif key in (Qt.Key.Key_Backspace, Qt.Key.Key_Delete):
            if self.trade_drawing_active:
                self._trade_undo_last_point()
                return True
        
        return False  # Don't consume other keys

    # =========================
    # HELPER HANDLERS
    # =========================

    def _handle_mouse_move(self, event):
        """Mouse move: update label, dragging icon, vertex editing, and edge preview."""
        gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else QCursor.pos()
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
        gp = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else QCursor.pos()
        view = self.ui.graphicsView
        vp = view.viewport()
        inside_view = vp.rect().contains(vp.mapFromGlobal(gp))
        btn = event.button()
        et = event.type()
    
        # Vertex editing mode
        if self.vertex_editing_active and et == QEvent.Type.MouseButtonPress:
            if btn == Qt.MouseButton.RightButton:
                # Right-click cancels vertex editing
                self.cancel_vertex_editing()
                return True
            elif btn == Qt.MouseButton.LeftButton:
                # Left-click finishes vertex editing
                scene_pos = view.mapToScene(vp.mapFromGlobal(gp))

                self.finish_vertex_editing(scene_pos)
                return True  # Consume the event
    
        # Dragging mode
        if self.is_dragging:
            return self._handle_drag_click(event, gp, inside_view)
    
        # Edge drawing mode
        if self.edge_drawing_active and et == QEvent.Type.MouseButtonPress:
            return self._handle_edge_click(event, gp, inside_view)

        # Trade drawing mode
        if self.trade_drawing_active and et == QEvent.Type.MouseButtonPress:
            return self._handle_trade_click(event, gp, inside_view)
        
        # Normal mode selection
        if not self.is_dragging and not self.edge_drawing_active and et == QEvent.Type.MouseButtonPress:
            return self._handle_normal_click(event, gp, inside_view)
    
        return False
    
    
    # =========================
    # SUB-MODE HANDLERS
    # =========================
        
    def _handle_drag_click(self, event, gp, inside_view):
        # cancel move/drag on right click (press or release), anywhere
        if event.button() == Qt.MouseButton.RightButton:
            self.moving_city = None
            self.deselect_item()
            return True
    
        if event.type() == QEvent.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton and not inside_view:
                self.deselect_item()
                return True
    
        elif event.type() == QEvent.Type.MouseButtonRelease:
            if event.button() == Qt.MouseButton.LeftButton:
                self.deselect_item()
                if inside_view:
                    view = self.ui.graphicsView
                    vp   = view.viewport()
                    vp_pos   = vp.mapFromGlobal(gp)         # viewport coords
                    scene_pos = view.mapToScene(vp_pos)     
                    self.handle_icon_drop(scene_pos)
                return True
    
        return False

    def _handle_edge_click(self, event, gp, inside_view):
        if event.button() == Qt.MouseButton.RightButton or not inside_view:
            self._edge_prompt_incomplete()
            return True
        if event.button() == Qt.MouseButton.LeftButton:
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
        if event.button() == Qt.MouseButton.RightButton and inside_view:
            scene_pos = self.ui.graphicsView.mapToScene(
                self.ui.graphicsView.viewport().mapFromGlobal(gp)
            )
            items = self.scene.items(scene_pos)
    
            for it in items:
                if it.flags() & QGraphicsItem.ItemIsSelectable:
                    # Optional: auto-select before showing menu
                    self._select_scene_item(it)
                    self._show_context_menu_for_item(it, gp)
                    return True
    
            # No selectable item -> clear selection
            self.deselect_all()
            return True
    
        # --- LEFT CLICK ---
        if event.button() == Qt.MouseButton.LeftButton and inside_view:
            scene_pos = self.ui.graphicsView.mapToScene(
                self.ui.graphicsView.viewport().mapFromGlobal(gp)
            )
            items = self.scene.items(scene_pos)
    
            for it in items:
                if it.flags() & QGraphicsItem.ItemIsSelectable:
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
        Handle selecting any selectable object on the scene.
        Only one selection can be active at a time.
        """
        # Clear ALL previous selection states
        self.clear_border_selection_overlay()
        self.clear_trade_route_selection_overlay()
        self.deselect_city_marker()
        self.border_selected = False
        self.selected_item = None

        # Trade route segment hit
        if hasattr(item, "data") and callable(item.data):
            route_type = item.data(Qt.ItemDataRole.UserRole)
            if route_type == "TRADE_ROUTE":
                city_index = item.data(Qt.ItemDataRole.UserRole + 1)
                city = self._get_city_by_index(city_index)
                if city:
                    self.select_trade_route_overlay(city)
                    self.selected_item = item
                    # Create vertex handles for editing
                    if city.trade_route and city.trade_route.trade_points:
                        pts = [(p.x, p.y) for p in city.trade_route.trade_points]
                        self.create_vertex_handles("TRADE_ROUTE", pts, city)
                    return
            
            # Vertex handle selection
            if route_type == "VERTEX_HANDLE":
                self.start_vertex_editing(item)
                return

        # Edge segment (hit proxy)
        if item in self.border_edge_hit_items:
            self.selected_edge_index = item.data(Qt.ItemDataRole.UserRole + 1)
            self.select_empire_border_overlay()
            self.selected_item = item
            # Create vertex handles for border editing
            empire = self.state.current_empire_object
            if empire and empire.border and empire.border.edges:
                pts = [(edge.x, edge.y) for edge in empire.border.edges]
                self.create_vertex_handles("EMPIRE_BORDER", pts)
            return
        
        # (optional: keep vertex/icon handling if you still want it)
        if item in self.border_icon_items:
            self.select_empire_border_overlay()
            self.selected_item = item
            return

        # City markers
        if hasattr(item, "data") and callable(item.data):
            city_obj = item.data(1)
            if city_obj and city_obj.__class__.__name__ == "City":
                self.select_city_marker(item, city_obj)
                return
    
        # If nothing matched, ensure nothing is selected
        self.deselect_all()

        
    def select_city_marker(self, item, city_obj):
        """Visual + state change when a city marker is selected."""
        self.selected_item = item
        # You could change appearance here (glow, outline, etc.)
        # Or just rely on QGraphicsItem's built-in selection visuals
        item.setSelected(True)
        # Maybe update side panel UI here
    
    def deselect_city_marker(self):
        """Clear city selection visuals."""
        if self.selected_item and self.selected_item in self.city_items.values():
            self.selected_item.setSelected(False)
        self.selected_item = None

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
        if self.selected_item == item:
            # already selected -> deselect
            self.deselect_item()
        else:
            self.select_item(item)
            # visually mark it selected in the list
            self.ui.listWidget.setCurrentItem(item)

    def select_item(self, item):
        self.deselect_all() # clear current selections first
        self.selected_item = item
        self.selected_kind = item.data(Qt.ItemDataRole.UserRole)  # EmpCityTypes or EmpObjTypes
        pixmap = item.icon().pixmap(self.ui.listWidget.iconSize())
        self.ui.graphicsView.setInteractive(False)

        # cache the exact pixmap used for drag
        self.drag_pixmap = pixmap
        
        # Don't create a floating icon - use cursor instead
        self.is_dragging = True
        self.set_drawing_cursor(True, pixmap)
        self.ui.graphicsView.setDragMode(QGraphicsView.DragMode.NoDrag)
        
        self._apply_interactivity_to_all(False)

    def deselect_item(self):
        self.selected_item = None
        self.is_dragging = False
        self.set_drawing_cursor(False)
        self.ui.graphicsView.setInteractive(True)

        self.ui.graphicsView.setDragMode(QGraphicsView.DragMode.NoDrag)  # not ScrollHandDrag
    
        # FIX: also clear the QListWidget’s selection so it’s not visually highlighted
        self.ui.listWidget.clearSelection()
        self._apply_interactivity_to_all(True)
            
    # ===================================================================
    # CORE VISUAL STATE MANAGEMENT
    # ===================================================================
    
    def deselect_all(self):
        """Clear all selection states."""
        self.clear_border_selection_overlay()
        self.clear_trade_route_selection_overlay()
        self.clear_vertex_handles()
        self.deselect_city_marker()
        self.border_selected = False
        self.selected_item = None
        self.selected_edge_index = None

    def _clear_selection_overlay(self, overlay_type):
        """Generic function to clear selection overlays."""
        if overlay_type == "border":
            items = [self.border_sel_line_items, self.border_sel_handle_items]
            for item_list in items:
                for it in item_list:
                    if hasattr(it, 'scene') and it.scene() is not None:
                        self.scene.removeItem(it)
                item_list.clear()
            self.border_selected = False
        elif overlay_type == "trade_route":
            items = [self.trade_route_sel_line_items, self.trade_route_sel_handle_items]
            for item_list in items:
                for it in item_list:
                    if hasattr(it, 'scene') and it.scene() is not None:
                        self.scene.removeItem(it)
                item_list.clear()
            self.trade_route_selected = False
            self.selected_trade_route_city = None
        elif overlay_type == "vertex":
            for handle in self.vertex_handle_items:
                if hasattr(handle, 'scene') and handle.scene() is not None:
                    self.scene.removeItem(handle)
            self.vertex_handle_items.clear()
            self.vertex_editing_active = False

    def clear_border_selection_overlay(self):
        """Remove border selection overlay."""
        self._clear_selection_overlay("border")
        
    def clear_vertex_handles(self):
        """Remove vertex editing handles."""
        self._clear_selection_overlay("vertex")

    # ===================================================================
    # UNIFIED MESSAGE BOXES & UTILITIES
    # ===================================================================
    
    def _show_warning(self, title, message):
        """Show a standardized warning message box."""
        return QMessageBox.warning(self, title, message, QMessageBox.StandardButton.Ok)
    
    def _show_question(self, title, message, default_button=QMessageBox.StandardButton.No):
        """Show a standardized question message box."""
        return QMessageBox.question(self, title, message, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, default_button)
    
    def _show_no_background_warning(self):
        """Show the standard 'no background' warning."""
        self._show_warning("No background", "Drop onto the background image area.")
        
    def _show_move_city_dialog(self, city, new_x, new_y):
        """Show dialog asking if user wants to move a city."""
        return self._show_question(
            "Move Our City?",
            f"Move 'Our City' from ({city.x}, {city.y}) to ({new_x}, {new_y})?"
        )
        
    def _show_incomplete_border_dialog(self):
        """Show dialog for incomplete border with multiple options."""
        return QMessageBox.warning(
            self, "Incomplete Border",
            "You have not closed the border shape. Would you like to save this border shape?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )
        
    def _show_incomplete_trade_route_dialog(self):
        """Show dialog for incomplete trade route."""
        return QMessageBox.information(
            self, "Incomplete Trade Route",
            "This trade route doesn't end on our city. Would you like to save it anyway?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel
        )

    def _clear_scene_state(self):
        """Clear all scene-related state when scene is cleared or reset."""
        # Clear selection state
        self.selected_item = None
        self.selected_kind = None
        self._trade_dot_reps = []
        self.selected_edge_index = None
        self.selected_trade_route_city = None
        
        # Clear city items tracking (items will be removed from scene by scene.clear())
        try:
            self.city_items.clear()
            self.city_labels.clear()

        except Exception as e:
            print(f"{e}")
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
        
        # Clear selection states
        self.trade_route_selected = False
        self.trade_route_sel_line_items = []
        self.trade_route_sel_handle_items = []
        self.trade_route_hit_items = []
        
        self.vertex_editing_active = False
        self.vertex_handle_items = []
        
        # Clear visual overlays
        try:
            self.clear_border_selection_overlay()
        except Exception as e:
            print(f"{e}")
        try:
            self.clear_trade_route_selection_overlay()
        except Exception as e:
            print(f"{e}")

    # ===================================================================
    # CITY & ENTITY MANAGEMENT
    # ===================================================================
    def _untick_default_city_if_removed(self, city):
        """Untick a city in the default cities menu if it was removed."""
        if not hasattr(self, 'cities_data') or not hasattr(self, 'city_actions'):
            return
            
        city_name = city.name
        current_map_name = self._get_current_map_name()
        
        if not current_map_name:
            return
            
        # Search for the city in all regions
        for region_name, cities in self.cities_data.items():
            if city_name in cities:
                city_data = cities[city_name]
                map_data = city_data.get("default_map", {}).get(current_map_name, {})
                
                # Check if this matches the coordinates of the removed city
                if (map_data.get("x") == city.x and map_data.get("y") == city.y):
                    # Find and untick the corresponding menu action
                    if region_name in self.city_actions:
                        for action in self.city_actions[region_name]:
                            if action.text() == city_name:
                                action.setChecked(False)
                                # Update the region "Select All" state
                                self._update_region_select_all_state(region_name)
                                return

    def _update_region_select_all_state(self, region_name):
        """Update the Select All action state for a region based on its cities."""
        if region_name not in self.region_actions or region_name not in self.city_actions:
            return
            
        region_action = self.region_actions[region_name]
        city_actions = self.city_actions[region_name]
        
        # Check if all cities are checked
        all_checked = all(action.isChecked() for action in city_actions)
        
        # Update the region action state
        region_action.setChecked(all_checked)
        
        # Also update the main "Add all" state
        self._update_main_select_all_state()

    def clear_empire_border_visual(self):
        """Clear empire border visuals."""
        self.clear_border_selection_overlay()
        if self.border_visual_group is not None:
            try:
                self.scene.removeItem(self.border_visual_group)
            except Exception:
                pass
            self.border_visual_group = None
        self.border_icon_items.clear()
    
    # ===================================================================
    # TRADE ROUTE CLICK HANDLING & DRAWING OPERATIONS
    # ===================================================================
    
    def _handle_trade_click(self, event, gp, inside_view):
        """Handle mouse clicks during trade route drawing."""
        if event.button() == Qt.MouseButton.RightButton or not inside_view:
            self._abort_trade_drawing()
            return True

        if event.button() == Qt.MouseButton.LeftButton:
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
                    city_pixmap = self._pixmap_for_city(city.city_type)
                    city_half_width = city_pixmap.width() // 2
                    city_half_height = city_pixmap.height() // 2
                    # Check if click is within city bounds (center-based coordinates)
                    if (city.x - city_half_width <= x <= city.x + city_half_width and 
                        city.y - city_half_height <= y <= city.y + city_half_height):
                        self._trade_undo_last_point() 
                        self._finalize_trade_route(success=True, reopen_dialog=True)
                        return True
                    break
            
            # Check for closing on existing point
            hit_idx = self._trade_hit_existing_point(x, y)
            if hit_idx == len(self.trade_drawing_points) - 2 and len(self.trade_drawing_points) >= 2:
                resp = self._show_incomplete_trade_route_dialog()
                if resp == QMessageBox.StandardButton.Yes:
                    self._trade_undo_last_point() 
                    self._finalize_trade_route(success=True)
                elif resp == QMessageBox.StandardButton.No:
                    self._abort_trade_drawing()
                else:
                    self._trade_undo_last_point()
            return True
        return False

    def start_trade_route(self, city):
        """Start drawing a trade route for a specific city."""
        if self.bg_item is None:
            self._show_no_background_warning()
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
            self.render_trade_route(city)
        else:
            self._abort_trade_drawing()
    
        self.ui.graphicsView.setInteractive(True)
        
        if reopen_dialog and city:
            QTimer.singleShot(100, lambda: self.edit_city(city))
    
    def _abort_trade_drawing(self):
        """Abort current trade route drawing session."""
        self._abort_drawing("trade", erase=True)
    
    def select_empire_border_overlay(self):
        """Mark the existing border overlay as selected, highlight selected edge thicker."""
        e = self.state.current_empire_object
        if not (self.empire_border and e and e.border and self.bg_item):
            return
        pts = [(edge.x, edge.y) for edge in e.border.edges]
        if len(pts) < 2:
            return
    
        self.clear_border_selection_overlay()
    
        selected_edge_idx = self.selected_edge_index
    
        # Draw dotted outline, making the selected edge thicker
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            p0 = self.bg_item.mapToScene(x0, y0)
            p1 = self.bg_item.mapToScene(x1, y1)
    
            # Thicker pen for the selected edge
            if selected_edge_idx == i:
                pen = QPen(Qt.black, 3)
            else:
                pen = QPen(Qt.black, 1)
            pen.setStyle(Qt.DotLine)
    
            seg = self.scene.addLine(p0.x(), p0.y(), p1.x(), p1.y(), pen)
            seg.setZValue(120)  # above icons
            self.border_sel_line_items.append(seg)
    
        # Square handles at vertices
        handle_size = 6
        half = handle_size / 2.0
        hpen = QPen(Qt.black, 1)
        hbrush = QBrush(Qt.white)
        for x, y in pts:
            p = self.bg_item.mapToScene(x, y)
            rect = self.scene.addRect(p.x() - half, p.y() - half, handle_size, handle_size, hpen, hbrush)
            rect.setZValue(130)
            self.border_sel_handle_items.append(rect)
    
        self.border_selected = True
    

    # %%% other input-adjacent 
    def _show_context_menu_for_item(self, item, global_pos):
        """Show context menu based on enum stored in item."""
        if not (hasattr(item, "data") and callable(item.data)):
            return

        obj_type = item.data(Qt.ItemDataRole.UserRole)
        if obj_type not in self.context_menu_options:
            return

        menu = QMenu(self)
        for label, callback in self.context_menu_options[obj_type]:
            act = QAction(label, self)
            # Fix lambda capture issue by using default parameter
            act.triggered.connect(lambda checked=False, cb=callback, it=item: cb(it))
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
    
    def drop_object(self, scene_pos):
        kind = self.selected_kind
        for enum in (ed.CityType, EmpObjTypes):
            try: kind = enum(kind); break
            except (ValueError, TypeError): pass
        if isinstance(kind, ed.CityType):
            self.handle_city_drop(scene_pos)
        elif kind == EmpObjTypes.EMPIRE_EDGE:
            self.handle_drop_empire_edge(scene_pos)
        else:
            print(f"Unknown kind: {kind}")

    # ---------- DROP HANDLER ----------
    def handle_icon_drop(self, scene_pos):
        # moving existing city?
        if self.moving_city is not None:
            xy = self._scene_to_image_xy(scene_pos)
            city = self.moving_city
            self.moving_city = None
            if xy is not None:
                x, y = xy
                self._remove_city_marker(city)

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
                    self.render_trade_route(city)

                self._place_city_marker(city, x, y)
                self.refresh_map() #handle all route updates and stuff
            return
        else:
            # Unified entry point now
            self.drop_object(scene_pos)
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
            color = QColor(255, 140, 0) if self.trade_is_land else Qt.cyan
            dot_item = self.scene.addEllipse(p.x() - 2, p.y() - 2, 4, 4, QPen(Qt.NoPen), QBrush(color))
            dot_item.setZValue(90)
            self.trade_drawing_point_items.append(dot_item)
            
            # Segment line
            if make_segment and len(self.trade_drawing_points) >= 2:
                x0, y0 = self.trade_drawing_points[-2]
                p0 = self.bg_item.mapToScene(x0, y0)
                line_item = self.scene.addLine(p0.x(), p0.y(), p.x(), p.y(), QPen(color, 2))
                line_item.setZValue(80)
                self.trade_drawing_line_items.append(line_item)
            
            self._create_temp_line("trade")
            
        elif drawing_type == "edge":
            # Prevent duplicate consecutive points
            if self.edge_points_img and self.edge_points_img[-1] == (x_img, y_img):
                return
                
            self.edge_points_img.append((x_img, y_img))
            
            # Red vertex dot
            dot_item = self._place_dot(x_img, y_img, r=5.0, brush=QBrush(Qt.red), z=90)
            if dot_item:
                self.edge_point_items.append(dot_item)
            
            # Segment line
            if make_segment and len(self.edge_points_img) >= 2:
                x0, y0 = self.edge_points_img[-2]
                line_item = self._place_line(x0, y0, x_img, y_img, pen=QPen(Qt.red, 2), z=80)
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
            if not (self.trade_drawing_active and self.trade_temp_line_item and 
                    self.trade_drawing_points and self.bg_item):
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
                    p_last.x(), p_last.y(), p_last.x(), p_last.y(), QPen(Qt.red, 2)
                )
                self.edge_temp_line_item.setZValue(100)
                
            if cursor_scene_pos is None:
                self.edge_temp_line_item.setLine(p_last.x(), p_last.y(), p_last.x(), p_last.y())
            else:
                self.edge_temp_line_item.setLine(
                    p_last.x(), p_last.y(), cursor_scene_pos.x(), cursor_scene_pos.y()
                )
            if self.edge_drawing_active:
                self.set_drawing_cursor(True)

    def _create_temp_line(self, drawing_type: str):
        """Generic function to create temp lines for drawing."""
        if drawing_type == "trade":
            if not self.trade_drawing_points or self.bg_item is None:
                return
            last_x, last_y = self.trade_drawing_points[-1]
            p0 = self.bg_item.mapToScene(last_x, last_y)
            pen = QPen(QColor(255, 140, 0) if self.trade_is_land else Qt.cyan, 2)
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
    def create_vertex_handles(self, vertex_type, points, city=None):
        """Create vertex handles for editing trade routes or empire borders."""
        self.clear_vertex_handles()
        
        if not points or not self.bg_item:
            return
        
        handle_size = 8
        half = handle_size / 2.0
        
        for i, (x, y) in enumerate(points):
            scene_pos = self.bg_item.mapToScene(x, y)
            
            # Create blue square handle
            handle = self.scene.addRect(
                scene_pos.x() - half, scene_pos.y() - half, 
                handle_size, handle_size,
                QPen(Qt.blue, 1), QBrush(Qt.blue)
            )
            handle.setZValue(140)  # Above everything else
            handle.setFlag(QGraphicsItem.ItemIsSelectable, True)
            handle.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Store data for vertex editing
            handle.setData(Qt.ItemDataRole.UserRole, "VERTEX_HANDLE")
            handle.setData(Qt.ItemDataRole.UserRole + 1, vertex_type)  # "TRADE_ROUTE" or "EMPIRE_BORDER"
            handle.setData(Qt.ItemDataRole.UserRole + 2, i)  # Vertex index
            if city:
                handle.setData(Qt.ItemDataRole.UserRole + 3, city)  # City object for trade routes
                
            self.vertex_handle_items.append(handle)

    def start_vertex_editing(self, handle_item):
        """Start editing a vertex by making it stick to the mouse."""
        if self.vertex_editing_active:
            return  # Already editing
            
        vertex_type = handle_item.data(Qt.ItemDataRole.UserRole + 1)
        vertex_index = handle_item.data(Qt.ItemDataRole.UserRole + 2)
        city = handle_item.data(Qt.ItemDataRole.UserRole + 3)  # May be None for borders
        
        self.vertex_editing_active = True
        self.editing_vertex_type = vertex_type
        self.editing_vertex_index = vertex_index
        self.editing_vertex_city = city
        self.editing_vertex_handle = handle_item
        
        # Visual feedback - make handle yellow while editing
        handle_item.setBrush(QBrush(Qt.yellow))
        
        # Disable view interaction during editing
        self.ui.graphicsView.setInteractive(False)

    def update_vertex_position(self, scene_pos):
        """Update vertex position during dragging."""
        if not self.vertex_editing_active or not self.editing_vertex_handle:
            return
            
        # Move the handle to follow the mouse
        # handle_size = 8
        # half = handle_size / 2.0
        rect = self.editing_vertex_handle.rect()
        rect.moveCenter(scene_pos)
        self.editing_vertex_handle.setRect(rect)

    def finish_vertex_editing(self, scene_pos):
        """Finish vertex editing and save changes."""
        if not self.vertex_editing_active:
            return
            
        # Convert scene position to image coordinates
        xy = self._scene_to_image_xy(scene_pos)
        if xy is None:
            self.cancel_vertex_editing()
            return
            
        x, y = xy
        
        # Update the underlying data
        if self.editing_vertex_type == "TRADE_ROUTE" and self.editing_vertex_city:
            city = self.editing_vertex_city
            if (city.trade_route and city.trade_route.trade_points and 
                0 <= self.editing_vertex_index < len(city.trade_route.trade_points)):
                # Update the trade point
                city.trade_route.trade_points[self.editing_vertex_index].x = int(x)
                city.trade_route.trade_points[self.editing_vertex_index].y = int(y)
                self.mark_unsaved_changes()  # Mark as unsaved after modifying trade route
                # Re-render the trade route
                # Rebuild global dot reps and rerender all routes so dedupe is correct
                self._trade_dot_reps = []
                for c in self.state.current_empire_object.cities:
                    if c.trade_route:
                        self.render_trade_route(c)
                
                # Recreate handles for the edited route
                pts = [(p.x, p.y) for p in city.trade_route.trade_points]
                self.create_vertex_handles("TRADE_ROUTE", pts, city)
                # Recreate vertex handles with new positions
                
        elif self.editing_vertex_type == "EMPIRE_BORDER":
            empire = self.state.current_empire_object
            if (empire and empire.border and empire.border.edges and 
                0 <= self.editing_vertex_index < len(empire.border.edges)):
                # Update the border edge
                empire.border.edges[self.editing_vertex_index].x = int(x)
                empire.border.edges[self.editing_vertex_index].y = int(y)
                self.mark_unsaved_changes()  # Mark as unsaved after modifying border
                # Re-render the empire border

                # Recreate vertex handles with new positions
                pts = [(edge.x, edge.y) for edge in empire.border.edges]
                self.create_vertex_handles("EMPIRE_BORDER", pts)
                self.render_empire_border()
        # Reset editing state
        self.vertex_editing_active = False
        self.editing_vertex_type = None
        self.editing_vertex_index = None
        self.editing_vertex_city = None
        self.editing_vertex_handle = None
        self.ui.graphicsView.setInteractive(True)

    def cancel_vertex_editing(self):
        """Cancel vertex editing without saving changes."""
        if not self.vertex_editing_active:
            return
            
        # Restore original handle color
        if self.editing_vertex_handle:
            self.editing_vertex_handle.setBrush(QBrush(Qt.blue))
        
        # Reset editing state
        self.vertex_editing_active = False
        self.editing_vertex_type = None
        self.editing_vertex_index = None
        self.editing_vertex_city = None
        self.editing_vertex_handle = None
        self.ui.graphicsView.setInteractive(True)
    
    def _place_pixmap(self, x: float, y: float, pm: QPixmap, z: float, group: QGraphicsItemGroup | None = None,
                      center: bool = True, data: dict | None = None, cursor=Qt.CursorShape.ArrowCursor,
                      item_cls=QGraphicsPixmapItem):
        """Place a pixmap at image coords (x,y) mapped to scene, return the item."""
        if self.bg_item is None or pm is None or pm.isNull():
            return None
        p = self._img_to_scene(x, y)
        it = item_cls(pm)
        if center:
            it.setOffset(-pm.width() / 2.0, -pm.height() / 2.0)
        it.setPos(p)
        it.setZValue(z)
        it.setCursor(cursor)
        if data:
            for role, val in data.items():
                it.setData(role, val)
        if group is not None:
            group.addToGroup(it)
        else:
            self.scene.addItem(it)
        return it
    
    def _place_dot(self, x: float, y: float, r: float, brush: QBrush, z: float,
                   group: QGraphicsItemGroup | None = None):
        """Place a filled circle at image coords; return the item."""
        if self.bg_item is None:
            return None
        p = self._img_to_scene(x, y)
        it = self.scene.addEllipse(p.x()-r, p.y()-r, 2*r, 2*r, QPen(Qt.NoPen), brush)
        it.setZValue(z)
        if group is not None:
            group.addToGroup(it)
        return it
    
    def _place_line(self, x0: float, y0: float, x1: float, y1: float, pen: QPen, z: float,
                    group: QGraphicsItemGroup | None = None):
        """Place a line between image coords; return the item."""
        if self.bg_item is None:
            return None
        p0 = self._img_to_scene(x0, y0)
        p1 = self._img_to_scene(x1, y1)
        it = self.scene.addLine(p0.x(), p0.y(), p1.x(), p1.y(), pen)
        it.setZValue(z)
        if group is not None:
            group.addToGroup(it)
        return it
    
    def _stamp_along_segment(self, x0: float, y0: float, x1: float, y1: float, spacing: float,
                             place_cb, include_start=True, include_end=True):
        """Call place_cb(x, y) along one segment with uniform spacing."""
        dx, dy = (x1 - x0), (y1 - y0)
        seg_len = (dx*dx + dy*dy) ** 0.5
        if seg_len <= 1e-6:
            if include_start and include_end:
                place_cb(x0, y0)  # degenerate
            return
        ux, uy = dx / seg_len, dy / seg_len
        if include_start:
            place_cb(x0, y0)
        dist = spacing
        # center-to-center spacing; stop just before end, end handled by include_end
        while dist < seg_len - 1e-6:
            place_cb(x0 + ux*dist, y0 + uy*dist)
            dist += spacing
        if include_end:
            place_cb(x1, y1)
    
    def _stamp_along_polyline(self, pts: list[tuple[float, float]], spacing: float, place_cb,
                              include_ends=True):
        """Stamp along a whole polyline."""
        if not pts:
            return
        if len(pts) == 1:
            if include_ends:
                place_cb(pts[0][0], pts[0][1])
            return
        # first point stamped by the first segment when include_ends=True
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i+1]
            self._stamp_along_segment(x0, y0, x1, y1, spacing, place_cb,
                                      include_start=(include_ends and i == 0),
                                      include_end=(include_ends or i < len(pts)-2))
    
    def _get_trade_dot_pixmap(self, is_land: bool) -> QPixmap:
        """Get the appropriate dot pixmap for trade routes."""
        key = "land_dot" if is_land else "sea_dot"
        pil = self.state.images.get(key)       
        pm = self.pil_to_qpixmap(pil)
        pm.setDevicePixelRatio(1.0)
        return pm
        
    def _get_empire_edge_pixmap(self) -> QPixmap:
        """Get the empire edge pixmap for border rendering."""
        for el in self.state.elements:
            if el["kind"] == EmpObjTypes.EMPIRE_EDGE:
                return self.pil_to_qpixmap(el["pil"])
        return QPixmap()
    
    # ==== trade route rendering (uses shared stamping) =========================
    
    def clear_trade_route_visuals(self, city_index: int):
        """Remove visual elements for a specific city's trade route."""
        # Clear selection if this route is selected
        if (self.trade_route_selected and 
            self.selected_trade_route_city and 
            self._get_city_index(self.selected_trade_route_city) == city_index):
            self.clear_trade_route_selection_overlay()
        
        # Remove the group and all its items
        if city_index in self._trade_route_groups:
            group = self._trade_route_groups[city_index]
            if group.scene() is not None:  # Defensive check
                self.scene.removeItem(group)
            del self._trade_route_groups[city_index]
            
        # Remove hit items for this city's trade route - more robust cleanup
        items_to_remove = []
        for item in self.trade_route_hit_items:
            if hasattr(item, 'data') and callable(item.data) and item.data(Qt.ItemDataRole.UserRole + 1) == city_index:
                items_to_remove.append(item)
        
        for item in items_to_remove:
            self.trade_route_hit_items.remove(item)
            # Items are already removed with the group, no need to remove from scene again

    def clear_all_trade_route_visuals(self):
        """Remove all permanent trade route visuals."""
        for group in self._trade_route_groups.values():
            self.scene.removeItem(group)
        self._trade_route_groups.clear()
        
        # Clear all hit items
        self.trade_route_hit_items.clear()
        
        # Clear selection if any trade route is selected
        if self.trade_route_selected:
            self.clear_trade_route_selection_overlay()

    def clear_trade_route_selection_overlay(self):
        """Remove trade route selection visuals (dotted lines and white squares)."""
        self._clear_selection_overlay("trade_route")

    def select_trade_route_overlay(self, city):
        """Show selection overlay for a trade route (dotted lines + white squares)."""
        if not city or not city.trade_route or not city.trade_route.trade_points or len(city.trade_route.trade_points) < 2:
            return
        
        # Ensure background item exists before proceeding
        if self.bg_item is None:
            return
            
        self.clear_trade_route_selection_overlay()
        
        pts = [(p.x, p.y) for p in city.trade_route.trade_points]
        
        # Draw dotted outline for each segment
        for i in range(len(pts) - 1):
            x0, y0 = pts[i]
            x1, y1 = pts[i + 1]
            p0 = self.bg_item.mapToScene(x0, y0)
            p1 = self.bg_item.mapToScene(x1, y1)
            
            pen = QPen(QColor(255, 140, 0) if city.trade_route.r_type == ed.TradeRouteType.LAND else Qt.cyan, 2)
            pen.setStyle(Qt.DotLine)
            
            seg = self.scene.addLine(p0.x(), p0.y(), p1.x(), p1.y(), pen)
            seg.setZValue(120)  # Above everything else
            self.trade_route_sel_line_items.append(seg)
        
        # Add white square handles at vertices
        handle_size = 6
        half = handle_size / 2.0
        hpen = QPen(Qt.black, 1)
        hbrush = QBrush(Qt.white)
        for x, y in pts:
            p = self.bg_item.mapToScene(x, y)
            rect = self.scene.addRect(p.x() - half, p.y() - half, handle_size, handle_size, hpen, hbrush)
            rect.setZValue(130)  # Above dotted lines
            self.trade_route_sel_handle_items.append(rect)
        
        self.trade_route_selected = True
        self.selected_trade_route_city = city
        
    def _make_trade_dot_placer(self, dot_pm, group, placed_reps, merge_radius_px=6):
        """Return a place_cb(x,y) that skips dots within merge_radius_px of an existing one."""
        r2 = merge_radius_px * merge_radius_px
    
        def place_cb(x, y):
            ix, iy = int(x), int(y)
            # skip if close to an existing representative
            for rx, ry in placed_reps:
                dx, dy = ix - rx, iy - ry
                if dx*dx + dy*dy <= r2:
                    return  # too close → don't render another dot
            # keep this one as the cluster rep and actually place it
            placed_reps.append((ix, iy))
            self._place_pixmap(ix, iy, dot_pm, z=5, group=group, center=True)
        return place_cb
        
    def render_trade_route(self, city):
        """Render permanent trade route visuals for a specific city, with dot dedupe and selectable hit segments."""
        city_index = self._get_city_index(city)
        if city_index is None:
            return
    
        # clear any old visuals for this city (removes group & its children)
        self.clear_trade_route_visuals(city_index)
    
        if not city.trade_route:
            return
    
        # make a group for the route visuals
        group = QGraphicsItemGroup()
        group.setZValue(5)
        self.scene.addItem(group)
        self._trade_route_groups[city_index] = group
    
        # build the polyline points (keep start city + "our city" endpoint, like your other impl)
        pts = [(p.x, p.y) for p in city.trade_route.trade_points]
        pts.insert(0, (city.x, city.y))
        has_ours, our_city = self.state.has_our_city()
        if has_ours:
            pts.append((our_city.x, our_city.y))
    
        # stamp dots with global de-dup
        is_land = (city.trade_route.r_type == ed.TradeRouteType.LAND)
        dot_pm = self._get_trade_dot_pixmap(is_land)
    
        if not dot_pm.isNull():
            reps = getattr(self, "_trade_dot_reps", [])
            r2 = 6 * 6  # merge radius ~ dot diameter
    
            def place_trade_dot(x, y):
                ix, iy = int(x), int(y)
                for rx, ry in reps:
                    dx, dy = ix - rx, iy - ry
                    if dx*dx + dy*dy <= r2:
                        return  # too close—skip
                reps.append((ix, iy))
                self._place_pixmap(ix, iy, dot_pm, z=5, group=group, center=True)
    
            self._stamp_along_polyline(pts, spacing=12, place_cb=place_trade_dot, include_ends=True)

        # ALWAYS add wide, invisible hit segments so the route is selectable/editable
        for i in range(len(pts) - 1):
            try:
                p0 = self._img_to_scene(pts[i][0], pts[i][1])
                p1 = self._img_to_scene(pts[i+1][0], pts[i+1][1])
                hit = QGraphicsLineItem(p0.x(), p0.y(), p1.x(), p1.y())
                hit.setPen(QPen(Qt.transparent, 12))  # wide click target
                hit.setZValue(6)                      # above dots, below overlays
                hit.setFlag(QGraphicsItem.ItemIsSelectable, True)
                hit.setData(Qt.ItemDataRole.UserRole, "TRADE_ROUTE")
                hit.setData(Qt.ItemDataRole.UserRole + 1, city_index)  # city idx
                hit.setData(Qt.ItemDataRole.UserRole + 2, i)           # segment idx
                group.addToGroup(hit)
                self.trade_route_hit_items.append(hit)
            except Exception as e:
                print(f"Error creating trade route hit items: {e}")
                continue


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

        resp = self._show_incomplete_border_dialog()
        
        if resp == QMessageBox.StandardButton.Yes:
            self._finalize_edge(success=True, close_to_index=0)
        elif resp == QMessageBox.StandardButton.No:
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
            close_item = self._place_line(x_last, y_last, x_close, y_close, QPen(Qt.red, 2), 80)
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

        # Mark border present and render the permanent overlay
        self.empire_border = True
        self.render_empire_border()
        
    def _save_border_shape(self, points_img_xy: list[tuple[int, int]], density: int = 28):
        """Persist the border polyline to the model as ed.Border with ed.Edge entries."""
        empire = self.state.current_empire_object
        if empire is None:
            return

        try:
            edges = [ed.Edge(x=int(x), y=int(y), hidden=False) for (x, y) in points_img_xy]
            border_obj = ed.Border(density=int(density), edges=edges)
            empire.border = border_obj  # single border only
            self.mark_unsaved_changes()  # Mark as unsaved after creating border
        except Exception:
            # Fallback if dataclasses not available for some reason
            border_obj = type("Border", (), {})()
            border_obj.density = int(density)
            border_obj.edges = [type("Edge", (), {"x": int(x), "y": int(y), "hidden": False})() for (x, y) in points_img_xy]
            empire.border = border_obj
    
    def _edge_abort(self, erase: bool):
        """Stop drawing; optionally erase temp items; always reset cursor consistently."""
        self._abort_drawing("edge", erase=erase)
    
    # ==== border rendering (uses the same stamping helpers) ====================
    
    def render_empire_border(self):
        if not self.empire_border:
            return
        e = self.state.current_empire_object
        if e is None or e.border is None or self.bg_item is None:
            return
    
        pts = [(edge.x, edge.y) for edge in e.border.edges]
        if len(pts) < 2:
            return
    
        hidden = [bool(edg.hidden) for edg in e.border.edges]
        density = e.border.density or 28
        icon_pm = self._get_empire_edge_pixmap()
        if icon_pm.isNull():
            return
    
        # clear previous visuals
        self.clear_border_selection_overlay()
        self.clear_empire_border_visual()
        self.border_edge_hit_items.clear()
    
        # group for everything
        self.border_visual_group = QGraphicsItemGroup()
        self.border_visual_group.setZValue(75)
        self.scene.addItem(self.border_visual_group)

        def place_flag_icon(x_img: int, y_img: int):
            it = self._place_pixmap(
                x_img, y_img, icon_pm, z=75, group=self.border_visual_group, center=True
            )
            if it:
                it.setFlag(QGraphicsPixmapItem.ItemIsSelectable, False)
                it.setAcceptHoverEvents(False)
                it.setCursor(Qt.CursorShape.ArrowCursor)
                it.setData(Qt.ItemDataRole.UserRole, EmpObjTypes.EMPIRE_EDGE)
                self.border_icon_items.append(it)
    
        def place_blue_vertex(i: int):
            self._place_dot(pts[i][0], pts[i][1], r=5.0, brush=QBrush(Qt.blue), z=85,
                            group=self.border_visual_group)
    
        n = len(pts)
        # selectable hit-lines and stamping/blue-dots per segment
        for i in range(n):
            j = (i + 1) % n
            # fat invisible selectable hit
            p0 = self._img_to_scene(pts[i][0], pts[i][1])
            p1 = self._img_to_scene(pts[j][0], pts[j][1])
            hit = QGraphicsLineItem(p0.x(), p0.y(), p1.x(), p1.y())
            hit.setPen(QPen(Qt.transparent, 12))
            hit.setZValue(76)
            hit.setFlag(QGraphicsItem.ItemIsSelectable, True)
            hit.setData(Qt.ItemDataRole.UserRole, EmpObjTypes.EMPIRE_EDGE)
            hit.setData(Qt.ItemDataRole.UserRole + 1, i)  # edge index
            self.border_visual_group.addToGroup(hit)
            self.border_edge_hit_items.append(hit)
    
            if hidden[i]:
                place_blue_vertex(i)
                continue
    
            # stamp flags along this visible segment using the shared segment stamper
            self._stamp_along_segment(
                pts[i][0], pts[i][1], pts[j][0], pts[j][1],
                spacing=density, place_cb=lambda x, y: place_flag_icon(int(round(x)), int(round(y))),
                include_start=True, include_end=True
            )
        return
    
    def delete_empire_border(self, force = False):
        """Delete the empire border with optional confirmation."""
        if not force:
            resp = QMessageBox.question(
                self,
                "Delete Border",
                "Are you sure you want to delete the empire border?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if resp != QMessageBox.StandardButton.Yes:
                return
        
        # Clear from model
        empire = self.state.current_empire_object
        if empire:
            empire.border = None
        
        # Clear visuals
        self.clear_empire_border_visual()
        self.empire_border = False
        
    def toggle_edge_hidden_from_item(self, item):
        """Toggle the hidden state of an edge segment."""
        empire = self.state.current_empire_object
        if not (empire and empire.border):
            return
        
        edge_index = item.data(Qt.ItemDataRole.UserRole + 1)  # stored during render
        if edge_index is None:
            return
            

        edges = empire.border.edges
        if 0 <= edge_index < len(edges):
            edges[edge_index].hidden = not bool(edges[edge_index].hidden)
            self.render_empire_border()
        
        
    def handle_drop_empire_edge(self, scene_pos):
        # If we already have a border, ask first
        if self.empire_border and self.state.current_empire_object.border:
            resp = QMessageBox.question(
                self,
                "Start New Border?",
                "An empire border already exists. Start a new one and discard the current border?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if resp != QMessageBox.StandardButton.Yes:
                return
            # erase model + visuals
            self.delete_empire_border(force = True)
    
        xy = self._scene_to_image_xy(scene_pos)
        if xy is None:
            self._show_no_background_warning()
            return
        x, y = xy
        
        if not self.state.check_if_empire():
            # Create empire and update with current background info if available
            self.state.new_empire()
            if self.bg_item and hasattr(self, '_current_image_path'):
                # Update with current background information
                pixmap = self.bg_item.pixmap()
                if self.bg_type == ed.EmpBackgroundTypes.CUSTOM:
                    self.state.current_empire_object.version = 2
                    self.state.current_empire_object.map_info = ed.Map(
                        image=os.path.basename(self._current_image_path),
                        width=pixmap.width(),
                        height=pixmap.height()
                    )
                    self.state.current_empire_object.show_ireland = False

        # Start edge drawing immediately
        self._begin_edge_drawing(x, y)

# %% Everything else
   
    # ---------- ROUTER ----------
    

    def add_city_icons_to_list(self):
        self.ui.listWidget.clear()
        for el in self.state.elements:
            # Skip disabled elements
            if not el.get("enabled", True):
                continue
                
            item = QListWidgetItem(el["name"])
            item.setIcon(QIcon(self.pil_to_qpixmap(el["pil"])))
            item.setSizeHint(QSize(100, 80))
            item.setData(Qt.ItemDataRole.UserRole, el["kind"])   # store the enum directly (EmpCityTypes or EmpObjTypes)
            self.ui.listWidget.addItem(item)
        self.ui.listWidget.setIconSize(QSize(64, 64))

    def _no_bg_item_alive(self):
        # alive iff we have an object AND it still belongs to a scene
        return self.no_bg_item is not None and self.no_bg_item.scene() is not None
    
    def _pixmap_for_city(self, ctype) -> QPixmap:
        for el in self.state.elements:
            if el["kind"] == ctype:
                # keep original image size from your PIL source
                return self.pil_to_qpixmap(el["pil"])
        return QPixmap()

    def _place_city_marker(self, city, x, y):
        """Place a city marker at the given top-left coordinates (x, y are top-left for scene placement)."""
        pm = self._pixmap_for_city(city.city_type)
        if self.bg_item is None:
            return
        offset_x = x - pm.width()//2
        offset_y = y - pm.height()//2
        scene_pt = self.bg_item.mapToScene(offset_x, offset_y)
    
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
            kind = city.city_type
            if kind is not None:
                item.setData(Qt.ItemDataRole.UserRole, kind)
            else:
                print(f"WARNING: No kind mapping found for city.city_type = {city.city_type}")
            self.scene.addItem(item)
            self.city_items[key] = item
    
        # Apply current interactivity state (pointer on hover only when not dragging)
        self._apply_item_interactivity(item, enable=not self.is_dragging)
        
        # Apply current visibility state based on view options
        if hasattr(self.ui, 'actionViewOption1'):
            item.setVisible(self.ui.actionViewOption1.isChecked())
        
        # Create and add label if needed
        self._create_city_label(city)

    def _apply_item_interactivity(self, item, enable: bool):
        item.setAcceptHoverEvents(enable)
        item.setCursor(Qt.CursorShape.PointingHandCursor if enable else Qt.CursorShape.ArrowCursor)
    
    def _apply_interactivity_to_all(self, enable: bool):
        # Create a copy of the values to avoid issues with items being deleted during iteration
        items_to_process = list(self.city_items.values())
        for it in items_to_process:
            # Check if the item is still valid before accessing it
            try:
                self._apply_item_interactivity(it, enable)
            except RuntimeError:
                # Item was deleted from C++ side, remove it from our tracking
                # Find and remove the corresponding entry
                keys_to_remove = [k for k, v in self.city_items.items() if v == it]
                for key in keys_to_remove:
                    self.city_items.pop(key, None)

    def _remove_city_marker(self, city):
        """Remove the scene item for this city, if it exists."""
        key = id(city)
        
        # Remove city icon
        item = self.city_items.pop(key, None)
        if item is not None:
            self.scene.removeItem(item)
            # let Qt delete C++ object; don't keep stale refs
        
        # Remove name label
        self._remove_city_label(city)
# %% No-background message
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
        self.no_bg_item = None  # clear stale reference
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
# %% Default cities
    def _update_default_cities_menu_state(self):
        """Enable/disable Default Cities menu based on background type."""
        # Enable menu only for predefined map types
        should_enable = self.bg_type in [
            ed.EmpBackgroundTypes.BIG_MAP,
            ed.EmpBackgroundTypes.NORTH_MAP,
            ed.EmpBackgroundTypes.SOUTH_MAP
        ]
        
        self.ui.menuDefaultCities.setEnabled(should_enable)
        
        # If enabled, sync the menu state with loaded cities
        if should_enable:
            self._sync_default_cities_menu_with_loaded_empire()

    def _sync_default_cities_menu_with_loaded_empire(self):
        """Sync the default cities menu checkboxes with cities already loaded in the empire."""
        if not self.state.current_empire_object or not hasattr(self.state.current_empire_object, 'cities'):
            return
            
        if not hasattr(self, 'cities_data') or not hasattr(self, 'city_actions'):
            return
            
        current_map_name = self._get_current_map_name()
        if not current_map_name or current_map_name == ed.EmpBackgroundTypes.CUSTOM:
            return
            
        # Get all cities currently in the empire
        loaded_cities = self.state.current_empire_object.cities
        
        # Clear all checkboxes first
        for region_name, region_city_actions in self.city_actions.items():
            for action in region_city_actions:
                action.setChecked(False)
        
        # Check cities that match default city positions
        for loaded_city in loaded_cities:
            # Try to find this city in the default cities data
            for region_name, cities in self.cities_data.items():
                for city_name, city_data in cities.items():
                    map_data = city_data.get("default_map", {}).get(current_map_name)
                    if map_data:
                        expected_x = map_data.get("x")
                        expected_y = map_data.get("y")
                        
                        # Check if the loaded city matches this default city position (within tolerance)
                        if (expected_x is not None and expected_y is not None and
                            abs(loaded_city.x - expected_x) <= 5 and  # 5 pixel tolerance
                            abs(loaded_city.y - expected_y) <= 5):
                            
                            # Find the corresponding action and check it
                            if region_name in self.city_actions:
                                for action in self.city_actions[region_name]:
                                    if action.text() == city_name:
                                        action.setChecked(True)
                                        break
                            break
        
        # Update the "Select All" states for each region
        for region_name in self.region_actions:
            self._update_region_select_all_state(region_name)
        
        # Update the main "Add all" state
        self._update_main_select_all_state()
        
    def _place_default_city(self, region_name, city_name):
        """Place a default city on the map using coordinates from JSON."""
        try:
            current_map_name = self._get_current_map_name()
            if not current_map_name or not hasattr(self, 'cities_data'):
                return
            
            # Get city data from JSON
            city_data = self.cities_data.get(region_name, {}).get(city_name, {})
            map_data = city_data.get("default_map", {}).get(current_map_name, {})
            
            if not map_data:
                print(f"No coordinates found for {city_name} on {current_map_name}")
                return
            
            x = map_data.get("x")
            y = map_data.get("y")
           
            
            if x is None or y is None:
                print(f"Invalid coordinates for {city_name}: x={x}, y={y}")
                return
            
            # Check if city already exists at this location to avoid duplicates
            if self.state.check_if_empire():
                empire = self.state.current_empire_object
                for existing_city in empire.cities:
                    if (existing_city.name == city_name and 
                        abs(existing_city.x - x) <= 2 and abs(existing_city.y - y) <= 2):
                        # City already exists at this location, don't add duplicate
                        print(f"City {city_name} already exists at ({x}, {y})")
                        return
            
            # Create a city object and map the type from JSON
            city = ed.City(city_name, x, y)
            city.city_type = ed.CityType.ROMAN
            # Use unified method to add the city properly
            self._add_city_to_empire(city, force_add=True)            
        except Exception as e:
            print(f"Error placing city {city_name}: {e}")
    
    def _remove_default_city(self, region_name, city_name):
        """Remove a default city from the map."""
        try:
            if not self.state.check_if_empire():
                return
            
            empire = self.state.current_empire_object
            current_map_name = self._get_current_map_name()
            
            # Get expected coordinates for this default city
            expected_coords = None
            if hasattr(self, 'cities_data') and current_map_name:
                city_data = self.cities_data.get(region_name, {}).get(city_name, {})
                map_data = city_data.get("default_map", {}).get(current_map_name, {})
                if map_data:
                    expected_x = map_data.get("x")
                    expected_y = map_data.get("y")
                    if expected_x is not None and expected_y is not None:
                        expected_coords = (expected_x, expected_y)
            
            # Find and remove cities that match the name and location (if known)
            cities_to_remove = []
            for city in empire.cities:
                if city.name == city_name:
                    # If we know the expected coordinates, only remove cities at that location
                    if expected_coords:
                        expected_x, expected_y = expected_coords
                        if abs(city.x - expected_x) <= 5 and abs(city.y - expected_y) <= 5:
                            cities_to_remove.append(city)
                    else:
                        # If we don't know expected coordinates, remove all cities with this name
                        cities_to_remove.append(city)
            
            # Remove the identified cities
            for city in cities_to_remove:
                empire.cities.remove(city)
                self._remove_city_marker(city)
                
                # Remove name label if it exists using proper key
                city_key = id(city)
                if city_key in self.city_labels:
                    try:
                        text_item = self.city_labels[city_key]
                        if hasattr(text_item, 'bg_rect'):
                            self.scene.removeItem(text_item.bg_rect)
                        self.scene.removeItem(text_item)
                        del self.city_labels[city_key]
                    except (RuntimeError, KeyError):
                        pass
            
            if cities_to_remove:
                print(f"Removed {len(cities_to_remove)} instance(s) of {city_name}")
            
        except Exception as e:
            print(f"Error removing city {city_name}: {e}")
# %% Other

    
    def set_background_image(self, pil_img, open_dialog = False):
        #if no empire atm -> ask to create one
        if open_dialog:
            # Check for unsaved changes before changing background
            if not self._check_before_discarding("background"):
                return
                
            file_path, _ = QFileDialog.getOpenFileName(
                self, "Select Background Image", "", "Images (*.png *.jpg *.bmp *.gif)"
            )
            if not file_path:
                return
            else:
                pixmap = QPixmap(file_path)
                
                # Validate that existing elements will fit in the new background
                out_of_bounds = self._validate_empire_elements_fit_background(pixmap)
                if out_of_bounds:
                    if not self._show_elements_wont_fit_dialog(out_of_bounds):
                        return  # User cancelled
                
                self.state.selected_empire_image = pixmap
                self._current_image_path = file_path  # Track the image path
        # if (not self.state.check_if_empire()) or self.state.has_any_data(): 
        #     self._ensure_new_empire_for_new_background()
            
        if pil_img:
            pixmap = self.pil_to_qpixmap(pil_img)
            
            # Validate that existing elements will fit in the new background
            out_of_bounds = self._validate_empire_elements_fit_background(pixmap)
            if out_of_bounds:
                if not self._show_elements_wont_fit_dialog(out_of_bounds):
                    return  # User cancelled
            
            self.state.selected_empire_image = pixmap
            # For PIL images, we don't have a file path unless it was loaded from _load_and_validate_empire_map
    
        self.bg_item = None
        self._clear_scene_state()
        #or self.scene.clear()
        self.no_bg_item = None
        self.bg_item = QGraphicsPixmapItem(pixmap)
        self.bg_item.setZValue(-1000)  # keep it behind markers
        self.scene.addItem(self.bg_item)
        self.scene.setSceneRect(pixmap.rect())
        self.ui.graphicsView.setEnabled(True)
        self.remove_no_background_message()
        
        # Set background type to CUSTOM if not set via dialog
        if open_dialog and not hasattr(self, '_bg_type_set_by_dialog'):
            self.bg_type = ed.EmpBackgroundTypes.CUSTOM
            self._update_default_cities_menu_state()  # Update menu state for custom background
        
        # Repopulate Default Cities menu
        self.populate_default_cities_menu()
        
        # Update empire map info with new background details
        image_path = getattr(self, '_current_image_path', None) if open_dialog else None
        self._update_empire_map_info(image_path=image_path, pixmap=pixmap)
        
        # Re-render empire elements if they exist
        if self.state.current_empire_object:
            empire = self.state.current_empire_object
            
            # Re-render cities
            if hasattr(empire, 'cities'):
                for city in empire.cities:
                    self._place_city_on_scene(city)
                    if city.trade_route is not None:
                        self.render_trade_route(city)
            
            # Re-render empire border
            if self.empire_border and empire.border:
                self.render_empire_border()
    
    def on_new_empire(self):
        """Handle the New Empire action by showing the image selection dialog."""
        # Check if we have unsaved changes
        if not self._check_before_discarding("new"):
            return
        dialog = ImageSelectionDialog(self)
        
        if dialog.exec() == QDialog.Accepted:
            selected_image = dialog.get_selected_image()
            selected_type = dialog.get_selected_image_type()
            if selected_image:
                # Load image as QPixmap to validate
                pixmap = QPixmap(selected_image)
                if pixmap.isNull():
                    QMessageBox.warning(self, "Invalid Image", 
                                       f"Could not load image file:\n{selected_image}")
                    return
                
                # Clear current empire data and set new background
                self.clear_empire_data()
                self.state.new_empire()
                # Store the current image path for later use
                self._current_image_path = selected_image
                
                # Store the pixmap and set background (same as working method)
                self.state.selected_empire_image = pixmap
                self.scene.clear()
                self.bg_item = None
                
                # Clear all trade route state when scene is cleared
                self._clear_scene_state()
                # --------the below needs to be replaced with a call to normal select background function
                self.no_bg_item = None
                self.bg_item = QGraphicsPixmapItem(pixmap)
                self.bg_type = selected_type  # Store the background type

                self.bg_item.setZValue(-1000)  # keep it behind markers
                self.scene.addItem(self.bg_item)
                self.scene.setSceneRect(pixmap.rect())
                self.ui.graphicsView.setEnabled(True)
                self.remove_no_background_message()
                # --------the above needs to be replaced with a call to normal select background function
                
                # Now update the empire with proper map info for custom backgrounds
                if selected_type != ed.EmpBackgroundTypes.LEGACY:
                    # Upgrade to version 2 and set map info
                    self.state.current_empire_object.version = 2
                    self.state.current_empire_object.map_info = ed.Map(
                        image=os.path.basename(selected_image),  # Just the filename
                        width=pixmap.width(),
                        height=pixmap.height()
                    )
                    self.state.current_empire_object.show_ireland = False  # Default setting for custom images
                else:
                    # For legacy backgrounds, keep version 1 and default show_ireland
                    self.state.current_empire_object.show_ireland = True
                
                # Repopulate Default Cities menu for new background
                self.populate_default_cities_menu()
                self._update_default_cities_menu_state()  # Update menu state based on new background
                # Update window title to indicate new file
                self.current_file_path = None
                self.has_unsaved_changes = False
                self.update_window_title()
                # Update UI state after creating new empire
                self.update_ui_state()
                
    def clear_empire_data(self):
        """Clear all current empire data for a new empire."""
        # Clear the empire data
        if self.state.current_empire_object:
            self.state.current_empire_object = None

            
        # Clear the list widget and re-add template icons
        self.ui.listWidget.clear()
        self.add_city_icons_to_list()  # Re-add the template icons
        
        # Update UI state after clearing empire
        self.update_ui_state()

    def on_empire_properties(self):
        """Handle the Empire Properties action by showing the properties dialog."""
        if not self.state or not self.state.current_empire_object:
            return  # Should not happen since button should be disabled
        
        dialog = EmpirePropertiesDialog(self)
        
        # Load current values from empire object
        empire = self.state.current_empire_object
        
        # Load border spacing
        if hasattr(empire, 'border') and empire.border is not None:
            # If border is a Border object, extract density
            if hasattr(empire.border, 'density'):
                dialog.set_border_spacing(empire.border.density)
            else:
                dialog.set_border_spacing(50)  # Default value
        else:
            # No border object, use defaults
            dialog.set_border_spacing(50)
            
        # Load show_ireland setting from empire object
        if hasattr(empire, 'show_ireland'):
            dialog.set_show_ireland(empire.show_ireland)
        else:
            dialog.set_show_ireland(False)  # Default value
        
        # Load ornaments setting (check if ornaments list is not empty)
        ornaments_enabled = bool(hasattr(empire, 'ornaments') and empire.ornaments and len(empire.ornaments) > 0)
        dialog.set_ornaments_enabled(ornaments_enabled)
        
        if dialog.exec() == QDialog.Accepted:
            # Get the values from the dialog
            border_spacing = dialog.get_border_spacing()
            show_ireland = dialog.get_show_ireland()
            ornaments_enabled = dialog.get_ornaments_enabled()
            
            # Ensure empire has a border object for border spacing
            if not hasattr(empire, 'border') or empire.border is None:
                # Create a new Border object
                empire.border = ed.Border(density=border_spacing)
            else:
                # Update existing border object
                if hasattr(empire.border, 'density'):
                    empire.border.density = border_spacing
                # If it's just a number, replace with proper Border object
                elif isinstance(empire.border, (int, float)):
                    empire.border = ed.Border(density=border_spacing)

            empire.show_ireland = show_ireland
            
            # Handle ornaments - clear if disabled, keep/add if enabled
            if ornaments_enabled:
                # If ornaments is empty and we're enabling, add a placeholder
                if not empire.ornaments:
                    empire.ornaments = [1]  # Add a default ornament value
            else:
                # Clear ornaments if disabled
                empire.ornaments = []
            
            print(f"Saved: Border spacing: {border_spacing}, Show Ireland: {show_ireland}, Ornaments: {ornaments_enabled}")
            
            # Update UI to reflect changes if needed
            self.update_ui_state()
            self.render_empire_border()  # Re-render border with new spacing

    def on_default_empire_map_selected(self):
        if "The_empire" in self.state.images:
            empire_image = self.state.images["The_empire"]
            if isinstance(empire_image, list):
                empire_image = empire_image[0]

            self.set_background_image(empire_image)
            self.bg_type = ed.EmpBackgroundTypes.LEGACY
        else:
            QMessageBox.warning(self, "Missing Map",
                                "The 'Default Empire Map' is not available in the loaded images.",
                                QMessageBox.StandardButton.Ok)

    def pil_to_qpixmap(self, pil_img):
        if pil_img.mode != "RGBA":
            pil_img = pil_img.convert("RGBA")
        w, h = pil_img.size
        data = pil_img.tobytes("raw", "RGBA")
        qimg = QImage(data, w, h, QImage.Format.Format_RGBA8888)
        return QPixmap.fromImage(qimg)


    # -------------------------------------------------------
    # New "city" drop handler (generalized), keeps old name too
    # -------------------------------------------------------
    def _add_city_to_empire(self, city, force_add=False):
        """
        Unified method to properly add a city to the empire and scene.
        Handles all necessary steps: empire list, scene placement, name labels, tracking.
        
        Args:
            city: The City object to add
            force_add: If True, always add to empire.cities. If False, only add if not already there.
        """
        # Ensure there's an empire
        if not self.state.check_if_empire():
            # Create empire and update with current background info if available
            self.state.new_empire()
            if self.bg_item and hasattr(self, '_current_image_path'):
                # Update with current background information
                pixmap = self.bg_item.pixmap()
                if self.bg_type == ed.EmpBackgroundTypes.CUSTOM:
                    self.state.current_empire_object.version = 2
                    self.state.current_empire_object.map_info = ed.Map(
                        image=os.path.basename(self._current_image_path),
                        width=pixmap.width(),
                        height=pixmap.height()
                    )
                    self.state.current_empire_object.show_ireland = False
        empire = self.state.current_empire_object
        
        # Add to empire cities list if not already there or if forced
        if force_add or city not in empire.cities:
            empire.cities.append(city)
            self.mark_unsaved_changes()  # Mark as unsaved after adding city
        
        # Place visual marker on scene
        self._place_city_on_scene(city)
        
        # Create name label if name labels are visible
        self._create_city_label(city)
        
        # Update default cities menu state
        self._update_default_cities_menu_state()
        
        return city

    def handle_city_drop(self, scene_pos):
        xy = self._scene_to_image_xy(scene_pos)
        if xy is None:
            self._show_no_background_warning()
            return
        x, y = xy

        kind = self.selected_kind
        ctype = ed.CityType(kind)

        # OUR city: single instance with move-confirmation
        if kind == ed.CityType.OURS:
            has_ours, ours = self.state.has_our_city()
            if has_ours:
                resp = self._show_move_city_dialog(ours, x, y)
                if resp == QMessageBox.StandardButton.No:
                    return
                self._remove_city_marker(ours)
                # Store center coordinates in city data
                ours.x, ours.y = x, y
                self.mark_unsaved_changes()  # Mark as unsaved after moving city
                # Use unified method to re-add the moved city
                self._add_city_to_empire(ours, force_add=False)
                return

            # Create new "Our City" with center coordinates
            ours = ed.City(name="Our City", x=x, y=y, city_type=ed.CityType.OURS, sells=[])
            self._add_city_to_empire(ours, force_add=True)
            return

        # Other city types: create freely
        
        default_name = ed.CityType(kind).value
        # Store center coordinates in city data
        # corrected
        city = ed.City(name=default_name, x=x, y=y, city_type=ctype)

        if ctype in (ed.CityType.TRADE,ed.CityType.FUTURE_TRADE):
            city.trade_route = ed.TradeRoute(cost = 500, r_type = ed.TradeRouteType.LAND)
        self._add_city_to_empire(city, force_add=True)
        self.render_trade_route(city)

    # -------------------------------------------------------
    # City Name Label Management
    # -------------------------------------------------------
    
    def _get_city_label_mode(self) -> str:
        n = self.ui.actionViewOption4.isChecked()
        t = self.ui.actionViewOption5.isChecked()
        return 'both' if n and t else ('name' if n else ('trade' if t else 'off'))
    
        
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
        buys  = ", ".join(_fmt_res(r) for r in (city.buys or []))
        trade = ("S: " + sells if sells else "") + (" | " if sells and buys else "") + ("B: " + buys if buys else "")
    
        # --- get or create the label items (idempotent) ---
        if not hasattr(self, "city_labels"):
            self.city_labels = {}
    
        item = self.city_labels.get(key)
        if item is None:
            item = QGraphicsTextItem()
            font = QFont("Bookman Old Style", pointSize=8)
            item.setFont(font)
            item.setDefaultTextColor(Qt.GlobalColor.black)
    
            bg = QGraphicsRectItem()
            bg.setBrush(QBrush(Qt.GlobalColor.white))
            bg.setPen(QPen(Qt.GlobalColor.black, 1))
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
                f"color:#000; text-align:center; margin:0;\">{esc(name_text)}</p>"
            )
        if mode in ("trade", "both") and trade_text:
            parts.append(
                f"<p style=\"font-family:'{fam}'; font-size:8pt; font-weight:400; "
                f"color:#000; text-align:center; margin:0;\">{esc(trade_text)}</p>"
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
        item.bg_rect.setRect(
            r.x() - padding,
            r.y() - padding,
            r.width() + 2 * padding,
            r.height() + 2 * padding,
        )
    
        # Preferred position (above icon, centered)
        city_item = self.city_items[key]
        city_pos, city_rect = city_item.pos(), city_item.boundingRect()
        x = city_pos.x() + city_rect.width() / 2 - r.width() / 2
        y = city_pos.y() - r.height() + 6
    
        # Overlap-avoid: bump up, else down
        def overlaps(yv: float) -> bool:
            test = QRectF(x, yv, r.width(), r.height())
            for ok, other in self.city_labels.items():
                if ok == key or not other.isVisible():
                    continue
                orr = other.boundingRect()
                op = other.pos()
                if test.intersects(QRectF(op.x(), op.y(), orr.width(), orr.height())):
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
        """Toggle visibility of all city markers."""
        visible = self.ui.actionViewOption1.isChecked()
        for item in self.city_items.values():
            try:
                item.setVisible(visible)
            except RuntimeError:
                # Item was deleted, skip
                pass
        print(f"Cities visibility: {'ON' if visible else 'OFF'}")
    
    def toggle_trade_routes_visibility(self):
        """Toggle visibility of all trade routes."""
        visible = self.ui.actionViewOption2.isChecked()
        
        # Toggle permanent trade route graphics
        if hasattr(self, 'permanent_trade_route_items'):
            for items_list in self.permanent_trade_route_items.values():
                for item in items_list:
                    try:
                        item.setVisible(visible)
                    except RuntimeError:
                        # Item was deleted, skip
                        pass
        
        # Toggle drawing state items if they exist
        if hasattr(self, 'trade_drawing_line_items'):
            for item in self.trade_drawing_line_items:
                try:
                    item.setVisible(visible)
                except RuntimeError:
                    pass
                    
        if hasattr(self, 'trade_drawing_point_items'):
            for item in self.trade_drawing_point_items:
                try:
                    item.setVisible(visible)
                except RuntimeError:
                    pass
                    
        if hasattr(self, 'trade_temp_line_item') and self.trade_temp_line_item:
            try:
                self.trade_temp_line_item.setVisible(visible)
            except RuntimeError:
                pass
                
        if hasattr(self, 'trade_route_sel_line_items'):
            for item in self.trade_route_sel_line_items:
                try:
                    item.setVisible(visible)
                except RuntimeError:
                    pass
        
        print(f"Trade routes visibility: {'ON' if visible else 'OFF'}")
    
    def toggle_border_visibility(self):
        """Toggle visibility of empire border."""
        visible = self.ui.actionViewOption3.isChecked()
        
        # Toggle border drawing items
        if hasattr(self, 'edge_line_items'):
            for item in self.edge_line_items:
                try:
                    item.setVisible(visible)
                except RuntimeError:
                    pass
                    
        if hasattr(self, 'edge_point_items'):
            for item in self.edge_point_items:
                try:
                    item.setVisible(visible)
                except RuntimeError:
                    pass
                    
        if hasattr(self, 'edge_temp_line_item') and self.edge_temp_line_item:
            try:
                self.edge_temp_line_item.setVisible(visible)
            except RuntimeError:
                pass
        
        print(f"Empire border visibility: {'ON' if visible else 'OFF'}")
    

    def update_all_city_labels_from_toggles(self):
        mode = self._get_city_label_mode()
        for city in self.state.current_empire_object.cities:
            self._apply_city_label_mode(city, mode)


                
    def align_trade_points(self, alignment_radius: int) -> int:
        """
        Snap nearby trade points (pixel units) to a shared integer coordinate.
    
        For each trade point across all cities, if it's within `alignment_radius`
        (in pixels) of a previously-seen representative, set its (x, y) exactly
        to that representative's coords. Otherwise it becomes a new representative.
    
        Returns:
            int: number of points whose coordinates changed.
        """
        # Collect a global list of all trade-point objects
        all_points = []
        for city in self.state.current_empire_object.cities:
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
        
    def refresh_map(self):
        """Refresh and re-render all map elements (F5)."""
        print("Refreshing map...")
        
        if not self.state.check_if_empire():
            print("No empire to refresh")
            return
            
        empire = self.state.current_empire_object
        
        # Clear all visual elements except background
        if self.scene and self.bg_item:
            # Remove all items except background
            
            for item in list(self.scene.items()):
                if item != self.bg_item:
                    self.scene.removeItem(item)
        self._trade_dot_reps = []
                    
        if self.state.snap_enabled:
            moved = self.align_trade_points(self.state.snap_distance)

        # Clear internal state
        self.city_items.clear()
        self.city_labels.clear()
        self._clear_scene_state()
        
        # Re-render all empire elements
        
        # 1. Re-render cities

        for city in empire.cities:
            self._place_city_on_scene(city)
            # Always create name labels (visibility will be controlled by toggle)
            self._create_city_label(city)

            # Re-render trade routes
            if city.trade_route is not None:
                self.render_trade_route(city)
        
        # 2. Re-render empire border if enabled
        if empire.border:
            self.empire_border = True
            self.render_empire_border()
        
        # 3. Update visibility states based on current toggle settings
        self.update_all_city_labels_from_toggles()
        self.toggle_cities_visibility()
        self.toggle_trade_routes_visibility()
        self.toggle_border_visibility()
        
        # 4. Repopulate Default Cities menu
        self.populate_default_cities_menu()
        if moved > 0:
            self.has_unsaved_changes = True
            QMessageBox.information(
                self, "Tradepoints aligned", f"Snapped {moved} tradepoints to their neighbours",
                QMessageBox.StandardButton.Ok
            )
        print("Map refresh completed")

    def populate_default_cities_menu(self):
        """Populate the Default Cities menu with hierarchical regions and cities from JSON."""
        try:
            # Handle PyInstaller bundle paths
            if getattr(sys, 'frozen', False):
                # Running in PyInstaller bundle
                base_path = sys._MEIPASS
            else:
                # Running in normal Python environment
                base_path = os.path.dirname(os.path.abspath(__file__))
                
            json_path = os.path.join(base_path, "augustus_assets", "Areldir_maps", "cities_grouped.json")
            
            if not os.path.exists(json_path):
                print(f"Cities JSON file not found: {json_path}")
                return
                
            with open(json_path, 'r', encoding='utf-8') as f:
                self.cities_data = json.load(f)
            
            # Clear existing menu items
            self.ui.menuDefaultCities.clear()
            # Keep track of region actions for parent-child relationships
            self.region_actions = {}
            self.city_actions = {}
            self.select_all_regions_action = None  # Store reference to main "Add all" action
            
            # Get the current background map name
            current_map_name = self._get_current_map_name()
            if not current_map_name:
                # No background set, show message
                no_bg_action = QAction("No background set - select a background first", self)
                no_bg_action.setEnabled(False)
                self.ui.menuDefaultCities.addAction(no_bg_action)
                return
            
            select_all_regions_action = QAction("Add all", self)
            select_all_regions_action.setCheckable(True)
            
            # Create region menus with cities
            for region_name, cities in self.cities_data.items():
                # Check if any cities in this region have coordinates for current map
                available_cities = []
                for city_name, city_data in cities.items():
                    map_data = city_data.get("default_map", {}).get(current_map_name)
                    if map_data:
                        # Check if city coordinates fit within current background bounds
                        if self._city_fits_on_current_background(map_data.get("x"), map_data.get("y")):
                            available_cities.append((city_name, city_data))
                # Only create region menu if it has cities for current map
                if not available_cities:
                    continue
                    
                # Create region submenu
                region_menu = self.ui.menuDefaultCities.addMenu(region_name)
                
                # Create a "Select All" action for the region
                select_all_action = QAction(f"Select All {region_name}", self)
                select_all_action.setCheckable(True)
                select_all_action.triggered.connect(
                    lambda checked, region=region_name: self.on_region_select_all(region, checked)
                )
                region_menu.addAction(select_all_action)
                self.region_actions[region_name] = select_all_action
                
                # Add separator
                region_menu.addSeparator()
                
                # Add individual city actions (only for available cities)
                region_city_actions = []
                for city_name, city_data in available_cities:
                    city_action = QAction(city_name, self)
                    city_action.setCheckable(True)
                    city_action.triggered.connect(
                        lambda checked, city=city_name, region=region_name: 
                        self.on_city_selected(region, city, checked)
                    )
                    region_menu.addAction(city_action)
                    region_city_actions.append(city_action)
                
                self.city_actions[region_name] = region_city_actions
            
            # Add "Add all" action at the top if there are any regions
            if self.region_actions:
                select_all_regions_action.triggered.connect(self.on_select_all_regions)
                self.select_all_regions_action = select_all_regions_action  # Store reference
                # Insert at the beginning of the menu
                acts = self.ui.menuDefaultCities.actions()
                if acts:
                    self.ui.menuDefaultCities.insertAction(acts[0], select_all_regions_action)
                else:
                    self.ui.menuDefaultCities.addAction(select_all_regions_action)
                
                # Add a separator after the "Add all" action
                self.ui.menuDefaultCities.addSeparator()
                    
        except Exception as e:
            print(f"Error populating Default Cities menu: {e}")
    
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
                return ed.EmpBackgroundTypes.CUSTOM  #
            else:
                return ed.EmpBackgroundTypes.NONE
    

    def _city_fits_on_current_background(self, x, y):
        """Check if city coordinates fit within current background image bounds."""
        if x is None or y is None:
            return False
        
        if not self.bg_item:
            return True  # No background set, allow all
        
        # Get background image dimensions
        pixmap = self.bg_item.pixmap()
        if pixmap.isNull():
            return True
        
        bg_width = pixmap.width()
        bg_height = pixmap.height()
        
        # Check if coordinates are within bounds (with some margin for city icon size)
        margin = 50  # Allow some margin for city icon
        return (x >= 0 and x < bg_width - margin and 
                y >= 0 and y < bg_height - margin)

    
    def on_select_all_regions(self, checked):
        """Handle the top-level "Add all" checkbox that selects/deselects all regions and cities."""
        # Toggle all region "Select All" actions
        for region_name in self.region_actions:
            region_action = self.region_actions[region_name]
            region_action.setChecked(checked)
            # This will trigger the region's select all logic
            self.on_region_select_all(region_name, checked)
    
    def on_region_select_all(self, region_name, checked):
        """Handle region "Select All" checkbox."""
        if region_name in self.city_actions:
            for city_action in self.city_actions[region_name]:
                city_action.setChecked(checked)
                # Also trigger the city selection logic
                city_name = city_action.text()
                self.on_city_selected(region_name, city_name, checked)
    
    def on_city_selected(self, region_name, city_name, checked):
        """Handle individual city selection."""
        print(f"City {city_name} in {region_name}: {'selected' if checked else 'deselected'}")
        
        # Update region "Select All" state based on individual city states
        if region_name in self.city_actions and region_name in self.region_actions:
            region_action = self.region_actions[region_name]
            city_actions = self.city_actions[region_name]
            
            # Check if all cities are selected
            all_selected = all(action.isChecked() for action in city_actions)
            
            # Update region action state
            region_action.setChecked(all_selected)
        
        # Update the main "Add all" action state
        self._update_main_select_all_state()
        
        # Place or remove the city on the map
        if checked:
            self._place_default_city(region_name, city_name)
        else:
            self._remove_default_city(region_name, city_name)
    
    def _update_main_select_all_state(self):
        """Update the main 'Add all' action state based on all region states."""
        if not hasattr(self, 'select_all_regions_action') or self.select_all_regions_action is None:
            return
            
        # Check if all region "Select All" actions are checked
        all_regions_selected = all(region_action.isChecked() for region_action in self.region_actions.values())
        
        # Update the main action state
        self.select_all_regions_action.setChecked(all_regions_selected)
    
    # -------------------------------------------------------
    # Non-city handler(s)
    # -------------------------------------------------------


if __name__ == "__main__":
    
    app = QApplication.instance() or QApplication([])
    window = MainWindow()
    # One global filter to observe ALL widgets
    app.installEventFilter(window)
    if not window.init_failed:
        window.show()
        sys.exit(app.exec())
    sys.exit(0)
