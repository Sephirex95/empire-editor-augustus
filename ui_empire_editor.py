# ui_empire_editor.py
from PySide6.QtCore import Qt, QCoreApplication
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QWidget, QListWidget, QGraphicsView,
    QMenuBar, QMenu, QStatusBar, QSplitter, QHBoxLayout, QLabel
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

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        self.graphicsView = EmpireMapView()
        self.graphicsView.setMinimumWidth(400)
        splitter.addWidget(self.graphicsView)

        self.listWidget = QListWidget()
        self.listWidget.setMinimumWidth(400)
        self.listWidget.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.listWidget.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.listWidget.setWordWrap(True)
        self.listWidget.setUniformItemSizes(False)
        self.listWidget.setTextElideMode(Qt.ElideNone)
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
