# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'form.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtWidgets import (QApplication, QGraphicsView, QListWidget, QListWidgetItem,
    QMainWindow, QMenu, QMenuBar, QSizePolicy,
    QStatusBar, QWidget)

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1915, 931)
        self.actionOpen = QAction(MainWindow)
        self.actionOpen.setObjectName(u"actionOpen")
        self.actionSave = QAction(MainWindow)
        self.actionSave.setObjectName(u"actionSave")
        self.actionSelect_background_Image = QAction(MainWindow)
        self.actionSelect_background_Image.setObjectName(u"actionSelect_background_Image")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.listWidget = QListWidget(self.centralwidget)
        self.listWidget.setObjectName(u"listWidget")
        self.listWidget.setGeometry(QRect(1580, 21, 256, 751))
        self.graphicsView = QGraphicsView(self.centralwidget)
        self.graphicsView.setObjectName(u"graphicsView")
        self.graphicsView.setGeometry(QRect(25, 21, 1531, 751))
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QMenuBar(MainWindow)
        self.menubar.setObjectName(u"menubar")
        self.menubar.setGeometry(QRect(0, 0, 1915, 25))
        self.menuEmpire_editor_augustus = QMenu(self.menubar)
        self.menuEmpire_editor_augustus.setObjectName(u"menuEmpire_editor_augustus")
        self.menuMap_Settings = QMenu(self.menubar)
        self.menuMap_Settings.setObjectName(u"menuMap_Settings")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QStatusBar(MainWindow)
        self.statusbar.setObjectName(u"statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.menubar.addAction(self.menuEmpire_editor_augustus.menuAction())
        self.menubar.addAction(self.menuMap_Settings.menuAction())
        self.menuEmpire_editor_augustus.addSeparator()
        self.menuEmpire_editor_augustus.addSeparator()
        self.menuEmpire_editor_augustus.addSeparator()
        self.menuEmpire_editor_augustus.addAction(self.actionOpen)
        self.menuEmpire_editor_augustus.addAction(self.actionSave)
        self.menuMap_Settings.addAction(self.actionSelect_background_Image)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"MainWindow", None))
        self.actionOpen.setText(QCoreApplication.translate("MainWindow", u"Open", None))
        self.actionSave.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.actionSelect_background_Image.setText(QCoreApplication.translate("MainWindow", u"Select background Image", None))
        self.menuEmpire_editor_augustus.setTitle(QCoreApplication.translate("MainWindow", u"File", None))
        self.menuMap_Settings.setTitle(QCoreApplication.translate("MainWindow", u"Map Settings", None))
    # retranslateUi

