from PySide6.QtCore import Qt, QCoreApplication, QMetaObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QListWidget, QGraphicsView,
    QMenuBar, QMenu, QStatusBar, QSplitter, QHBoxLayout
)


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1920, 931)
        MainWindow.setMinimumWidth(900)  # 400 + 400 + some room
    
        # Actions
        self.actionOpen = QAction(MainWindow)
        self.actionSave = QAction(MainWindow)
        self.actionSelect_background_Image = QAction(MainWindow)
    
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
        self.graphicsView = QGraphicsView()
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
    
        # Build menu
        self.menuEmpire_editor_augustus.addAction(self.actionOpen)
        self.menuEmpire_editor_augustus.addAction(self.actionSave)
        self.menuMap_Settings.addAction(self.actionSelect_background_Image)
        self.menubar.addAction(self.menuEmpire_editor_augustus.menuAction())
        self.menubar.addAction(self.menuMap_Settings.menuAction())
    
        self.retranslateUi(MainWindow)
        QMetaObject.connectSlotsByName(MainWindow)


    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", "MainWindow", None))
        self.actionOpen.setText(QCoreApplication.translate("MainWindow", "Open", None))
        self.actionSave.setText(QCoreApplication.translate("MainWindow", "Save", None))
        self.actionSelect_background_Image.setText(QCoreApplication.translate("MainWindow", "Select background Image", None))
        self.menuEmpire_editor_augustus.setTitle(QCoreApplication.translate("MainWindow", "File", None))
        self.menuMap_Settings.setTitle(QCoreApplication.translate("MainWindow", "Map Settings", None))
