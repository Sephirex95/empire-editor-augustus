#!/usr/bin/env python3
"""
Test the New Empire functionality
"""
import sys
from PyQt6.QtWidgets import QApplication
from main_window import MainWindow

def test_new_empire():
    app = QApplication(sys.argv)
    
    # Create main window
    window = MainWindow()
    window.show()
    
    print("Main window created successfully!")
    print("You can now test the File -> New menu option")
    
    # For automated testing, we can call the method directly
    # window.on_new_empire()
    
    return app

if __name__ == "__main__":
    app = test_new_empire()
    # Uncomment the next line if you want to show the window
    # app.exec()
