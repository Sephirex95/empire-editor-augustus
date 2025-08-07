# -*- coding: utf-8 -*-
"""
Created on Fri Jul 18 10:30:38 2025

@author: jslaw
"""

import sys
from PySide6.QtWidgets import QApplication
from main_window import MainWindow

# Reuse QApplication if it already exists (Spyder/IPython)
app = QApplication.instance()
if not app:
    app = QApplication(sys.argv)

# Only close and delete if previously defined
if "main_window_instance" in globals():
    try:
        main_window_instance.close()
        del main_window_instance
    except Exception as e:
        print("Warning: Failed to close previous window:", e)

# Create a new main window
main_window_instance = MainWindow()
main_window_instance.show()

# Only exit the process if running as a standalone script
if __name__ == "__main__" and not hasattr(sys, 'ps1'):
    sys.exit(app.exec())
