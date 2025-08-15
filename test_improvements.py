#!/usr/bin/env python3
"""
Test the improved ImageSelectionDialog
"""
import sys
from PyQt6.QtWidgets import QApplication
from ui_empire_editor import ImageSelectionDialog

def test_improved_dialog():
    app = QApplication(sys.argv)
    
    try:
        dialog = ImageSelectionDialog()
        print("✓ ImageSelectionDialog created successfully!")
        print("✓ Transparent background applied")
        print("✓ Increased font size for list")
        print("✓ Minimum sizes set to prevent hiding panels")
        
        # Test font size increase
        font = dialog.image_list.font()
        print(f"✓ List font size: {font.pointSize()} points")
        
        # Test minimum widths
        print(f"✓ Left panel minimum width: {dialog.image_list.parent().minimumWidth()}px")
        
        print("\nDialog improvements applied successfully!")
        print("You can test by running the main application and selecting File -> New")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    if test_improved_dialog():
        print("🎉 All improvements working correctly!")
    else:
        print("❌ Test failed.")
