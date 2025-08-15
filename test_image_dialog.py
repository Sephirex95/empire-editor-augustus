#!/usr/bin/env python3
"""
Test the Image Selection Dialog functionality
"""
import sys
from PyQt6.QtWidgets import QApplication
from ui_empire_editor import ImageSelectionDialog

def test_image_dialog():
    app = QApplication(sys.argv)
    
    # Create the dialog
    dialog = ImageSelectionDialog()
    
    print("Image Selection Dialog created successfully!")
    print("Available default images:")
    for i in range(dialog.image_list.count()):
        item = dialog.image_list.item(i)
        print(f"  - {item.text()}")
    
    # For testing without GUI, just show that it can be created
    print("\nDialog is ready to be shown with dialog.exec()")
    
    return True

if __name__ == "__main__":
    if test_image_dialog():
        print("✓ Image Selection Dialog test passed!")
    else:
        print("✗ Image Selection Dialog test failed!")
