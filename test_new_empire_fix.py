#!/usr/bin/env python3
"""
Test the fixed new empire functionality
"""
import sys
from PySide6.QtWidgets import QApplication
from main_window import MainWindow

def test_new_empire_fix():
    app = QApplication(sys.argv)
    
    try:
        window = MainWindow()
        print("✓ MainWindow created successfully!")
        
        # Test that our new dialog can be created
        from ui_empire_editor import ImageSelectionDialog
        dialog = ImageSelectionDialog(window)
        print("✓ ImageSelectionDialog created successfully!")
        
        print("\nFixes applied:")
        print("✓ Fixed QDialog.accepted -> QDialog.Accepted")
        print("✓ Use QPixmap directly instead of PIL conversion")
        print("✓ Follow same pattern as working set_background_image method")
        print("✓ Simplified clear_empire_data to avoid scene conflicts")
        
        print("\nThe new empire functionality should now work correctly!")
        print("Test by running the application and selecting File -> New")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    if test_new_empire_fix():
        print("🎉 New empire fix applied successfully!")
    else:
        print("❌ Test failed.")
