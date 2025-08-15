#!/usr/bin/env python3
"""
Script to fix all Qt constants from PySide6 to PyQt6 format
"""
import re

def fix_qt_constants(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Replace Qt cursor constants
    replacements = [
        ('Qt.ArrowCursor', 'Qt.CursorShape.ArrowCursor'),
        ('Qt.CrossCursor', 'Qt.CursorShape.CrossCursor'),
        ('Qt.PointingHandCursor', 'Qt.CursorShape.PointingHandCursor'),
        ('Qt.SizeAllCursor', 'Qt.CursorShape.SizeAllCursor'),
        ('Qt.IBeamCursor', 'Qt.CursorShape.IBeamCursor'),
        ('Qt.WaitCursor', 'Qt.CursorShape.WaitCursor'),
        ('Qt.BusyCursor', 'Qt.CursorShape.BusyCursor'),
        # Mouse button constants
        ('Qt.LeftButton', 'Qt.MouseButton.LeftButton'),
        ('Qt.RightButton', 'Qt.MouseButton.RightButton'),
        ('Qt.MiddleButton', 'Qt.MouseButton.MiddleButton'),
        ('Qt.NoButton', 'Qt.MouseButton.NoButton'),
        # Orientation constants
        ('Qt.Horizontal', 'Qt.Orientation.Horizontal'),
        ('Qt.Vertical', 'Qt.Orientation.Vertical'),
        # Alignment constants
        ('Qt.AlignCenter', 'Qt.AlignmentFlag.AlignCenter'),
        ('Qt.AlignLeft', 'Qt.AlignmentFlag.AlignLeft'),
        ('Qt.AlignRight', 'Qt.AlignmentFlag.AlignRight'),
        ('Qt.AlignTop', 'Qt.AlignmentFlag.AlignTop'),
        ('Qt.AlignBottom', 'Qt.AlignmentFlag.AlignBottom'),
        # Scroll bar policy
        ('Qt.ScrollBarAsNeeded', 'Qt.ScrollBarPolicy.ScrollBarAsNeeded'),
        ('Qt.ScrollBarAlwaysOff', 'Qt.ScrollBarPolicy.ScrollBarAlwaysOff'),
        ('Qt.ScrollBarAlwaysOn', 'Qt.ScrollBarPolicy.ScrollBarAlwaysOn'),
        # Text elide mode
        ('Qt.ElideNone', 'Qt.TextElideMode.ElideNone'),
        ('Qt.ElideLeft', 'Qt.TextElideMode.ElideLeft'),
        ('Qt.ElideRight', 'Qt.TextElideMode.ElideRight'),
        ('Qt.ElideMiddle', 'Qt.TextElideMode.ElideMiddle'),
        # Aspect ratio mode
        ('Qt.KeepAspectRatio', 'Qt.AspectRatioMode.KeepAspectRatio'),
        ('Qt.IgnoreAspectRatio', 'Qt.AspectRatioMode.IgnoreAspectRatio'),
        # Transform mode
        ('Qt.SmoothTransformation', 'Qt.TransformationMode.SmoothTransformation'),
        ('Qt.FastTransformation', 'Qt.TransformationMode.FastTransformation'),
        # User role
        ('Qt.UserRole', 'Qt.ItemDataRole.UserRole'),
        # QSettings format
        ('QSettings.IniFormat', 'QSettings.Format.IniFormat'),
        ('QSettings.NativeFormat', 'QSettings.Format.NativeFormat'),
        # QImage format
        ('QImage.Format_RGBA8888', 'QImage.Format.Format_RGBA8888'),
        ('QImage.Format_RGB32', 'QImage.Format.Format_RGB32'),
        ('QImage.Format_ARGB32', 'QImage.Format.Format_ARGB32'),
        # QGraphicsView drag modes
        ('QGraphicsView.NoDrag', 'QGraphicsView.DragMode.NoDrag'),
        ('QGraphicsView.ScrollHandDrag', 'QGraphicsView.DragMode.ScrollHandDrag'),
        ('QGraphicsView.RubberBandDrag', 'QGraphicsView.DragMode.RubberBandDrag'),
        # QPainter render hints
        ('QPainter.SmoothPixmapTransform', 'QPainter.RenderHint.SmoothPixmapTransform'),
        ('QPainter.Antialiasing', 'QPainter.RenderHint.Antialiasing'),
        ('QPainter.TextAntialiasing', 'QPainter.RenderHint.TextAntialiasing'),
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Fixed Qt constants in {file_path}")

if __name__ == "__main__":
    fix_qt_constants("main_window.py")
    fix_qt_constants("ui_empire_editor.py")
