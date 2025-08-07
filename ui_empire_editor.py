# ui_empire_editor.py

from PySide6.QtCore import Qt, QCoreApplication, QRect, QMetaObject
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QListWidget, QGraphicsView,
    QMenuBar, QMenu, QStatusBar
)


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1920, 931)
        MainWindow.setMinimumWidth(1400)

        # Actions
        self.actionOpen = QAction(MainWindow)
        self.actionOpen.setObjectName("actionOpen")
        self.actionSave = QAction(MainWindow)
        self.actionSave.setObjectName("actionSave")
        self.actionSelect_background_Image = QAction(MainWindow)
        self.actionSelect_background_Image.setObjectName("actionSelect_background_Image")

        # Central widget
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        # Sidebar list
        self.listWidget = QListWidget(self.centralwidget)
        self.listWidget.setObjectName("listWidget")
        self.listWidget.setGeometry(QRect(1520, 21, 375, 751))
        self.listWidget.setMinimumWidth(400)
        self.listWidget.setDragEnabled(True)
        self.listWidget.setSelectionMode(QListWidget.SingleSelection)
        self.listWidget.setDefaultDropAction(Qt.MoveAction)

        # Graphics view (placeholder — will be replaced)
        self.graphicsView = QGraphicsView(self.centralwidget)
        self.graphicsView.setObjectName("graphicsView")
        self.graphicsView.setGeometry(QRect(25, 21, 1531, 751))

        MainWindow.setCentralWidget(self.centralwidget)

        # Menus
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName("menubar")
        self.menubar.setGeometry(QRect(0, 0, 1915, 25))
        self.menuEmpire_editor_augustus = QMenu(self.menubar)
        self.menuEmpire_editor_augustus.setObjectName("menuEmpire_editor_augustus")
        self.menuMap_Settings = QMenu(self.menubar)
        self.menuMap_Settings.setObjectName("menuMap_Settings")
        MainWindow.setMenuBar(self.menubar)

        # Status bar
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        # Add menu items
        self.menubar.addAction(self.menuEmpire_editor_augustus.menuAction())
        self.menubar.addAction(self.menuMap_Settings.menuAction())
        self.menuEmpire_editor_augustus.addAction(self.actionOpen)
        self.menuEmpire_editor_augustus.addAction(self.actionSave)
        self.menuMap_Settings.addAction(self.actionSelect_background_Image)

        self.retranslateUi(MainWindow)
        QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", "MainWindow", None))
        self.actionOpen.setText(QCoreApplication.translate("MainWindow", "Open", None))
        self.actionSave.setText(QCoreApplication.translate("MainWindow", "Save", None))
        self.actionSelect_background_Image.setText(QCoreApplication.translate("MainWindow", "Select background Image", None))
        self.menuEmpire_editor_augustus.setTitle(QCoreApplication.translate("MainWindow", "File", None))
        self.menuMap_Settings.setTitle(QCoreApplication.translate("MainWindow", "Map Settings", None))
