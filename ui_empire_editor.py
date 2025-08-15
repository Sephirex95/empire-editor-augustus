# ui_empire_editor.py
import os
from PyQt6.QtCore import Qt, QCoreApplication, QSize
from PyQt6.QtGui import QAction, QPixmap
from PyQt6.QtWidgets import (
    QWidget, QListWidget, QGraphicsView,
    QMenuBar, QMenu, QStatusBar, QSplitter, QHBoxLayout, QLabel,
    QDialog, QVBoxLayout, QPushButton, QListWidgetItem, QFileDialog,
    QMessageBox
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

        self.actionDefaultEmpireMap = QAction(MainWindow)
        self.actionDefaultEmpireMap.setObjectName("actionDefaultEmpireMap")

        self.actionOptions = QAction(MainWindow); self.actionOptions.setObjectName("actionOptions")
        self.actionAbout   = QAction(MainWindow); self.actionAbout.setObjectName("actionAbout")

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
        self.menuSettings = QMenu(self.menubar); self.menuSettings.setObjectName("menuSettings")
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
        self.menuEmpireProperties.addAction(self.actionDefaultEmpireMap)

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
        self.menuSettings.setTitle(_t("MainWindow", "Settings", None))
        self.menuHelp.setTitle(_t("MainWindow", "Help", None))
        self.menuGitHub.setTitle(_t("MainWindow", "GitHub", None))

        # Actions
        self.actionNew.setText(_t("MainWindow", "New", None))
        self.actionOpen.setText(_t("MainWindow", "Open Empire XML", None))
        self.actionSave.setText(_t("MainWindow", "Save Empire XML", None))
        self.actionSelect_background_Image.setText(_t("MainWindow", "Select background Image", None))
        self.actionDefaultEmpireMap.setText(_t("MainWindow", "Default Empire Map", None))
        self.actionOptions.setText(_t("MainWindow", "Options…", None))
        self.actionAbout.setText(_t("MainWindow", "About", None))
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
        
        # Store the selected image path
        self.selected_image_path = None
        
        # Default images (use absolute paths)
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.default_images = [
            os.path.join(base_dir, "augustus_assets", "Areldir_maps", "Orbis_Terrarum_Empire_Map.png"),
            os.path.join(base_dir, "augustus_assets", "Areldir_maps", "Occidentalis_Empire_Map.png"),
            os.path.join(base_dir, "augustus_assets", "Areldir_maps", "Orientalis_Empire_Map.png"),
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
        
        for image_path in self.default_images:
            # Create display name from filename
            if image_path and os.path.exists(image_path):
                display_name = os.path.basename(image_path).replace('_', ' ').replace('.png', '')
                item = QListWidgetItem(display_name)
                item.setData(Qt.ItemDataRole.UserRole, image_path)  # Store full path
                self.image_list.addItem(item)
    
    def on_selection_changed(self, current_row):
        """Handle selection change in the image list."""
        if current_row >= 0:
            item = self.image_list.item(current_row)
            if item:
                image_path = item.data(Qt.ItemDataRole.UserRole)
                self.selected_image_path = image_path
                self.update_preview(image_path)
                self.ok_button.setEnabled(True)
        else:
            self.ok_button.setEnabled(False)
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
            item.setData(Qt.ItemDataRole.UserRole, file_path)
            self.image_list.addItem(item)
            
            # Select the newly added item
            self.image_list.setCurrentItem(item)
            
    def get_selected_image(self):
        """Return the path of the selected image."""
        return self.selected_image_path
