# -*- coding: utf-8 -*-
"""
Created on Sun Aug 10 22:02:04 2025

@author: Sephirex95
"""

# city_properties_dialog.py
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import *

from edit_city import Ui_Dialog, CityIconSelector
from empire_data import *

import sys
# --- helpers ---------------------------------------------------------------


def enum_strings(enum_cls):
    # Works whether enum values are strings or not.
    items = []
    for m in enum_cls:
        s = m.value if isinstance(m.value, str) else m.name
        items.append(s)
    return items


def to_city_type(text: str) -> CityType | None:
    """Case-insensitive conversion to CityType enum."""
    try:
        return CityType(text.strip().lower())
    except ValueError:
        return None


def enum_text(e) -> str:
    return e.value if hasattr(e, "value") else str(e)


def to_trade_route_type(text: str) -> TradeRouteType | None:
    if not text:
        return None
    key = text.strip().lower()
    mapping = {
        "land": TradeRouteType.LAND,
        "sea": TradeRouteType.SEA,
    }
    return mapping.get(key)


class ResourceRow(QWidget):
    def __init__(self, resources, ours=False, parent=None):
        super().__init__(parent)

        self.combo = QComboBox(self)
        self.combo.addItem("NONE")
        self.combo.addItems(resources)
        self.combo.wheelEvent = lambda e: e.ignore()  # disable scroll

        # if not ours: #no counter for our city resource list
        self.spin = QSpinBox(self)
        self.spin.setRange(0, 5000)
        self.spin.setSingleStep(1)
        self.spin.setAccelerated(True)
        self.spin.setValue(1)
        self.spin.wheelEvent = lambda e: e.ignore()  # disable scroll

        lay = QHBoxLayout(self)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(6)
        lay.addWidget(self.combo, 1)
        lay.addWidget(self.spin, 0)
        if ours:
            self.spin.setVisible(False)


class DynamicList:
    """Manages ResourceRow widgets inside a QListWidget with add/remove rules."""

    def __init__(self, list_widget: QListWidget, resources, dialog: "CityPropertiesDialog"):
        self.dialog = dialog
        self.list = list_widget
        self.resources_all = list(resources)  # full list (no NONE)
        self.available_resources = list(resources)  # mutable pool (no NONE)
        self.resource_order = {r: i for i, r in enumerate(resources)}  # original index lookup

        self._timers: dict[ResourceRow, QTimer] = {}
        self._item_for: dict[ResourceRow, QListWidgetItem] = {}
        self._append_row("NONE")  # initial row defaults to NONE
        self.list.setSelectionMode(QAbstractItemView.NoSelection)  # no row selection
        self.list.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # no focus border on the list

    def clear(self):
        for i in reversed(range(self.list.count())):
            it = self.list.takeItem(i)
            w = self.list.itemWidget(it)
            if w:
                w.deleteLater()
            del it
        self._item_for.clear()
        self._timers.clear()
        self.available_resources = list(self.resources_all)

    def load_from_resources(self, res_list: list[Resource], ours: bool):
        """Populate rows from Resource dataclasses."""
        self.clear()
        # start with a first row if empty
        if self.list.count() == 0:
            self._append_row("NONE")

        # consume specified resources in enum order for tidiness
        pairs = [(enum_text(r.resource_type), r.amount) for r in res_list]
        pairs.sort(key=lambda t: self.resource_order.get(t[0], 9999))

        # set rows
        if pairs:
            # re-use first row
            first_name, first_amt = pairs[0]
            # consume from pool so combos de-duplicate correctly
            if first_name in self.available_resources:
                self.available_resources.remove(first_name)
            row0 = self.list.itemWidget(self.list.item(0))
            row0.combo.blockSignals(True)
            row0.combo.setCurrentText(first_name)
            row0._last_value = first_name
            row0.combo.blockSignals(False)
            if hasattr(row0, "spin"):
                row0.spin.setValue(0 if first_amt is None else int(first_amt))

            # append the rest
            for name, amount in pairs[1:]:
                r = self._append_row(name)
                # consume from pool
                if name in self.available_resources:
                    self.available_resources.remove(name)
                if hasattr(r, "spin"):
                    r.spin.setValue(0 if amount is None else int(amount))

        # ensure trailing addable row
        last = self.list.itemWidget(self.list.item(self.list.count() - 1))
        if last and getattr(last, "_last_value", "NONE") != "NONE":
            self._append_row("NONE")

        # spins visibility
        self.set_spins_visible(not ours)
        self._refresh_all_combos()

    def to_resources(self, ours: bool) -> list[Resource]:
        """Extract Resource dataclasses from current rows."""
        out = []
        for i in range(self.list.count()):
            w = self.list.itemWidget(self.list.item(i))
            if not isinstance(w, ResourceRow):
                continue
            name = w.combo.currentText()
            if name == "NONE":
                continue
            rtype = ResourceType(name)  # let this raise if inconsistent
            amount = None if ours else int(w.spin.value())
            # for non-OURS, optional: skip zeroes
            if not ours and amount == 0:
                continue
            out.append(Resource(rtype, (1 if ours else amount or 1)))
        return out

    def add_empty_if_needed(self, row_widget: ResourceRow):
        last_idx = self.list.count() - 1
        idx = self._index_of(row_widget)
        max_rows = len(self.resources_all)  # only allow up to total resources
        if idx == last_idx and row_widget.combo.currentText() != "NONE" and self.list.count() < max_rows:
            self._append_row("NONE")

    def set_spins_visible(self, visible: bool):
        for i in range(self.list.count()):
            w = self.list.itemWidget(self.list.item(i))
            if isinstance(w, ResourceRow) and hasattr(w, "spin"):
                w.spin.setVisible(visible)

    def schedule_remove_if_none(self, row_widget: ResourceRow):
        idx = self._index_of(row_widget)
        last_idx = self.list.count() - 1
        if idx <= 0 or idx == last_idx:  # keep first row and last row
            return
        self.cancel_timer(row_widget)
        t = QTimer(self.list)
        t.setSingleShot(True)
        t.timeout.connect(lambda: self._remove_if_still_none(row_widget))
        self._timers[row_widget] = t
        t.start(500)

    def cancel_timer(self, row_widget: ResourceRow):
        t = self._timers.pop(row_widget, None)
        if t:
            t.stop()
            t.deleteLater()

    def _rows(self):
        for i in range(self.list.count()):
            w = self.list.itemWidget(self.list.item(i))
            if isinstance(w, ResourceRow):
                yield w

    def _refresh_all_combos(self):
        # Rebuild every combo’s items list to match current availability
        for row in self._rows():
            current = getattr(row, "_last_value", "NONE")
            options = ["NONE"] + sorted(
                self.available_resources
                + ([current] if current != "NONE" and current not in self.available_resources else []),
                key=lambda r: self.resource_order.get(r, 9999),
            )
            # Refill only if changed, and preserve selection
            combo = row.combo
            old_block = combo.blockSignals(True)
            if [combo.itemText(i) for i in range(combo.count())] != options:
                combo.clear()
                combo.addItems(options)
            # ensure current stays selected
            if current in options:
                combo.setCurrentText(current)
            else:
                combo.setCurrentText("NONE")
                row._last_value = "NONE"
            combo.blockSignals(old_block)

    # ----- internals -----
    def _append_row(self, initial_text: str):
        ctype_ours = self.dialog.current_city_type == CityType.OURS
        row = ResourceRow(self.available_resources, ours=ctype_ours, parent=self.list)
        # row = ResourceRow(self.available_resources, self.list, ctype_ours)  # pool only = real resources
        # NO: row.combo.insertItem(0, "NONE")  # ResourceRow already did this
        row.combo.setCurrentText(initial_text)

        item = QListWidgetItem(self.list)
        item.setSizeHint(row.sizeHint())
        self.list.addItem(item)
        self.list.setItemWidget(item, row)
        self._item_for[row] = item
        self.list.scrollToBottom()  # show the newly added row

        def on_changed(txt: str, w=row):
            self.cancel_timer(w)
            old = getattr(w, "_last_value", "NONE")
            new = txt

            # return old selection to pool if it was a real resource
            if old != "NONE" and old in self.resources_all and old not in self.available_resources:
                self.available_resources.append(old)

            # take new selection from pool if valid
            if new != "NONE" and new in self.available_resources:
                self.available_resources.remove(new)

            w._last_value = new

            if new == "NONE":
                self.schedule_remove_if_none(w)
            else:
                self.add_empty_if_needed(w)
            self._refresh_all_combos()
            w.combo.clearFocus()  # drop highlight/focus on the combo after change

        row.combo.currentTextChanged.connect(on_changed)
        row._last_value = initial_text
        self._refresh_all_combos()
        return row

    def _index_of(self, row_widget: ResourceRow) -> int:
        item = self._item_for.get(row_widget)
        return self.list.row(item) if item is not None else -1

    def _remove_if_still_none(self, row_widget: ResourceRow):
        self._timers.pop(row_widget, None)
        idx = self._index_of(row_widget)
        if idx > 0 and row_widget.combo.currentText() == "NONE" and not row_widget.combo.view().isVisible():
            # return last real resource to pool
            old = getattr(row_widget, "_last_value", "NONE")
            if old != "NONE" and old not in self.available_resources:
                self.available_resources.append(old)

            item = self._item_for.pop(row_widget, None)
            if item is not None:
                self.list.takeItem(idx)
                row_widget.deleteLater()
                del item
        self._refresh_all_combos()


# --- main dialog -----------------------------------------------------------


class CityPropertiesDialog(QDialog):
    def __init__(self, city: City, parent=None):
        super().__init__(parent)
        # get icons list from parents state:
        city_icons_dict = parent.state.get_city_icons_dict()

        self.ui = Ui_Dialog()
        # list of icons here
        self.ui.setupUi(self, current_city_icon=city.icon.value, dict_of_icons=city_icons_dict)

        # Cache references to the relevant UI bits
        # Exact bindings (from your retranslateUi)
        self._type_combo = self.ui.comboBox  # "Type"
        self.current_city_type = self._type_combo  # hack
        self._route_type_combo = self.ui.comboBox_2  # "Trade Route > Type"
        self._route_cost_spin = self.ui.spinBox  # adjust if your objectName differs
        self._name_edit = self.ui.lineEdit  # "Name"
        self._button_box = self.ui.buttonBox
        self._trade_group = self.ui.groupBox_2  # "Trade Route"
        self._lists_group = self.ui.groupBox  # "Trade" group (Sells/Buys)
        self._current_city_icon = self.ui.pushButtonCityIcon
        self.city = city
        # atm no X/Y widgets in this dialog
        self._x_spin = None
        self._y_spin = None

        res_names = enum_strings(ResourceType)
        self.sells = DynamicList(self.ui.listWidgetSells, res_names, self)
        self.buys = DynamicList(self.ui.listWidgetBuys, res_names, self)

        if self._type_combo is not None:
            self._type_combo.currentTextChanged.connect(self.on_city_type_changed)
            # apply initial state
            self.on_city_type_changed(self._type_combo.currentText())
            self.current_city_type = CityType(self._type_combo.currentText().lower())  # cast from text to class object

        self.ui.comboBox_2.setStyleSheet("")  # clear custom styles

        self.ui.comboBox_2.setAutoFillBackground(False)
        self.ui.comboBox_2.setPalette(QApplication.palette())  # reset to default app palette
        self.setStyleSheet("""
            QComboBox {
                background-color: palette(Base);
            }
        """)
        # Optional: set sensible widths
        self.ui.listWidgetSells.setUniformItemSizes(False)
        self.ui.listWidgetBuys.setUniformItemSizes(False)
        # ADD at the end of __init__ (after your styling and list setup)
        self._load_city_into_widgets()

        self.requested_route_draw = False
        self.ui.pushButton.clicked.connect(self.draw_trade_route)
        self.result_city: City | None = None

    def _load_city_into_widgets(self):
        c = self.city

        # basics
        if self._name_edit:
            self._name_edit.setText(c.name)

        # city type (store enums in userData; select by enum)
        if self._type_combo:
            block = self._type_combo.blockSignals(True)
            self._type_combo.clear()
            for ct in CityType:
                self._type_combo.addItem(enum_text(ct).capitalize(), ct)
            idx = self._type_combo.findData(c.city_type)
            if idx >= 0:
                self._type_combo.setCurrentIndex(idx)
            self._type_combo.blockSignals(block)
            self.on_city_type_changed(self._type_combo.currentText())

        # trade route
        if self._route_type_combo:
            block = self._route_type_combo.blockSignals(True)
            self._route_type_combo.clear()
            for rt in TradeRouteType:
                self._route_type_combo.addItem(enum_text(rt).capitalize(), rt)
            if c.trade_route:
                idx = self._route_type_combo.findData(c.trade_route.r_type)
                if idx >= 0:
                    self._route_type_combo.setCurrentIndex(idx)
                if self._route_cost_spin:
                    self._route_cost_spin.setValue(int(c.trade_route.cost))
            self._route_type_combo.blockSignals(block)

        # resources
        ours = c.city_type == CityType.OURS
        self.sells.load_from_resources(c.sells, ours=ours)
        self.buys.load_from_resources(c.buys, ours=False)

    def widget_values_to_city(self) -> City:
        c = self.city  # mutate the exact instance

        # basics
        c.name = self._name_edit.text()
        # no X/Y widgets in this dialog; keep existing coords
        c.city_type = self._type_combo.currentData() or to_city_type(self._type_combo.currentText())

        # trade route (optional). Preserve existing points until you add a UI.
        if self.ui.groupBox_2.isVisible():
            tr_type = self._route_type_combo.currentData() or to_trade_route_type(self._route_type_combo.currentText())
            tr_cost = int(self._route_cost_spin.value())
            existing_pts = c.trade_route.trade_points if c.trade_route else []
            c.trade_route = TradeRoute(cost=tr_cost, r_type=tr_type, trade_points=list(existing_pts))
        else:
            c.trade_route = None

        # resources (DynamicList already returns Resource objects)
        ours = c.city_type == CityType.OURS
        c.sells = self.sells.to_resources(ours)
        c.buys = self.buys.to_resources(False)
        
        # city icon - get from the icon selector if it was changed
        if hasattr(self.ui, 'current_city_icon') and self.ui.current_city_icon:
            c.icon = CityIconType(self.ui.current_city_icon)
        else:
            c.icon = CityIconType.default_icon(c.city_type)
        
        return c

    def draw_trade_route(self):
        self.requested_route_draw = True
        self.accept()

    def accept(self):
        self.result_city = self.widget_values_to_city()
        super().accept()

    def on_city_type_changed(self, text: str):
        """Show trade route UI only if city type is TRADE."""
        ctype = to_city_type(text)
        self.current_city_type = ctype
        # Rule summary:
        # - OURS, ROMAN, DISTANT, VULNERABLE -> hide trade route box & layout (and children)
        # - TRADE -> show them
        show_trade_route = ctype in [CityType.TRADE, CityType.FUTURE_TRADE]
        show_trade_lists = ctype in [CityType.TRADE, CityType.OURS, CityType.FUTURE_TRADE]
        # Group box: one call hides/shows all its children
        if self._trade_group is not None:
            self.ui.groupBox.setVisible(show_trade_lists)
            self.ui.groupBox_2.setVisible(show_trade_route)
            if ctype == CityType.OURS:
                self.ui.label_6.setVisible(False)
                self.ui.listWidgetBuys.setVisible(False)
                self.sells.set_spins_visible(False)
            elif ctype in [CityType.TRADE, CityType.FUTURE_TRADE]:
                self.ui.label_6.setVisible(True)
                self.ui.listWidgetBuys.setVisible(True)
                self.sells.set_spins_visible(True)
        # If you also have a separate layout area to hide:


# --- quick test
if __name__ == "__main__":
    app = QApplication.instance() or QApplication([])
    dlg = CityPropertiesDialog(City())
    dlg.show()
    """
    DEBUGGING COMMANDS FOR PREVIEWING:
        
    app.setStyle("Windows") # <-classic windows style 
    app.setPalette(app.style().standardPalette()) #<-forces standard windows colour palette, to override dark theme etc
    print(QStyleFactory.keys()) #show available basic styles
    """
    sys.exit(app.exec())
    sys.exit(0)
