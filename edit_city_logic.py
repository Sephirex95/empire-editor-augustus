# -*- coding: utf-8 -*-
"""
Created on Sun Aug 10 22:02:04 2025

@author: jslaw
"""
# city_properties_dialog.py
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QDialog, QListWidget, QListWidgetItem, QWidget, QHBoxLayout,
    QComboBox, QSpinBox, QStyleFactory, QAbstractItemView, QApplication
)
from PySide6.QtGui import QPalette
from edit_city import Ui_Dialog # <-- your generated file/class name
from empire_data import ResourceType, CityType  

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
    """Map translated/pretty UI labels to CityType (case-insensitive)."""
    if not text:
        return None
    key = text.strip().lower()
    mapping = {
        "ours": CityType.OURS,
        "trade": CityType.TRADE,
        "roman": CityType.ROMAN,
        "distant": CityType.DISTANT,
        "vulnerable": CityType.VULNERABLE,
    }
    return mapping.get(key)


class ResourceRow(QWidget):
    def __init__(self, resources, ours=False, parent=None):
        super().__init__(parent)

        self.combo = QComboBox(self)
        self.combo.addItem("NONE")
        self.combo.addItems(resources)
        self.combo.wheelEvent = lambda e: e.ignore()  # disable scroll
        
        #if not ours: #no counter for our city resource list
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
        self.resources_all = list(resources)          # full list (no NONE)
        self.available_resources = list(resources)    # mutable pool (no NONE)
        self.resource_order = {r: i for i, r in enumerate(resources)}  # original index lookup

        self._timers: dict[ResourceRow, QTimer] = {}
        self._item_for: dict[ResourceRow, QListWidgetItem] = {}
        self._append_row("NONE")                      # initial row defaults to NONE
        self.list.setSelectionMode(QAbstractItemView.NoSelection)   # no row selection
        self.list.setFocusPolicy(Qt.FocusPolicy.NoFocus)            # no focus border on the list

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
        if idx <= 0 or idx == last_idx:   # keep first row and last row
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
                self.available_resources + ([current] if current != "NONE" and current not in self.available_resources else []),
                key=lambda r: self.resource_order.get(r, 9999)
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
 

        ctype_ours = (self.dialog.current_city_type == CityType.OURS)
        row = ResourceRow(self.available_resources, ours=ctype_ours, parent=self.list)
        #row = ResourceRow(self.available_resources, self.list, ctype_ours)  # pool only = real resources
        # NO: row.combo.insertItem(0, "NONE")  # ResourceRow already did this
        row.combo.setCurrentText(initial_text)

        item = QListWidgetItem(self.list)
        item.setSizeHint(row.sizeHint())
        self.list.addItem(item)
        self.list.setItemWidget(item, row)
        self._item_for[row] = item
        self.list.scrollToBottom()   # show the newly added row


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
            w.combo.clearFocus()    # drop highlight/focus on the combo after change


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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)

        # Cache references to the relevant UI bits
        self._type_combo = getattr(self.ui, "comboBox", None)        # top "Type" combobox
        self._trade_group = getattr(self.ui, "groupBox_2", None)     # likely "Trade Route" group box
        self.current_city_type = None
        res_names = enum_strings(ResourceType)
        self.sells = DynamicList(self.ui.listWidgetSells, res_names, self)
        self.buys  = DynamicList(self.ui.listWidgetBuys, res_names, self)


        if self._type_combo is not None:
            self._type_combo.currentTextChanged.connect(self.on_city_type_changed)
            # apply initial state
            self.on_city_type_changed(self._type_combo.currentText())
            self.current_city_type = CityType(self._type_combo.currentText().lower()) #cast from text to class object

        # self.buyList = QListWidget(self.ui.verticalLayoutWidget)
        # vlay = self.ui.verticalLayout
        # idx = vlay.indexOf(self.ui.listView)
        # vlay.removeWidget(self.ui.listView)
        # self.ui.listView.setParent(None)
        
        # vlay.insertWidget(idx, self.buyList)
        # Collect resource names


        # Controllers for Sells and Buys

        self.ui.comboBox_2.setStyleSheet("")  # clear custom styles
        print(self.ui.groupBox_2.isEnabled())
        print("Enabled:", self.ui.comboBox_2.isEnabled())
        print("Palette role:", self.ui.comboBox_2.palette().color(QPalette.ColorRole.Base))
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
        
    def on_city_type_changed(self, text: str):
        """Show trade route UI only if city type is TRADE."""
        ctype = to_city_type(text)
        self.current_city_type = ctype
        # Rule summary:
        # - OURS, ROMAN, DISTANT, VULNERABLE -> hide trade route box & layout (and children)
        # - TRADE -> show them
        show_trade_route = (ctype == CityType.TRADE)
        show_trade_lists = (ctype == CityType.TRADE or ctype == CityType.OURS)
        # Group box: one call hides/shows all its children
        if self._trade_group is not None:
            self.ui.groupBox.setVisible(show_trade_lists)
            self.ui.groupBox_2.setVisible(show_trade_route)
            if ctype == CityType.OURS:
                self.ui.label_6.setVisible(False)
                self.ui.listWidgetBuys.setVisible(False)
                self.sells.set_spins_visible(False)  
            elif ctype == CityType.TRADE:
                self.ui.label_6.setVisible(True)
                self.ui.listWidgetBuys.setVisible(True)
                self.sells.set_spins_visible(True)  
        # If you also have a separate layout area to hide:

# --- quick test harness ----------------------------------------------------
if __name__ == "__main__":

    app = QApplication.instance() or QApplication([])
    dlg = CityPropertiesDialog()
    dlg.show()
    """
    DEBUGGING COMMANDS FOR PREVIEWING:
        
    app.setStyle("Windows") # <-classic windows style 
    app.setPalette(app.style().standardPalette()) #<-forces standard windows colour palette, to override dark theme etc
    print(QStyleFactory.keys()) #show available basic styles
    """
    sys.exit(app.exec())
    sys.exit(0)

