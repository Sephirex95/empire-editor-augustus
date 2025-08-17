# ui_empire_editor.py
import os
import sys
from pathlib import Path
import empire_data as ed
from PySide6.QtCore import Qt, QCoreApplication, QSize
from PySide6.QtGui import QAction, QPixmap, QIcon
from PySide6.QtWidgets import (
    QWidget, QListWidget, QGraphicsView,
    QMenuBar, QMenu, QStatusBar, QSplitter, QHBoxLayout, QLabel,
    QDialog, QVBoxLayout, QPushButton, QListWidgetItem, QFileDialog,
    QMessageBox, QSpinBox, QCheckBox, QDialogButtonBox
)

class EmpireMapView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1920, 920)
        MainWindow.setMinimumWidth(900)

        # ---- Actions ----
        self.actionNew  = QAction(MainWindow); self.actionNew.setObjectName("actionNew")
        self.actionNew.setShortcut("Ctrl+N")

        self.actionOpen = QAction(MainWindow); self.actionOpen.setObjectName("actionOpen")
        self.actionOpen.setShortcut("Ctrl+O")

        self.actionSave = QAction(MainWindow); self.actionSave.setObjectName("actionSave")
        self.actionSave.setShortcut("Ctrl+S")

        self.actionSelect_background_Image = QAction(MainWindow)
        self.actionSelect_background_Image.setObjectName("actionSelect_background_Image")

        self.actionEmpireProperties = QAction(MainWindow)
        self.actionEmpireProperties.setObjectName("actionEmpireProperties")

        self.actionOptions = QAction(MainWindow); self.actionOptions.setObjectName("actionOptions")
        self.actionAbout   = QAction(MainWindow); self.actionAbout.setObjectName("actionAbout")

        self.actionViewOption1 = QAction(MainWindow)
        self.actionViewOption1.setObjectName("actionViewOption1")
        self.actionViewOption1.setCheckable(True)
        self.actionViewOption1.setChecked(True)

        self.actionViewOption2 = QAction(MainWindow)
        self.actionViewOption2.setObjectName("actionViewOption2")
        self.actionViewOption2.setCheckable(True)
        self.actionViewOption2.setChecked(True)

        self.actionViewOption3 = QAction(MainWindow)
        self.actionViewOption3.setObjectName("actionViewOption3")
        self.actionViewOption3.setCheckable(True)
        self.actionViewOption3.setChecked(True)

        self.actionViewOption4 = QAction(MainWindow)
        self.actionViewOption4.setObjectName("actionViewOption4")
        self.actionViewOption4.setCheckable(True)
        self.actionViewOption4.setChecked(False)  # Off by default

        self.actionRefreshMap = QAction(MainWindow)
        self.actionRefreshMap.setObjectName("actionRefreshMap")
        self.actionRefreshMap.setShortcut("F5")

        # GitHub submenu actions
        self.actionGitHub_Augustus = QAction(MainWindow); self.actionGitHub_Augustus.setObjectName("actionGitHub_Augustus")
        self.actionGitHub_Editor   = QAction(MainWindow); self.actionGitHub_Editor.setObjectName("actionGitHub_Editor")
        self.actionGitHub_Custom   = QAction(MainWindow); self.actionGitHub_Custom.setObjectName("actionGitHub_Custom")

        # ---- Central widget / layout ----
        self.centralwidget = QWidget(MainWindow)
        MainWindow.setCentralWidget(self.centralwidget)

        layout = QHBoxLayout(self.centralwidget)
        layout.setContentsMargins(10, 10, 10, 10)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        self.graphicsView = EmpireMapView()
        self.graphicsView.setMinimumWidth(400)
        splitter.addWidget(self.graphicsView)

        self.listWidget = QListWidget()
        self.listWidget.setMinimumWidth(400)
        self.listWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.listWidget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.listWidget.setWordWrap(True)
        self.listWidget.setUniformItemSizes(False)
        self.listWidget.setTextElideMode(Qt.TextElideMode.ElideNone)
        splitter.addWidget(self.listWidget)

        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)
        splitter.setSizes([MainWindow.width() - 400, 400])

        # ---- Menu bar / status bar ----
        self.menubar = QMenuBar(MainWindow)
        MainWindow.setMenuBar(self.menubar)

        self.menuFile = QMenu(self.menubar); self.menuFile.setObjectName("menuFile")
        self.menuEmpireProperties = QMenu(self.menubar); self.menuEmpireProperties.setObjectName("menuEmpireProperties")
        self.menuDefaultCities = QMenu(self.menubar); self.menuDefaultCities.setObjectName("menuDefaultCities")
        self.menuView = QMenu(self.menubar); self.menuView.setObjectName("menuView")
        self.menuSettings = QMenu(self.menubar); self.menuSettings.setObjectName("menuSettings")
        self.menuSettings.setEnabled(False)  # Disabled by default
        self.menuHelp = QMenu(self.menubar); self.menuHelp.setObjectName("menuHelp")
        self.menuGitHub = QMenu(self.menuHelp); self.menuGitHub.setObjectName("menuGitHub")

        self.statusbar = QStatusBar(MainWindow)
        MainWindow.setStatusBar(self.statusbar)

        self.mouse_position_label = QLabel("Mouse Position: (0, 0)")
        self.mouse_position_label.setObjectName("mousePositionLabel")
        self.statusbar.addWidget(self.mouse_position_label)

        # ---- Build menus ----
        # File
        self.menuFile.addAction(self.actionNew)
        self.menuFile.addAction(self.actionOpen)
        self.menuFile.addAction(self.actionSave)

        # Empire properties
        self.menuEmpireProperties.addAction(self.actionSelect_background_Image)
        self.menuEmpireProperties.addAction(self.actionEmpireProperties)

        # View
        self.menuView.addAction(self.actionViewOption1)
        self.menuView.addAction(self.actionViewOption2)
        self.menuView.addAction(self.actionViewOption3)
        self.menuView.addAction(self.actionViewOption4)
        self.menuView.addSeparator()
        self.menuView.addAction(self.actionRefreshMap)
        # Settings
        self.menuSettings.addAction(self.actionOptions)

        # Help + GitHub submenu
        self.menuGitHub.addAction(self.actionGitHub_Augustus)
        self.menuGitHub.addAction(self.actionGitHub_Editor)
        self.menuGitHub.addAction(self.actionGitHub_Custom)
        self.menuHelp.addMenu(self.menuGitHub)
        self.menuHelp.addSeparator()
        self.menuHelp.addAction(self.actionAbout)

        # Add top-level menus to menubar
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuEmpireProperties.menuAction())
        self.menubar.addAction(self.menuDefaultCities.menuAction())
        self.menubar.addAction(self.menuView.menuAction())
        self.menubar.addAction(self.menuSettings.menuAction())
        self.menubar.addAction(self.menuHelp.menuAction())

        # No auto-connects here (we're wiring in main_window.py)
        self.retranslateUi(MainWindow)
    def retranslateUi(self, MainWindow):
        _t = QCoreApplication.translate
        MainWindow.setWindowTitle(_t("MainWindow", "Empire Editor", None))

        # Menus
        self.menuFile.setTitle(_t("MainWindow", "File", None))
        self.menuEmpireProperties.setTitle(_t("MainWindow", "Empire properties", None))
        self.menuView.setTitle(_t("MainWindow", "View", None))
        self.menuDefaultCities.setTitle(_t("MainWindow", "Default Cities", None))
        self.menuDefaultCities.setEnabled(False)  # Disabled by default
        self.menuSettings.setTitle(_t("MainWindow", "Settings", None))
        self.menuHelp.setTitle(_t("MainWindow", "Help", None))
        self.menuGitHub.setTitle(_t("MainWindow", "GitHub", None))

        # Actions
        self.actionNew.setText(_t("MainWindow", "New", None))
        self.actionOpen.setText(_t("MainWindow", "Open Empire XML", None))
        self.actionSave.setText(_t("MainWindow", "Save Empire XML", None))
        self.actionSelect_background_Image.setText(_t("MainWindow", "Select background Image", None))
        self.actionEmpireProperties.setText(_t("MainWindow", "Empire Properties", None))
        self.actionOptions.setText(_t("MainWindow", "Options…", None))
        self.actionAbout.setText(_t("MainWindow", "About", None))
        
        # View options
        self.actionViewOption1.setText(_t("MainWindow", "Show Cities", None))
        self.actionViewOption2.setText(_t("MainWindow", "Show Trade Routes", None))
        self.actionViewOption3.setText(_t("MainWindow", "Show Empire Border", None))
        self.actionViewOption4.setText(_t("MainWindow", "Show Name Labels", None))
        self.actionRefreshMap.setText(_t("MainWindow", "Refresh Map", None))
        
        self.actionGitHub_Augustus.setText(_t("MainWindow", "Augustus", None))
        self.actionGitHub_Editor.setText(_t("MainWindow", "Augustus Empire Editor", None))
        self.actionGitHub_Custom.setText(_t("MainWindow", "Custom Empires", None))


class ImageSelectionDialog(QDialog):
    """Modal dialog for selecting background images for new empire files."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Empire Map Background")
        self.setModal(True)
        self.setMinimumSize(600, 400)
        self.resize(600, 400)
        self.selected_type = ""
        # Store the selected image path
        self.selected_image_path = None
        # Store the selected image type
        self.selected_image_type = None
        
        # Default images (use absolute paths)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.default_images = [
            (os.path.join(base_dir, "augustus_assets", "Areldir_maps", "Orbis_Terrarum_Empire_Map.png"), ed.EmpBackgroundTypes.BIG_MAP),
            (os.path.join(base_dir, "augustus_assets", "Areldir_maps", "Occidentalis_Empire_Map.png"), ed.EmpBackgroundTypes.NORTH_MAP),
            (os.path.join(base_dir, "augustus_assets", "Areldir_maps", "Orientalis_Empire_Map.png"), ed.EmpBackgroundTypes.SOUTH_MAP),
        ]
        
        self.setup_ui()
        self.populate_image_list()
        
    def setup_ui(self):
        """Create the UI layout."""
        layout = QVBoxLayout(self)
        
        # Create horizontal splitter for list and preview
        splitter = QSplitter(Qt.Orientation.Horizontal)
        layout.addWidget(splitter)
        
        # Left side: Image list
        left_widget = QWidget()
        left_widget.setMinimumWidth(250)  # Prevent hiding the list
        left_layout = QVBoxLayout(left_widget)
        
        self.image_list = QListWidget()
        self.image_list.setMaximumWidth(300)
        self.image_list.setMinimumWidth(200)  # Ensure minimum visibility
        
        # Increase font size for better readability
        font = self.image_list.font()
        font.setPointSize(font.pointSize() + 2)  # Increase by 2 points
        self.image_list.setFont(font)
        
        self.image_list.currentRowChanged.connect(self.on_selection_changed)
        left_layout.addWidget(QLabel("Available Empire Maps:"))
        left_layout.addWidget(self.image_list)
        
        # Custom image button
        self.custom_button = QPushButton("Select Custom Image...")
        self.custom_button.clicked.connect(self.select_custom_image)
        left_layout.addWidget(self.custom_button)
        
        splitter.addWidget(left_widget)
        
        # Right side: Preview
        right_widget = QWidget()
        right_widget.setMinimumWidth(300)  # Prevent hiding the preview
        right_layout = QVBoxLayout(right_widget)
        
        right_layout.addWidget(QLabel("Preview:"))
        self.preview_label = QLabel()
        self.preview_label.setMinimumSize(400, 300)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("border: 1px solid gray; background-color: transparent;")
        self.preview_label.setText("Select an image to preview")
        right_layout.addWidget(self.preview_label)
        
        splitter.addWidget(right_widget)
        
        # Set splitter proportions and ensure panels can't be completely hidden
        splitter.setCollapsible(0, False)  # Left panel cannot be collapsed
        splitter.setCollapsible(1, False)  # Right panel cannot be collapsed
        splitter.setSizes([300, 500])
        
        # Bottom buttons
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setEnabled(False)  # Disabled until selection is made
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(cancel_button)
        
        layout.addLayout(button_layout)
        
    def populate_image_list(self):
        """Populate the list with default images."""
        self.image_list.clear()
        
        for (image_path, img_type) in self.default_images:
            # Create display name from filename
            if image_path and os.path.exists(image_path):
                display_name = os.path.basename(image_path).replace('_', ' ').replace('.png', '')
                item = QListWidgetItem(display_name)
                # Store both path and type as a tuple in UserRole
                item.setData(Qt.ItemDataRole.UserRole, (image_path, img_type))
                self.image_list.addItem(item)
    
    def on_selection_changed(self, current_row):
        """Handle selection change in the image list."""
        if current_row >= 0:
            item = self.image_list.item(current_row)
            if item:
                data = item.data(Qt.ItemDataRole.UserRole)
                if isinstance(data, tuple) and len(data) == 2:
                    # New format: (image_path, img_type)
                    image_path, img_type = data
                    self.selected_image_path = image_path
                    self.selected_image_type = img_type
                else:
                    # Legacy format: just image_path (for custom images)
                    self.selected_image_path = data
                    self.selected_image_type = ed.EmpBackgroundTypes.CUSTOM
                self.update_preview(self.selected_image_path)
                self.ok_button.setEnabled(True)
        else:
            self.ok_button.setEnabled(False)
            self.selected_image_path = None
            self.selected_image_type = None
            self.preview_label.setText("Select an image to preview")
    
    def update_preview(self, image_path):
        """Update the preview with the selected image."""
        if not image_path or not os.path.exists(image_path):
            self.preview_label.setText("Image not found:\n" + str(image_path))
            return
            
        try:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                self.preview_label.setText("Failed to load image")
                return
                
            # Scale pixmap to fit preview area while maintaining aspect ratio
            preview_size = self.preview_label.size()
            scaled_pixmap = pixmap.scaled(
                preview_size.width() - 10, 
                preview_size.height() - 10, 
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_label.setPixmap(scaled_pixmap)
            
        except Exception as e:
            self.preview_label.setText(f"Error loading image:\n{str(e)}")
    
    def select_custom_image(self):
        """Open file dialog to select a custom image."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Custom Empire Map Image",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif *.tiff);;All Files (*)"
        )
        
        if file_path:
            # Add custom image to the list
            display_name = f"Custom: {os.path.basename(file_path)}"
            item = QListWidgetItem(display_name)
            # Store just the path for custom images (no type)
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            self.image_list.addItem(item)
            
            # Select the newly added item
            self.image_list.setCurrentItem(item)
            
    def get_selected_image(self):
        """Return the path of the selected image."""
        return self.selected_image_path
    
    def get_selected_image_type(self):
        """Return the type of the selected image."""
        return self.selected_image_type


class EmpirePropertiesDialog(QDialog):
    """Modal dialog for configuring empire properties."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Empire Properties")
        self.setModal(True)
        self.setMinimumSize(300, 250)
        self.resize(350, 300)  # Narrower dialog
        
        # Store parent reference for checking map state
        self.main_window = parent
        
        # Store original values for cancel functionality
        self.original_border_spacing = 50  # Default to 50
        self.original_ornaments_enabled = True
        self.original_show_ireland = False
        
        self.setup_ui()
        self.update_ornaments_state()  # Set initial state based on map
        
    def setup_ui(self):
        """Create the UI layout."""
        layout = QVBoxLayout(self)
        
        # Properties group
        properties_group = QWidget()
        properties_layout = QVBoxLayout(properties_group)
        
        # Border spacing
        border_layout = QHBoxLayout()
        border_layout.addWidget(QLabel("Border Spacing:"))
        self.border_spacing_spinbox = QSpinBox()
        self.border_spacing_spinbox.setRange(0, 100)
        self.border_spacing_spinbox.setValue(50)  # Default value set to 50 as per border class
        self.border_spacing_spinbox.setSuffix(" px")
        border_layout.addWidget(self.border_spacing_spinbox)
        border_layout.addStretch()
        properties_layout.addLayout(border_layout)
        
        # Ornaments checkbox
        self.ornaments_checkbox = QCheckBox("Enable Ornaments")
        properties_layout.addWidget(self.ornaments_checkbox)
        
        # Show Ireland checkbox
        self.show_ireland_checkbox = QCheckBox("Show Ireland")
        properties_layout.addWidget(self.show_ireland_checkbox)
        
        layout.addWidget(properties_group)
        layout.addStretch()
        
        # Bottom area with legacy button and main buttons
        bottom_layout = QVBoxLayout()
        
        # Legacy button in corner (smaller)
        legacy_layout = QHBoxLayout()
        self.legacy_button = QPushButton("Legacy BG")
        self.legacy_button.setMaximumWidth(80)  # Make it smaller
        self.legacy_button.setToolTip("Set Legacy Background")  # Tooltip for clarity
        self.legacy_button.clicked.connect(self.set_legacy_background)
        legacy_layout.addWidget(self.legacy_button)
        legacy_layout.addStretch()  # Push to left corner
        bottom_layout.addLayout(legacy_layout)
        
        # Main OK/Cancel buttons
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.cancel_and_restore)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(cancel_button)
        
        bottom_layout.addLayout(button_layout)
        layout.addLayout(bottom_layout)
    
    def set_legacy_background(self):
        """Handle the set legacy background button click with warning."""
        # Show warning message
        reply = QMessageBox.question(
            self, 
            "Set Legacy Background", 
            "This will replace the current background with the default empire map. "
            "Any unsaved changes may be lost. Do you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Call the parent's on_default_empire_map_selected method
            if self.main_window and hasattr(self.main_window, 'on_default_empire_map_selected'):
                self.main_window.on_default_empire_map_selected()
                # Update ornaments state after setting legacy background
                self.update_ornaments_state()
                self.accept()
    
    def update_ornaments_state(self):
        """Update ornaments and show_ireland checkbox state based on map properties."""
        if self.main_window:
            # Check if empire.map_info is not None
            has_map_info = False
            if hasattr(self.main_window, 'state') and self.main_window.state:
                if hasattr(self.main_window.state, 'current_empire_object') and self.main_window.state.current_empire_object:
                    empire = self.main_window.state.current_empire_object
                    if hasattr(empire, 'map_info') and empire.map_info is not None:
                        has_map_info = True
            
            # Disable checkboxes if empire.map_info != None
            if has_map_info:
                self.ornaments_checkbox.setEnabled(False)
                self.show_ireland_checkbox.setEnabled(False)
            else:
                self.ornaments_checkbox.setEnabled(True)
                self.show_ireland_checkbox.setEnabled(True)
                
            # Set default states (ornaments enabled, show_ireland disabled by default)
            self.ornaments_checkbox.setChecked(not has_map_info)
            self.show_ireland_checkbox.setChecked(False)
        else:
            # Fallback: enable all controls if no parent reference
            self.ornaments_checkbox.setEnabled(True)
            self.show_ireland_checkbox.setEnabled(True)
            self.ornaments_checkbox.setChecked(True)
            self.show_ireland_checkbox.setChecked(False)
    
    def get_border_spacing(self):
        """Return the selected border spacing value."""
        return self.border_spacing_spinbox.value()
    
    def get_ornaments_enabled(self):
        """Return whether ornaments are enabled."""
        return self.ornaments_checkbox.isChecked()
    
    def get_show_ireland(self):
        """Return whether show Ireland is enabled."""
        return self.show_ireland_checkbox.isChecked()
    
    def set_border_spacing(self, value):
        """Set the border spacing value and store original."""
        self.original_border_spacing = value
        self.border_spacing_spinbox.setValue(value)
    
    def set_ornaments_enabled(self, enabled):
        """Set whether ornaments are enabled and store original."""
        self.original_ornaments_enabled = enabled
        self.ornaments_checkbox.setChecked(enabled)
    
    def set_show_ireland(self, enabled):
        """Set whether show Ireland is enabled and store original."""
        self.original_show_ireland = enabled
        self.show_ireland_checkbox.setChecked(enabled)
    
    def restore_original_values(self):
        """Restore original values for cancel functionality."""
        self.border_spacing_spinbox.setValue(self.original_border_spacing)
        self.ornaments_checkbox.setChecked(self.original_ornaments_enabled)
        self.show_ireland_checkbox.setChecked(self.original_show_ireland)
    
    def cancel_and_restore(self):
        """Cancel dialog and restore original values."""
        self.restore_original_values()
        self.reject()


def _find_editor_icon() -> Path | None:
    """Try _internal/editor.ico (PyInstaller), then local fallbacks."""
    base = Path(getattr(sys, "_MEIPASS", Path(sys.argv[0]).resolve().parent))
    candidates = [
        base / "_internal" / "editor.ico",  # PyInstaller onedir with contents_directory
        base / "editor.ico",
        Path("editor.ico"),
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def show_about_dialog(parent=None):
    dlg = QDialog(parent)
    dlg.setWindowTitle("About Empire Editor")
    dlg.setModal(True)
    dlg.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

    icon_path = _find_editor_icon()
    if icon_path:
        dlg.setWindowIcon(QIcon(str(icon_path)))        # Layout: icon on the left, rich text on the right
        layout = QVBoxLayout(dlg)
        top = QHBoxLayout()
        layout.addLayout(top)

        # Icon preview (optional)
        if icon_path:
            icon_lbl = QLabel(dlg)
            pm = QPixmap(str(icon_path))
            if not pm.isNull():
                # scale to a nice size; keeps aspect ratio
                pm = pm.scaled(64, 64, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_lbl.setPixmap(pm)
            icon_lbl.setAlignment(Qt.AlignTop | Qt.AlignLeft)
            top.addWidget(icon_lbl)

        # Rich text
        text_lbl = QLabel(dlg)
        text_lbl.setTextFormat(Qt.RichText)
        text_lbl.setOpenExternalLinks(True)
        text_lbl.setWordWrap(True)
        text_lbl.setText(
            """<b>Empire Editor for Augustus</b> by <b>Sephirex95</b><br>
            <a href="https://github.com/Sephirex95/empire-editor-augustus">
            https://github.com/Sephirex95/empire-editor-augustus</a><br><br>

            Sgreader code is a Python conversion of the citybuilding tools by <b>Bianca 'bvschaik' van Schaik</b>, author 
            of <a href="https://github.com/bvschaik/julius">Julius</a> and founder of the community:<br>
            <a href="https://github.com/bvschaik/citybuilding-tools">https://github.com/bvschaik/citybuilding-tools</a><br><br>

            Enormous thanks to <b>Areldir</b> for making and generously sharing the beautiful Empire maps used in this editor.<br><br>

            Vanilla assets extracted at runtime from <i>Caesar III</i> by Impressions Games,
            published by Sierra Studios (Activision).<br><br>

            Huge thanks also to <b>Destinationwalker</b>, <b>CommissarMarek</b> and <b>Turgon</b>
            who consulted on the usage of the XML logic, and PrettyFlower who authored the original code for custom empires.<br><br>
            
            Finally a big thank you to the entire Augustus community and dev team for their support and contributions, big and small.<br><br>
            
            Made using <b>PySide6</b> (Qt for Python). PySide6 and Qt are available under the
            <a href="https://www.gnu.org/licenses/lgpl-3.0.html">GNU LGPL v3</a>.<br>
            &copy; The Qt Company Ltd and other contributors. License texts and source:
            <a href="https://code.qt.io/pyside/pyside-setup">code.qt.io/pyside/pyside-setup</a>,
            <a href="https://www.qt.io/terms-conditions/license/">qt.io/terms-conditions/license/</a>.<br>
            This application dynamically links to PySide6/Qt. Under the LGPL v3, you may replace or
            relink those libraries with a modified version; reverse engineering is permitted for
            debugging such modifications."""
        )
        top.addWidget(text_lbl, 1)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok, parent=dlg)
        buttons.accepted.connect(dlg.accept)
        layout.addWidget(buttons)

        dlg.resize(580, 380)
        dlg.exec()