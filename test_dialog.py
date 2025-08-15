#!/usr/bin/env python3
"""
Test script for the ImageSelectionDialog
"""
import sys
from PyQt6.QtWidgets import QApplication
from ui_empire_editor import ImageSelectionDialog

def test_dialog():
    app = QApplication(sys.argv)
    
    dialog = ImageSelectionDialog()
    result = dialog.exec()
    
    if result == dialog.Accepted:
        print(f"Selected image: {dialog.selected_image_path}")
    else:
        print("Dialog cancelled")
    
    app.quit()

if __name__ == "__main__":
    test_dialog()
