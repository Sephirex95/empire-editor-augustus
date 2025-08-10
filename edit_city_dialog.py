# -*- coding: utf-8 -*-
"""
Refactored City Editor Dialog (PySide6)
- Uses dataclasses and enums from `empire_data` instead of redefining constants
- Fixes buggy checkbox behavior by using native checkable QTableWidgetItems
- Prevents sticky selections by disabling selection on the table
- Enables/disables amount spinboxes in sync with check state
- Streamlined load/save logic directly to/from the data classes
- Fixed-size dialog: size can be provided in the constructor or defaults to sizeHint

Drop-in replacement for the previous `edit_city_dialog.py`.
"""
from __future__ import annotations

from typing import Iterable, Optional

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLineEdit, QSpinBox, QComboBox, QPushButton, QLabel,
    QWidget, QStackedWidget, QTableWidget, QTableWidgetItem
)
from PySide6.QtCore import Qt, Slot

# ---- Import canonical data model & enums ----
from empire_data import (
    City, CityType, TradeRouteType,
    Resource, ResourceType,
)

# Resource display order comes from the enum declaration in empire_data.ResourceType
RESOURCE_NAMES: list[str] = [rt.value for rt in ResourceType]
CITY_TYPE_LABELS: list[str] = [ct.value for ct in CityType]   # ['ours','roman','distant','trade','vulnerable']
ROUTE_TYPE_LABELS: list[str] = [tt.value for tt in TradeRouteType]  # ['land','sea']


# -------- Resource Table ----------------------------------------------------
class ResourceTable(QTableWidget):
    """Two-column table: [Enabled ✓]  [Amount].

    - Checkable items in column 0 (native QTableWidgetItem checkboxes)
    - QSpinBox editors in column 1
    - When `show_amounts` is False, the amount column is hidden and disabled.
    - Works directly with `empire_data.Resource` objects.
    """

    def __init__(self, show_amounts: bool = True, parent: Optional[QWidget] = None):
        super().__init__(len(RESOURCE_NAMES), 2, parent)
        self._block = False  # reentrancy guard for itemChanged
        self._show_amounts = show_amounts

        self.setHorizontalHeaderLabels(["", "Amount"]) 
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QTableWidget.NoSelection)  # avoid sticky selections
        self.setFocusPolicy(Qt.StrongFocus)

        for row, name in enumerate(RESOURCE_NAMES):
            # Column 0: Name with checkbox
            item = QTableWidgetItem(name)
            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            item.setToolTip(name)
            self.setItem(row, 0, item)

            # Column 1: Amount spinbox (as editor widget)
            sp = QSpinBox(self)
            sp.setRange(1, 999)
            sp.setValue(1)
            sp.setEnabled(show_amounts)
            self.setCellWidget(row, 1, sp)

        # Hide amount column if requested
        self.setAmountColumnVisible(show_amounts)

        # React to user toggles
        self.itemChanged.connect(self._on_item_changed)

        self.resizeColumnsToContents()
        self.setColumnWidth(0, max(140, self.columnWidth(0)))

    # --- API ---
    def setAmountColumnVisible(self, visible: bool) -> None:
        self._show_amounts = visible
        self.setColumnHidden(1, not visible)
        # Ensure spinboxes are disabled when hidden
        for row in range(self.rowCount()):
            w = self.cellWidget(row, 1)
            if isinstance(w, QSpinBox):
                w.setEnabled(visible and self.item(row, 0).checkState() == Qt.Checked)

    def load(self, resources: Optional[Iterable[Resource]], has_amounts: bool) -> None:
        """Load directly from a list of `Resource` objects (or None)."""
        present: dict[str, Optional[int]] = {}
        if resources:
            for r in resources:
                try:
                    rtype = r.type.value if isinstance(r.type, ResourceType) else str(r.type)
                except Exception:
                    rtype = str(getattr(r, "type", ""))
                amt = getattr(r, "amount", None)
                present[rtype] = None if amt is None else int(amt)

        self._block = True
        try:
            for row, name in enumerate(RESOURCE_NAMES):
                item = self.item(row, 0)
                sp = self.cellWidget(row, 1)
                checked = name in present
                item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
                if isinstance(sp, QSpinBox):
                    if has_amounts and present.get(name) is not None:
                        sp.setValue(present[name])
                    sp.setEnabled(has_amounts and checked and self._show_amounts)
        finally:
            self._block = False

    def to_resources(self, has_amounts: bool) -> list[Resource]:
        out: list[Resource] = []
        for row, name in enumerate(RESOURCE_NAMES):
            item = self.item(row, 0)
            if item.checkState() != Qt.Checked:
                continue
            amount: Optional[int]
            if has_amounts:
                sp = self.cellWidget(row, 1)
                amount = int(sp.value()) if isinstance(sp, QSpinBox) else 1
            else:
                amount = 1  # amount not stored for ours, but dataclass defaults to 1
            out.append(Resource(type=ResourceType(name), amount=amount))
        return out

    # --- Slots ---
    @Slot(QTableWidgetItem)
    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._block or item.column() != 0:
            return
        # Enable/disable amount editor in same row
        sp = self.cellWidget(item.row(), 1)
        if isinstance(sp, QSpinBox):
            sp.setEnabled(self._show_amounts and item.checkState() == Qt.Checked)


# -------- Dialog ------------------------------------------------------------
class EmpireCityDialog(QDialog):
    """City editor dialog bound to `empire_data.City`.

    Usage:
        dlg = EmpireCityDialog(city_obj, parent=self, fixed_size=(720, 560))
        if dlg.exec() == QDialog.Accepted:
            # city_obj has been updated
    """

    def __init__(self, city: City, parent: Optional[QWidget] = None, fixed_size: Optional[tuple[int, int]] = None):
        super().__init__(parent)
        self.city = city
        self.setWindowTitle("City Properties")

        # --- Layout scaffold
        root = QVBoxLayout(self)

        # Basics
        basics = QGroupBox("Basics")
        form = QFormLayout(basics)

        self.name_edit = QLineEdit()
        self.x_spin = QSpinBox(); self.x_spin.setRange(0, 100000)
        self.y_spin = QSpinBox(); self.y_spin.setRange(0, 100000)

        self.type_combo = QComboBox()
        self.type_combo.addItems(CITY_TYPE_LABELS)

        form.addRow("Name", self.name_edit)
        form.addRow("X", self.x_spin)
        form.addRow("Y", self.y_spin)
        form.addRow("Type", self.type_combo)

        # Type-specific area
        self.stack = QStackedWidget()

        # Page 0: OURS -> Sells (no amounts)
        page_ours = QWidget(); v0 = QVBoxLayout(page_ours)
        sells_box_ours = QGroupBox("What we can produce (sells)")
        vb0 = QVBoxLayout(sells_box_ours)
        self.sells_ours = ResourceTable(show_amounts=False)
        vb0.addWidget(self.sells_ours)
        v0.addWidget(sells_box_ours)
        v0.addStretch()

        # Page 1: TRADE -> route + buys/sells (with amounts)
        page_trade = QWidget(); v1 = QVBoxLayout(page_trade)

        route_box = QGroupBox("Trade Route")
        route_form = QFormLayout(route_box)
        self.route_cost = QSpinBox(); self.route_cost.setRange(0, 99999); self.route_cost.setValue(500)
        self.route_type = QComboBox(); self.route_type.addItems(ROUTE_TYPE_LABELS)
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

        # Page 2: Other types (roman/distant/vulnerable)
        page_other = QWidget(); v2 = QVBoxLayout(page_other)
        v2.addWidget(QLabel("No trading options for this city type."))
        v2.addStretch()

        self.stack.addWidget(page_ours)   # 0
        self.stack.addWidget(page_trade)  # 1
        self.stack.addWidget(page_other)  # 2

        # Buttons
        btns = QHBoxLayout()
        btns.addStretch()
        ok_btn = QPushButton("OK"); ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel"); cancel_btn.clicked.connect(self.reject)
        btns.addWidget(ok_btn)
        btns.addWidget(cancel_btn)

        # Assemble
        root.addWidget(basics)
        root.addWidget(self.stack)
        root.addLayout(btns)

        # Behavior
        self.type_combo.currentTextChanged.connect(self._on_type_changed)

        # Load model data
        self._load_from_city()

        # Fixed size
        if fixed_size is not None:
            self.setFixedSize(*fixed_size)
        else:
            self.setFixedSize(self.sizeHint())

    # ----- Type switching -----
    @Slot(str)
    def _on_type_changed(self, label: str) -> None:
        # Map enum value labels to pages
        idx = 2  # other by default
        if label == CityType.OURS.value:
            idx = 0
        elif label == CityType.TRADE.value:
            idx = 1
        self.stack.setCurrentIndex(idx)

    # ----- Load/Save -----
    def _load_from_city(self) -> None:
        c = self.city
        self.name_edit.setText(c.name or "")
        self.x_spin.setValue(int(c.x or 0))
        self.y_spin.setValue(int(c.y or 0))

        # type -> combo
        tlabel = c.type.value if isinstance(c.type, CityType) else str(c.type)
        if tlabel not in CITY_TYPE_LABELS:
            tlabel = CityType.TRADE.value
        self.type_combo.setCurrentText(tlabel)
        self._on_type_changed(tlabel)

        if tlabel == CityType.OURS.value:
            self.sells_ours.load(c.sells, has_amounts=False)
        elif tlabel == CityType.TRADE.value:
            # route
            self.route_cost.setValue(int(c.trade_route_cost or 500))
            route_label = c.trade_route_type.value if isinstance(c.trade_route_type, TradeRouteType) else str(c.trade_route_type)
            if route_label not in ROUTE_TYPE_LABELS:
                route_label = TradeRouteType.LAND.value
            self.route_type.setCurrentText(route_label)
            # resources
            self.buys_trade.load(c.buys, has_amounts=True)
            self.sells_trade.load(c.sells, has_amounts=True)

    # ----- Write back -----
    def accept(self) -> None:  # noqa: D401
        c = self.city
        c.name = self.name_edit.text().strip()
        c.x = int(self.x_spin.value())
        c.y = int(self.y_spin.value())

        # type
        current_label = self.type_combo.currentText()
        try:
            c.type = CityType(current_label)
        except ValueError:
            c.type = CityType.TRADE

        if c.type == CityType.OURS:
            c.sells = self.sells_ours.to_resources(has_amounts=False)
            c.buys = []
            c.trade_route_cost = None
            c.trade_route_type = TradeRouteType.LAND
        elif c.type == CityType.TRADE:
            c.trade_route_cost = int(self.route_cost.value())
            try:
                c.trade_route_type = TradeRouteType(self.route_type.currentText())
            except ValueError:
                c.trade_route_type = TradeRouteType.LAND
            c.buys = self.buys_trade.to_resources(has_amounts=True)
            c.sells = self.sells_trade.to_resources(has_amounts=True)
        else:
            c.buys = []
            c.sells = []
            c.trade_route_cost = None
            c.trade_route_type = TradeRouteType.LAND

        super().accept()
