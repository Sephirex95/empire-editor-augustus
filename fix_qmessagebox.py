#!/usr/bin/env python3
"""
Script to fix all QMessageBox constants from PySide6 to PyQt6 format
"""
import re

def fix_qmessagebox_constants(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace QMessageBox constants
    replacements = [
        ('QMessageBox.Ok', 'QMessageBox.StandardButton.Ok'),
        ('QMessageBox.Yes', 'QMessageBox.StandardButton.Yes'),
        ('QMessageBox.No', 'QMessageBox.StandardButton.No'),
        ('QMessageBox.Cancel', 'QMessageBox.StandardButton.Cancel'),
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed QMessageBox constants in {file_path}")

if __name__ == "__main__":
    fix_qmessagebox_constants("main_window.py")
