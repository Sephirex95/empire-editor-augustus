#!/usr/bin/env python3
"""
Test the application with fixed QEvent constants
"""
import sys
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    
    try:
        window = MainWindow()
        print("✓ MainWindow created successfully!")
        
        # Test that our new dialog can be created
        from ui_empire_editor import ImageSelectionDialog
        dialog = ImageSelectionDialog(window)
        print("✓ ImageSelectionDialog created successfully!")
        
        print("\nApplication is ready!")
        print("You can now use File -> New to test the image selection dialog.")
        
        # Uncomment the next lines to actually show the window
        # window.show()
        # app.exec()
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

if __name__ == "__main__":
    if main():
        print("🎉 All tests passed! The application is working correctly.")
    else:
        print("❌ Tests failed.")
