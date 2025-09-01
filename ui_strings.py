# -*- coding: utf-8 -*-
"""
UI Strings for Empire Editor.

This module contains all user-facing strings used in the application,
organized as a flat enum structure for easy reference and modification.

@author: sephirex95
"""

from enum import Enum


class UIS(str, Enum):
    """All UI strings in a flat structure for easy access."""

    # Dialog Titles
    UNSAVED_CHANGES = "Unsaved Changes"
    OPEN_XML = "Open Empire XML"
    SAVE_XML = "Save Empire XML"
    SAVE_AUGUSTUS = "Save to Augustus directory"
    TR_EXISTS = "Trade Route already exists"
    LEGACY_EMP = "Legacy Empire"
    NO_IMAGE = "No Image Specified"
    IMG_NOT_FOUND = "Map Image Not Found"
    NO_IMG_SEL = "No Image Selected"
    ELEMENTS_OOB = "Elements Outside Map Bounds"
    IMG_LOAD_ERR = "Image Load Error"
    MAP_LOAD_ERR = "Map Loading Error"
    DEL_TR = "Delete Trade Route"
    NO_BG = "No background"
    INCOMPLETE_BORDER = "Incomplete Border"
    INCOMPLETE_TR = "Incomplete Trade Route"
    MOVE_OUR_CITY = "Move Our City?"
    DEL_CITY = "Delete City"
    DEL_BORDER = "Delete Border"
    CONFIRM_DEL = "Confirm Deletion"
    WARNING = "Warning"
    ERROR = "Error"
    INFO = "Information"
    SUCCESS = "Success"
    SAVE_ERROR = "Save Error"
    MISSING_MAP = "Missing Map"
    TR_ALIGNED = "Tradepoints aligned"
    NO_MAP = "No Map Specified"
    DUP_OUR_CITY = "Duplicate 'Our City'"
    START_NEW_BORDER = "Start New Border?"
    INVALID_IMG = "Invalid Image"

    # Dialog Messages
    UNSAVED_SAVE = "You have unsaved changes. Do you want to save before {context}?"
    UNSAVED_DISCARD = "You have unsaved changes. Do you want to discard them and continue?"
    UNSAVED_PROGRESS = "You have unsaved work in the current empire.\nYou will lose your progress, continue?"

    LEGACY_EMP_MSG = "This is a version 1 empire file. Loading default empire background."
    NO_MAP_MSG = "Empire file doesn't specify a map. Loading default empire background."
    NO_IMAGE_MSG = "Empire map doesn't specify an image file. Loading default empire background."
    NO_IMG_SEL_MSG = "No image selected. Loading default empire background."

    # File operations
    EMP_LOADED = "Empire loaded from {file_path}"
    FILE_NOT_FOUND = "File not found: {file_path}"
    LOAD_ERROR = "Failed to load empire:\n{error}"
    NO_EMP_SAVE = "No empire to save. Create an empire first."
    EMP_SAVED_MSG = "Empire saved to {file_path}"
    SAVE_ERROR_MSG = "Failed to save empire:\n{error}"
    OUR_CITY_NOT_SET = "'Our City' is not set; the empire may function incorrectly.\n\nAre you sure you want to save?"
    AUGUSTUS_PROMPT = "Augustus user directory is set.\n\nWould you like to save to the Augustus user directories?\n• XML → editor/empires\n• Image → community/image"

    # Map and image messages
    MISSING_MAP_MSG = "The 'Default Empire Map' is not available in the loaded images."
    TR_ALIGNED_MSG = "Snapped {moved} tradepoints to their neighbours"
    DEL_TR_CONFIRM = "Delete trade route path for {city_name}?"
    IMG_NOT_FOUND_PROMPT = "Could not find map image: {image_path}\nPlease locate the correct image file."
    ELEMENTS_OOB_REMOVED = "Removed {removed_elements} elements that were outside the map boundaries.\nMap size: {image_width}x{image_height}"
    IMG_LOAD_FAIL = "Failed to load image {found_image_path}:\n{error}\nLoading default empire background instead."
    MAP_LOAD_FAIL = "Error loading empire map: {error}\nLoading default empire background."
    DUP_OUR_CITY_MSG = "There is already an 'Our City'. Remove it first."
    DEL_BORDER_CONFIRM = "Are you sure you want to delete the empire border?"
    START_NEW_BORDER_MSG = "An empire border already exists. Start a new one and discard the current border?"
    INVALID_IMG_MSG = "Could not load image file:\n{selected_image}"

    # Background validation
    ELEMENTS_OOB_MSG = "Some elements do not fit in the selected background:\n\n{elements}\n\nThese elements will be removed or hidden. Are you sure you want to continue?"
    IMG_LOAD_ERR_MSG = "Failed to load image: {error}"
    MAP_LOAD_ERR_MSG = "Error loading empire map: {error}"

    TR_EXISTS_MSG = "This city already has a trade route. Do you want to replace it?"
    DEL_TR_MSG = "Are you sure you want to delete this trade route?"

    NO_BG_MSG = "Drop onto the background image area."
    INCOMPLETE_BORDER_MSG = "You have not closed the border shape. Would you like to save this border shape?"
    INCOMPLETE_TR_MSG = "This trade route doesn't end on our city. Would you like to save it anyway?"

    MOVE_OUR_CITY_MSG = "Move 'Our City' from ({old_x}, {old_y}) to ({new_x}, {new_y})?"

    MOVE_CITY_MSG = "Move city '{city_name}' to ({x}, {y})?"
    DEL_CITY_MSG = "Are you sure you want to delete city '{city_name}'?"
    DEL_BORDER_MSG = "Are you sure you want to delete the empire border?"

    # File Filters
    XML_FILES = "XML Files (*.xml);;All Files (*)"
    IMAGE_FILES = "Image Files (*.png *.jpg *.jpeg *.bmp *.gif);;All Files (*)"

    # Button Labels
    BROWSE = "Browse..."
    DEFAULT_BG = "Default Background"
    YES = "Yes"
    NO = "No"
    OK = "OK"
    CANCEL = "Cancel"
    SAVE = "Save"
    DONT_SAVE = "Don't Save"

    # Menu Labels
    DEL_TR_MENU = "Delete Trade Route"
    EDIT_CITY = "Edit City"
    MOVE_CITY = "Move City"
    DEL_CITY_MENU = "Delete City"
    DEL_BORDER_MENU = "Delete Border"
    EDIT_BORDER = "Edit Border Properties"

    # Status Messages
    LOADING_BG = "Loading background image from empire map info"
    LOADING_DEFAULT = "loading default empire map"
    EMP_LOADED_STATUS = "Empire loaded successfully"
    EMP_SAVED = "Empire saved successfully"
    NO_CHANGES = "No changes to save"

    # Validation Messages
    INVALID_COORDS = "Invalid coordinates: ({x}, {y})"
    CITY_NAME_REQ = "City name is required"
    TR_INCOMPLETE = "Trade route must have at least 2 points"
    BORDER_INCOMPLETE = "Border must have at least 3 points"

    # URLs
    GITHUB_AUGUSTUS = "https://github.com/Keriew/augustus/tree/master?tab=readme-ov-file"
    GITHUB_EDITOR = "https://github.com/Sephirex95/empire-editor-augustus"
    GITHUB_CUSTOM = "https://github.com/Keriew/augustus/discussions/734"
