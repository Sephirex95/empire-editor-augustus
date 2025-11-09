# -*- coding: utf-8 -*-
"""
Created on Sun Aug 10 21:51:04 2025

@author: sephirex95
"""

# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'city_propertiesAzdzne.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import QCoreApplication, QMetaObject, QRect, QSize, Qt
from PySide6.QtGui import QCursor, QFont, QIcon, QPixmap, QImage
from PySide6.QtWidgets import *


def pil_to_qimage(pil_image):
    pil_image = pil_image.convert("RGBA")
    data = pil_image.tobytes("raw", "RGBA")
    w, h = pil_image.size
    return QImage(data, w, h, QImage.Format.Format_RGBA8888)


class Ui_Dialog(object):
    def setupUi(self, Dialog, current_city_icon, dict_of_icons=None):
        if not Dialog.objectName():
            Dialog.setObjectName("Dialog")
        Dialog.setEnabled(True)

        self.icons_dict = dict_of_icons
        self.current_city_icon = current_city_icon
        Dialog.resize(683, 487)
        Dialog.setMinimumSize(QSize(683, 487))
        font = QFont()
        font.setStyleStrategy(QFont.PreferDefault)
        Dialog.setFont(font)
        Dialog.setCursor(QCursor(Qt.CursorShape.ArrowCursor))
        Dialog.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        Dialog.setAutoFillBackground(True)
        Dialog.setSizeGripEnabled(False)
        Dialog.setModal(True)

        self.buttonBox = QDialogButtonBox(Dialog)
        self.buttonBox.setGeometry(QRect(10, 450, 661, 32))
        self.buttonBox.setOrientation(Qt.Orientation.Horizontal)
        self.buttonBox.setStandardButtons(
            QDialogButtonBox.Cancel | QDialogButtonBox.Ok | QDialogButtonBox.RestoreDefaults
        )

        self.groupBox = QGroupBox(Dialog)
        self.groupBox.setGeometry(QRect(350, 20, 321, 431))

        self.verticalLayoutWidget = QWidget(self.groupBox)
        self.verticalLayoutWidget.setGeometry(QRect(10, 20, 301, 391))
        self.verticalLayout = QVBoxLayout(self.verticalLayoutWidget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)

        self.label_5 = QLabel(self.verticalLayoutWidget)
        self.verticalLayout.addWidget(self.label_5)

        self.listWidgetSells = QListWidget(self.verticalLayoutWidget)
        self.verticalLayout.addWidget(self.listWidgetSells)

        self.label_6 = QLabel(self.verticalLayoutWidget)
        self.verticalLayout.addWidget(self.label_6)

        self.listWidgetBuys = QListWidget(self.verticalLayoutWidget)
        self.verticalLayout.addWidget(self.listWidgetBuys)

        # FORM AREA
        self.formLayoutWidget = QWidget(Dialog)
        self.formLayoutWidget.setGeometry(QRect(20, 30, 321, 260))
        self.formLayout = QFormLayout(self.formLayoutWidget)
        self.formLayout.setContentsMargins(0, 0, 0, 0)

        font1 = QFont()
        font1.setPointSize(12)

        self.label = QLabel(self.formLayoutWidget)
        self.label.setFont(font1)
        self.formLayout.setWidget(0, QFormLayout.LabelRole, self.label)

        self.lineEdit = QLineEdit(self.formLayoutWidget)
        self.formLayout.setWidget(0, QFormLayout.FieldRole, self.lineEdit)

        self.label_2 = QLabel(self.formLayoutWidget)
        self.label_2.setFont(font1)
        self.formLayout.setWidget(1, QFormLayout.LabelRole, self.label_2)

        self.comboBox = QComboBox(self.formLayoutWidget)
        for _ in range(5):
            self.comboBox.addItem("")
        self.formLayout.setWidget(1, QFormLayout.FieldRole, self.comboBox)

        # SHRINK INPUTS SO BUTTON CAN FIT NEXT TO THEM
        self.lineEdit.setFixedWidth(180)
        self.comboBox.setFixedWidth(180)

        # CITY ICON BUTTON NEXT TO INPUTS
        self.pushButtonCityIcon = QPushButton(Dialog)
        self.pushButtonCityIcon.setObjectName("pushButtonCityIcon")
        self.pushButtonCityIcon.setGeometry(QRect(270, 35, 60, 60))  # <--- HERE
        self.pushButtonCityIcon.clicked.connect(self.openIconSelector)

        # SECOND GROUP BOX
        self.groupBox_2 = QGroupBox(self.formLayoutWidget)
        self.groupBox_2.setMinimumSize(QSize(0, 160))
        self.formLayout.setWidget(2, QFormLayout.SpanningRole, self.groupBox_2)

        self.formLayoutWidget_2 = QWidget(self.groupBox_2)
        self.formLayoutWidget_2.setGeometry(QRect(50, 20, 221, 71))
        self.formLayout_2 = QFormLayout(self.formLayoutWidget_2)

        font3 = QFont()
        font3.setPointSize(12)

        self.label_4 = QLabel(self.formLayoutWidget_2)
        self.label_4.setFont(font3)
        self.formLayout_2.setWidget(1, QFormLayout.LabelRole, self.label_4)

        self.comboBox_2 = QComboBox(self.formLayoutWidget_2)
        self.comboBox_2.addItem("")
        self.comboBox_2.addItem("")
        self.formLayout_2.setWidget(1, QFormLayout.FieldRole, self.comboBox_2)

        self.label_3 = QLabel(self.formLayoutWidget_2)
        self.label_3.setFont(font3)
        self.formLayout_2.setWidget(2, QFormLayout.LabelRole, self.label_3)

        self.spinBox = QSpinBox(self.formLayoutWidget_2)
        self.spinBox.setMaximum(100000)
        self.spinBox.setSingleStep(100)
        self.spinBox.setValue(500)
        self.formLayout_2.setWidget(2, QFormLayout.FieldRole, self.spinBox)

        self.pushButton = QPushButton(self.groupBox_2)
        self.pushButton.setGeometry(QRect(20, 100, 280, 41))
        self.pushButton.setFont(font3)

        self.retranslateUi(Dialog)
        self.buttonBox.accepted.connect(Dialog.accept)
        self.buttonBox.rejected.connect(Dialog.reject)
        QMetaObject.connectSlotsByName(Dialog)

    # setupUi
    def openIconSelector(self):
        # Get icons from the dictionary passed during setupUi
        if self.icons_dict is None:
            QMessageBox.warning(None, "Error", "No icons dictionary provided")
            return

        # Convert PIL images to QPixmap for the dialog
        icon_pixmaps = {}
        for key, pil_image in self.icons_dict.items():
            # Convert PIL image to QPixmap using BytesIO
            import io

            buffer = io.BytesIO()
            pil_image.save(buffer, format="PNG")
            qimage = QImage()
            qimage.loadFromData(buffer.getvalue())
            pixmap = QPixmap.fromImage(qimage)
            icon_pixmaps[key] = pixmap

        # Use None as parent since Ui_Dialog is not a QWidget
        dlg = CityIconSelector(icon_pixmaps, parent=None)

        if dlg.exec():
            # store the selection (now it's a key from the dictionary)
            self.current_city_icon = dlg.selected_icon
            # update the button icon using the pixmap
            self.pushButtonCityIcon.setIcon(QIcon(icon_pixmaps[self.current_city_icon]))
            self.pushButtonCityIcon.setIconSize(QSize(48, 48))

    def retranslateUi(self, Dialog):
        Dialog.setWindowTitle(QCoreApplication.translate("Dialog", "City Properties", None))
        self.groupBox.setTitle(QCoreApplication.translate("Dialog", "Trade", None))
        self.label_5.setText(QCoreApplication.translate("Dialog", "Sells", None))
        self.label_6.setText(QCoreApplication.translate("Dialog", "Buys", None))
        self.label.setText(QCoreApplication.translate("Dialog", "Name", None))
        self.lineEdit.setText(QCoreApplication.translate("Dialog", "City Name", None))
        self.label_2.setText(QCoreApplication.translate("Dialog", "Type", None))
        self.comboBox.setItemText(0, QCoreApplication.translate("Dialog", "Ours", None))
        self.comboBox.setItemText(1, QCoreApplication.translate("Dialog", "Trade", None))
        self.comboBox.setItemText(2, QCoreApplication.translate("Dialog", "Roman", None))
        self.comboBox.setItemText(3, QCoreApplication.translate("Dialog", "Distant", None))
        self.comboBox.setItemText(4, QCoreApplication.translate("Dialog", "Vulnerable", None))

        self.groupBox_2.setTitle(QCoreApplication.translate("Dialog", "Trade Route", None))
        self.label_3.setText(QCoreApplication.translate("Dialog", "Cost", None))
        self.label_4.setText(QCoreApplication.translate("Dialog", "Type", None))
        self.comboBox_2.setItemText(0, QCoreApplication.translate("Dialog", "Land", None))
        self.comboBox_2.setItemText(1, QCoreApplication.translate("Dialog", "Sea", None))
        self.pushButtonCityIcon.setToolTip(QCoreApplication.translate("Dialog", "Change City Icon", None))
        # Placeholder until external code sets real icon
        pil_img = self.icons_dict[self.current_city_icon]
        qimg = pil_to_qimage(pil_img)
        pixmap = QPixmap.fromImage(qimg).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.pushButtonCityIcon.setIcon(QIcon(pixmap))
        self.pushButtonCityIcon.setIconSize(QSize(48, 48))  # <--- this is what was missing
        self.pushButtonCityIcon.setFixedSize(60, 60)  # ensure button can display it

        self.pushButton.setText(QCoreApplication.translate("Dialog", "Plot Trade Route", None))

    # retranslateUi


from PySide6.QtWidgets import QDialog, QGridLayout, QPushButton
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize


class CityIconSelector(QDialog):
    def __init__(self, icon_pixmaps_dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select City Icon")
        self.resize(400, 400)

        layout = QGridLayout(self)

        self.selected_icon = None
        size = QSize(48, 48)

        # Create grid from dictionary
        for index, (key, pixmap) in enumerate(icon_pixmaps_dict.items()):
            btn = QPushButton()
            btn.setIcon(QIcon(pixmap))
            btn.setIconSize(size)
            btn.setFixedSize(64, 64)
            btn.setToolTip(key)  # Show the key name on hover
            btn.clicked.connect(lambda checked=False, k=key: self.choose(k))
            btn.setAutoDefault(False)
            btn.setDefault(False)
            btn.setFocusPolicy(Qt.NoFocus)

            layout.addWidget(btn, index // 4, index % 4)

    def choose(self, key):
        self.selected_icon = key
        self.accept()
