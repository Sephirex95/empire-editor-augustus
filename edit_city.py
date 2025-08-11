# -*- coding: utf-8 -*-
"""
Created on Sun Aug 10 21:51:04 2025

@author: jslaw
"""

# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'city_propertiesAzdzne.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QAbstractButton, QAbstractSpinBox, QApplication, QComboBox,
    QDialog, QDialogButtonBox, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QSizePolicy, QSpinBox,
    QVBoxLayout, QWidget)

class Ui_Dialog(object):
    def setupUi(self, Dialog):
        if not Dialog.objectName():
            Dialog.setObjectName(u"Dialog")
        Dialog.setEnabled(True)
        Dialog.resize(683, 487)
        font = QFont()
        font.setStyleStrategy(QFont.PreferDefault)
        Dialog.setFont(font)
        Dialog.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        Dialog.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        Dialog.setAutoFillBackground(True)
        Dialog.setSizeGripEnabled(False)
        Dialog.setModal(True)
        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setObjectName(u"buttonBox")
        self.buttonBox.setGeometry(QRect(10, 450, 661, 32))
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.StandardButton.Cancel|QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.RestoreDefaults)
        self.groupBox = QGroupBox(Dialog)
        self.groupBox.setObjectName(u"groupBox")
        self.groupBox.setEnabled(True)
        self.groupBox.setGeometry(QRect(350, 20, 321, 431))
        self.verticalLayoutWidget = QWidget(self.groupBox)
        self.verticalLayoutWidget.setObjectName(u"verticalLayoutWidget")
        self.verticalLayoutWidget.setGeometry(QRect(10, 20, 301, 391))
        self.verticalLayout = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.label_5 = QLabel(self.verticalLayoutWidget)
        self.label_5.setObjectName(u"label_5")

        self.verticalLayout.addWidget(self.label_5)

        self.listWidgetSells = QListWidget(self.verticalLayoutWidget)
        self.listWidgetSells.setObjectName(u"listWidgetSells")

        self.verticalLayout.addWidget(self.listWidgetSells)

        self.label_6 = QLabel(self.verticalLayoutWidget)
        self.label_6.setObjectName(u"label_6")

        self.verticalLayout.addWidget(self.label_6)

        self.listWidgetBuys = QListWidget(self.verticalLayoutWidget)
        self.listWidgetBuys.setObjectName(u"listWidgetBuys")

        self.verticalLayout.addWidget(self.listWidgetBuys)

        self.formLayoutWidget = QWidget(Dialog)
        self.formLayoutWidget.setObjectName(u"formLayoutWidget")
        self.formLayoutWidget.setGeometry(QRect(20, 30, 321, 260))
        self.formLayout = QFormLayout(self.formLayoutWidget)
        self.formLayout.setObjectName(u"formLayout")
        self.formLayout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(self.formLayoutWidget)
        self.label.setObjectName(u"label")
        font1 = QFont()
        font1.setPointSize(12)
        font1.setStyleStrategy(QFont.PreferDefault)
        self.label.setFont(font1)

        self.formLayout.setWidget(0, QFormLayout.ItemRole.LabelRole, self.label)

        self.lineEdit = QLineEdit(self.formLayoutWidget)
        self.lineEdit.setObjectName(u"lineEdit")

        self.formLayout.setWidget(0, QFormLayout.ItemRole.FieldRole, self.lineEdit)

        self.label_2 = QLabel(self.formLayoutWidget)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setFont(font1)

        self.formLayout.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_2)

        self.comboBox = QComboBox(self.formLayoutWidget)
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.addItem("")
        self.comboBox.setObjectName(u"comboBox")
        self.comboBox.setAutoFillBackground(True)

        self.formLayout.setWidget(1, QFormLayout.ItemRole.FieldRole, self.comboBox)

        self.groupBox_2 = QGroupBox(self.formLayoutWidget)
        self.groupBox_2.setObjectName(u"groupBox_2")
        self.groupBox_2.setEnabled(True)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.groupBox_2.sizePolicy().hasHeightForWidth())
        self.groupBox_2.setSizePolicy(sizePolicy)
        self.groupBox_2.setMinimumSize(QSize(0, 160))
        font2 = QFont()
        #font2.setKerning(True)
        font2.setStyleStrategy(QFont.PreferDefault)
        self.groupBox_2.setFont(font2)
        self.formLayoutWidget_2 = QWidget(self.groupBox_2)
        self.formLayoutWidget_2.setObjectName(u"formLayoutWidget_2")
        self.formLayoutWidget_2.setGeometry(QRect(50, 20, 221, 71))
        self.formLayout_2 = QFormLayout(self.formLayoutWidget_2)
        self.formLayout_2.setObjectName(u"formLayout_2")
        self.formLayout_2.setContentsMargins(0, 0, 0, 0)
        self.label_3 = QLabel(self.formLayoutWidget_2)
        self.label_3.setObjectName(u"label_3")
        self.label_3.setMinimumSize(QSize(60, 0))
        font3 = QFont()
        font3.setPointSize(12)
        #font3.setKerning(True)
        font3.setStyleStrategy(QFont.PreferDefault)
        self.label_3.setFont(font3)

        self.formLayout_2.setWidget(2, QFormLayout.ItemRole.LabelRole, self.label_3)

        self.spinBox = QSpinBox(self.formLayoutWidget_2)
        self.spinBox.setObjectName(u"spinBox")
        self.spinBox.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.spinBox.setAutoFillBackground(True)
        self.spinBox.setWrapping(False)
        self.spinBox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        self.spinBox.setAccelerated(True)
        self.spinBox.setMaximum(100000)
        self.spinBox.setSingleStep(100)
        self.spinBox.setValue(500)

        self.formLayout_2.setWidget(2, QFormLayout.ItemRole.FieldRole, self.spinBox)

        self.label_4 = QLabel(self.formLayoutWidget_2)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setMinimumSize(QSize(60, 0))
        self.label_4.setBaseSize(QSize(80, 0))
        self.label_4.setFont(font3)

        self.formLayout_2.setWidget(1, QFormLayout.ItemRole.LabelRole, self.label_4)

        self.comboBox_2 = QComboBox(self.formLayoutWidget_2)
        self.comboBox_2.addItem("")
        self.comboBox_2.addItem("")
        self.comboBox_2.setObjectName(u"comboBox_2")
        self.comboBox_2.setAutoFillBackground(True)

        self.formLayout_2.setWidget(1, QFormLayout.ItemRole.FieldRole, self.comboBox_2)

        self.pushButton = QPushButton(self.groupBox_2)
        self.pushButton.setObjectName(u"pushButton")
        self.pushButton.setGeometry(QRect(20, 100, 280, 41))
        self.pushButton.setFont(font3)
        #self.pushButton.setAcceptDrops(False)
        self.pushButton.setAutoFillBackground(True)
        #self.pushButton.setFlat(False)

        self.formLayout.setWidget(2, QFormLayout.ItemRole.SpanningRole, self.groupBox_2)


        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)

        self.pushButton.setDefault(True)


        QMetaObject.connectSlotsByName(Dialog)
    # setupUi

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", u"City Properties", None))
        self.groupBox.setTitle(QCoreApplication.translate("Dialog", u"Trade", None))
        self.label_5.setText(QCoreApplication.translate("Dialog", u"Sells", None))
        self.label_6.setText(QCoreApplication.translate("Dialog", u"Buys", None))
        self.label.setText(QCoreApplication.translate("Dialog", u"Name", None))
        self.lineEdit.setText(QCoreApplication.translate("Dialog", u"City Name", None))
        self.label_2.setText(QCoreApplication.translate("Dialog", u"Type", None))
        self.comboBox.setItemText(0, QCoreApplication.translate("Dialog", u"Ours", None))
        self.comboBox.setItemText(1, QCoreApplication.translate("Dialog", u"Trade", None))
        self.comboBox.setItemText(2, QCoreApplication.translate("Dialog", u"Roman", None))
        self.comboBox.setItemText(3, QCoreApplication.translate("Dialog", u"Distant", None))
        self.comboBox.setItemText(4, QCoreApplication.translate("Dialog", u"Vulnerable", None))

        self.groupBox_2.setTitle(QCoreApplication.translate("Dialog", u"Trade Route", None))
        self.label_3.setText(QCoreApplication.translate("Dialog", u"Cost", None))
        self.label_4.setText(QCoreApplication.translate("Dialog", u"Type", None))
        self.comboBox_2.setItemText(0, QCoreApplication.translate("Dialog", u"Land", None))
        self.comboBox_2.setItemText(1, QCoreApplication.translate("Dialog", u"Sea", None))
        
        self.pushButton.setText(QCoreApplication.translate("Dialog", u"Plot Trade Route", None))
    # retranslateUi

