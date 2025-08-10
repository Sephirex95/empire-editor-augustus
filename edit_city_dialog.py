#edit_city_dialog.py
# -*- coding: utf-8 -*-
"""
Created on Sun Aug 10 01:59:23 2025

@author: sephirex95
"""

# ========== City Editor Dialog ==========
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QSpinBox, QComboBox, QPushButton, QLabel,
    QWidget, QStackedWidget, QTableWidget, QTableWidgetItem, QCheckBox
)
from PySide6.QtCore import Qt

RESOURCES = [
    "wheat","vegetables","fruit","olives","vines","meat","fish","wine","oil",
    "iron","gold","timber","wood","clay","marble","weapons","furniture","pottery"
]

# Map between editor type names and your model enum/values
CITY_TYPE_CHOICES = [
    ("ours",      "OURS"),
    ("trade",     "TRADE"),     # default
    ("roman",     "ROMAN"),     # distant roman, non-trade
    ("distant",   "DISTANT"),   # foreign, non-trade
    ("vulnerable","VULNERABLE") # distant roman, attackable
]

class ResourceTable(QTableWidget):
    """
    Two-column (Enabled, Amount) table of resources.
    For 'ours' cities, call set_amounts_visible(False) to hide the amount column.
    """
    def __init__(self, show_amounts=True, parent=None):
        super().__init__(len(RESOURCES), 2, parent)
        self.setHorizontalHeaderLabels(["", "Amount"])
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setAmountColumnVisible(show_amounts)

        for row, name in enumerate(RESOURCES):
            # checkbox with resource name as item text (for accessibility/tooltips)
            cb = QCheckBox(name)
            cb.setTristate(False)
            cb.setToolTip(name)
            self.setCellWidget(row, 0, cb)

            sp = QSpinBox()
            sp.setRange(1, 999)
            sp.setValue(1)
            self.setCellWidget(row, 1, sp)

        self.resizeColumnsToContents()
        self.setColumnWidth(0, 180)

    def setAmountColumnVisible(self, visible: bool):
        self.setColumnHidden(1, not visible)

    def load_from_lists(self, resource_list, has_amounts: bool):
        """
        resource_list: list[ (type:str, amount:int|None) ] or list[str]
        has_amounts=True for trade cities (buys/sells),
        has_amounts=False for 'ours' sells.
        """
        present = {}
        if resource_list:
            for entry in resource_list:
                if isinstance(entry, str):
                    present[entry] = None
                else:
                    rtype = entry.type if hasattr(entry, "type") else entry.get("type")
                    amount = entry.amount if hasattr(entry, "amount") else entry.get("amount")
                    present[str(rtype)] = amount

        for row, name in enumerate(RESOURCES):
            cb = self.cellWidget(row, 0)
            sp = self.cellWidget(row, 1)
            if name in present:
                cb.setChecked(True)
                if has_amounts and present[name] is not None:
                    sp.setValue(int(present[name]))
            else:
                cb.setChecked(False)
            sp.setEnabled(has_amounts)

    def to_list(self, has_amounts: bool):
        out = []
        for row, name in enumerate(RESOURCES):
            cb = self.cellWidget(row, 0)
            if not cb.isChecked():
                continue
            if has_amounts:
                sp = self.cellWidget(row, 1)
                out.append({"type": name, "amount": int(sp.value())})
            else:
                out.append({"type": name})
        return out


class EmpireCityDialog(QDialog):
    """
    Drop this class into your codebase. To use:
        dlg = EmpireCityDialog(city_obj, self)   # parent = MainWindow
        if dlg.exec() == QDialog.Accepted:
            # city_obj has been updated
    """
    def __init__(self, city, parent=None):
        super().__init__(parent)
        self.setWindowTitle("City Properties")
        self.city = city  # ed.City instance

        # --- Layout scaffold
        root = QVBoxLayout(self)

        # Basics
        basics = QGroupBox("Basics")
        form = QFormLayout(basics)

        self.name_edit = QLineEdit()
        self.x_spin = QSpinBox()
        self.y_spin = QSpinBox()
        for sp in (self.x_spin, self.y_spin):
            sp.setRange(0, 100000)  # adjust to your map bounds

        self.type_combo = QComboBox()
        for label, _ in CITY_TYPE_CHOICES:
            self.type_combo.addItem(label)

        form.addRow("Name", self.name_edit)
        form.addRow("X", self.x_spin)
        form.addRow("Y", self.y_spin)
        form.addRow("Type", self.type_combo)

        # Type-specific area
        self.stack = QStackedWidget()

        # Page 0: OURS -> Sells (no amounts)
        page_ours = QWidget()
        v0 = QVBoxLayout(page_ours)
        sells_box_ours = QGroupBox("What we can produce (sells)")
        v0f = QVBoxLayout(sells_box_ours)
        self.sells_ours = ResourceTable(show_amounts=False)
        v0f.addWidget(self.sells_ours)
        v0.addWidget(sells_box_ours)
        v0.addStretch()

        # Page 1: TRADE -> route + buys/sells (with amounts)
        page_trade = QWidget()
        v1 = QVBoxLayout(page_trade)

        route_box = QGroupBox("Trade Route")
        route_form = QFormLayout(route_box)
        self.route_cost = QSpinBox()
        self.route_cost.setRange(0, 99999)
        self.route_cost.setValue(500)
        self.route_type = QComboBox()
        self.route_type.addItems(["land", "sea"])
        route_form.addRow("Cost", self.route_cost)
        route_form.addRow("Type", self.route_type)

        buys_box = QGroupBox("Buys")
        vb1 = QVBoxLayout(buys_box)
        self.buys_trade = ResourceTable(show_amounts=True)
        vb1.addWidget(self.buys_trade)

        sells_box = QGroupBox("Sells")
        vb2 = QVBoxLayout(sells_box)
        self.sells_trade = ResourceTable(show_amounts=True)
        vb2.addWidget(self.sells_trade)

        v1.addWidget(route_box)
        v1.addWidget(buys_box)
        v1.addWidget(sells_box)

        # Page 2: ROMAN/DISTANT/VULNERABLE -> no trading widgets
        page_other = QWidget()
        v2 = QVBoxLayout(page_other)
        v2.addWidget(QLabel("No trading options for this city type."))
        v2.addStretch()

        # add pages in the order we’ll map to
        self.stack.addWidget(page_ours)   # 0
        self.stack.addWidget(page_trade)  # 1
        self.stack.addWidget(page_other)  # 2

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        ok_btn = QPushButton("OK")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)

        # Assemble
        root.addWidget(basics)
        root.addWidget(self.stack)
        root.addLayout(btns)

        # Wire type switching
        self.type_combo.currentTextChanged.connect(self._on_type_changed)

        # Load current city into widgets
        self._load_from_city()

    # ---------- Data binding ----------
    def _on_type_changed(self, t: str):
        if t == "ours":
            self.stack.setCurrentIndex(0)
        elif t == "trade":
            self.stack.setCurrentIndex(1)
        else:
            self.stack.setCurrentIndex(2)

    def _model_to_editor_type(self, city_type):
        # city.type is ed.CityType enum in your model
        name = getattr(city_type, "name", str(city_type)).upper() if city_type else "TRADE"
        for label, key in CITY_TYPE_CHOICES:
            if key == name:
                return label
        return "trade"

    def _editor_to_model_type(self, label: str):
        # returns a model ed.CityType member by name if it exists
        for l, key in CITY_TYPE_CHOICES:
            if l == label:
                return getattr(type(self.city.type), key, None) or getattr(self._city_type_enum(), key, None)
        return getattr(self._city_type_enum(), "TRADE", None)

    def _city_type_enum(self):
        # helper: ed.CityType enum
        return getattr(__import__("empire_data", fromlist=["CityType"]), "CityType")

    def _load_from_city(self):
        c = self.city
        self.name_edit.setText(getattr(c, "name", "") or "")
        self.x_spin.setValue(int(getattr(c, "x", 0) or 0))
        self.y_spin.setValue(int(getattr(c, "y", 0) or 0))
        tlabel = self._model_to_editor_type(getattr(c, "type", None))
        self.type_combo.setCurrentText(tlabel)
        self._on_type_changed(tlabel)

        # route / buys / sells:
        # Build simple lists from your model structure (adapt if your model differs)
        def to_list(objs):
            out = []
            for o in (objs or []):
                typ = getattr(o, "type", None)
                amt = getattr(o, "amount", None)
                if typ is None:
                    continue
                out.append({"type": str(typ), "amount": amt})
            return out

        if tlabel == "ours":
            self.sells_ours.load_from_lists(to_list(getattr(c, "sells", [])), has_amounts=False)

        elif tlabel == "trade":
            self.route_cost.setValue(int(getattr(c, "trade_route_cost", 500) or 500))
            self.route_type.setCurrentText(str(getattr(c, "trade_route_type", "land") or "land"))
            self.buys_trade.load_from_lists(to_list(getattr(c, "buys", [])), has_amounts=True)
            self.sells_trade.load_from_lists(to_list(getattr(c, "sells", [])), has_amounts=True)

    def accept(self):
        # write back to model
        c = self.city
        c.name = self.name_edit.text().strip()
        c.x = int(self.x_spin.value())
        c.y = int(self.y_spin.value())

        # type
        model_type = self._editor_to_model_type(self.type_combo.currentText())
        if model_type is not None:
            c.type = model_type

        # route / resources based on type
        tlabel = self.type_combo.currentText()
        if tlabel == "ours":
            # sells required; amounts not needed
            sells_list = self.sells_ours.to_list(has_amounts=False)
            c.sells = [self._mk_res(o["type"], None) for o in sells_list]

            # clear trade-only fields
            c.buys = []
            c.trade_route_cost = None
            c.trade_route_type = None

        elif tlabel == "trade":
            c.trade_route_cost = int(self.route_cost.value())
            c.trade_route_type = self.route_type.currentText()

            buys_list = self.buys_trade.to_list(has_amounts=True)
            sells_list = self.sells_trade.to_list(has_amounts=True)
            c.buys  = [self._mk_res(o["type"], o["amount"]) for o in buys_list]
            c.sells = [self._mk_res(o["type"], o["amount"]) for o in sells_list]

        else:
            # roman / distant / vulnerable → no trade
            c.buys = []
            c.sells = []
            c.trade_route_cost = None
            c.trade_route_type = None

        super().accept()

    def _mk_res(self, rtype: str, amount: int | None):
        """
        Create a resource entry matching your model. Adjust to your dataclass/structure.
        """
        # If ed.Resource exists as a dataclass (type, amount)
        try:
            from empire_data import Resource
            return Resource(type=rtype, amount=amount if amount is not None else 1)
        except Exception:
            # Fallback: simple object with attrs
            o = type("Resource", (), {})()
            o.type = rtype
            o.amount = amount if amount is not None else 1
            return o
