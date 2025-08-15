#ui_empire_editor.py
from PySide6.QtCore import Qt, QCoreApplication, QMetaObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QListWidget, QGraphicsView,
    QMenuBar, QMenu, QStatusBar, QSplitter, QHBoxLayout, QLabel
)

class EmpireMapView(QGraphicsView):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)  # no label updates here

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1920, 920)
        MainWindow.setMinimumWidth(900)  # 400 + 400 + some room
    
        # Actions
        self.actionOpen = QAction(MainWindow)
        self.actionOpen.setShortcut("Ctrl+O")  # Standard Open shortcut
        self.actionSave = QAction(MainWindow)
        self.actionSave.setShortcut("Ctrl+S")  # Standard Save shortcut
        self.actionSelect_background_Image = QAction(MainWindow)
        
        # Add the "Default Empire Map" action
        self.actionDefaultEmpireMap = QAction(MainWindow)

        # Central widget
        self.centralwidget = QWidget(MainWindow)
        MainWindow.setCentralWidget(self.centralwidget)
    
        # Layout
        layout = QHBoxLayout(self.centralwidget)
        layout.setContentsMargins(10, 10, 10, 10)
    
        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)
    
        # Graphics view setup
        self.graphicsView = EmpireMapView()
        self.graphicsView.setMinimumWidth(400)
        splitter.addWidget(self.graphicsView)
    
        # Sidebar setup
        self.listWidget = QListWidget()
        self.listWidget.setMinimumWidth(400)
        self.listWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.listWidget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.listWidget.setWordWrap(True)
        self.listWidget.setUniformItemSizes(False)
        self.listWidget.setTextElideMode(Qt.ElideNone)  # Don’t cut off text
        splitter.addWidget(self.listWidget)
    
        # Clamp sidebar width and set initial layout proportions
        splitter.setCollapsible(0, False)  # Don't allow graphicsView to be collapsed
        splitter.setCollapsible(1, False)  # Don't allow sidebar to collapse
        splitter.setSizes([MainWindow.width() - 400, 400])  # Default width for sidebar
    
        # Menu bar and status bar
        self.menubar = QMenuBar(MainWindow)
        self.menuEmpire_editor_augustus = QMenu(self.menubar)
        self.menuMap_Settings = QMenu(self.menubar)
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        MainWindow.setStatusBar(self.statusbar)
    
        # Add label to the status bar for mouse position
        self.mouse_position_label = QLabel("Mouse Position: (0, 0)")
        self.mouse_position_label.setObjectName("mousePositionLabel")
        self.statusbar.addWidget(self.mouse_position_label)  # left side


        # Build menu
        self.menuEmpire_editor_augustus.addAction(self.actionOpen)
        self.menuEmpire_editor_augustus.addAction(self.actionSave)
        self.menuMap_Settings.addAction(self.actionSelect_background_Image)
        self.menuMap_Settings.addAction(self.actionDefaultEmpireMap)  # Add new action here
        self.menubar.addAction(self.menuEmpire_editor_augustus.menuAction())
        self.menubar.addAction(self.menuMap_Settings.menuAction())
    
        # Connect the new action to the method that handles it
        #self.actionDefaultEmpireMap.triggered.connect(MainWindow.on_default_empire_map_selected)

        # Re-translate the UI elements (for localization)
        self.retranslateUi(MainWindow)
        QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", "MainWindow", None))
        self.actionOpen.setText(QCoreApplication.translate("MainWindow", "Open Empire XML", None))
        self.actionSave.setText(QCoreApplication.translate("MainWindow", "Save Empire XML", None))
        self.actionSelect_background_Image.setText(QCoreApplication.translate("MainWindow", "Select background Image", None))
        self.menuEmpire_editor_augustus.setTitle(QCoreApplication.translate("MainWindow", "File", None))
        self.menuMap_Settings.setTitle(QCoreApplication.translate("MainWindow", "Map Settings", None))
        
        # Set text for the new "Default Empire Map" action
        self.actionDefaultEmpireMap.setText(QCoreApplication.translate("MainWindow", "Default Empire Map", None))

