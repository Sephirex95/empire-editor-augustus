# program_state.py
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 27 22:26:08 2025

@author: sephirex95
"""

import os
import sys
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QMessageBox, QFileDialog
import empire_data as ed
from sg_reader_light import SgFileReader
from enum import Enum, auto
from PIL import Image


class EmpObjTypes(Enum):
    EMPIRE_EDGE = auto()
    LAND_DOT = auto()
    SEA_DOT = auto()
    TRADE_FLAG = auto()
    ROMAN_FLAG = auto()
    DISTANT_FLAG = auto()
    OUR_FLAG = auto()
    OUR_LEGION = auto()
    NATIVES = auto()
    DISTANT_BATTLE = auto()


class ProgramState:
    def __init__(self):
        self.images = {}
        self.selected_empire_image = None
        self.city_icons_map = {}
        self.init_failed = False
        self.current_empire_object = None
        # paths + feature fields
        self.c3_main_path = ""
        self.augustus_user_path = ""
        self.augustus_editor_empires_path = ""
        self.augustus_community_image_path = ""
        self.snap_enabled = False
        self.snap_distance = 0

        config_path = os.path.join(os.path.dirname(__file__), "empire_editor.cfg")
        self.settings = QSettings(config_path, QSettings.Format.IniFormat)
        # --- SLAP IN DEFAULTS (only if not set yet) ---
        s = self.settings
        s.beginGroup("features")
        if s.value("tp_snap_enabled") is None:
            s.setValue("tp_snap_enabled", True)
        if s.value("tp_snap_distance") is None:
            s.setValue("tp_snap_distance", 5)
        s.endGroup()
        s.beginGroup("graphics")
        if s.value("disable_high_dpi_scaling") is None:
            s.setValue("disable_high_dpi_scaling", True)
        s.endGroup()
        s.sync()
        # instaload
        self.snap_enabled = s.value("features/tp_snap_enabled", True, bool)
        self.snap_distance = s.value("features/tp_snap_distance", 5, int)
        self.disable_dpi_scaling = s.value("graphics/disable_high_dpi_scaling", True, bool)

    def init(self):
        if not self.load_c3_folder():
            self.init_failed = True
            return False
        self.select_augustus_user_directory()
        self.apply_settings_from_store()  # keep local fields in sync
        self.load_images()
        return not self.init_failed

    def apply_settings_from_store(self):
        """Refresh cached fields from QSettings (call after any dialog saves)."""
        s = self.settings
        self.c3_main_path = s.value("c3_main_folder", "", str)
        self.augustus_user_path = s.value("augustus_user_folder", "", str)
        self.snap_enabled = s.value("features/tp_snap_enabled", False, bool)
        self.snap_distance = s.value("features/tp_snap_distance", 0, int)
        self.disable_dpi_scaling = s.value("graphics/disable_high_dpi_scaling", True, bool)
        # derive convenience paths
        if self.augustus_user_path:
            self.augustus_community_image_path = os.path.join(self.augustus_user_path, "community", "image")
            self.augustus_editor_empires_path = os.path.join(self.augustus_user_path, "editor", "empires")
        else:
            self.augustus_community_image_path = ""
            self.augustus_editor_empires_path = ""

    # --- helpers to keep set/get tidy (optional) ---------------------------
    def set_snap_enabled(self, enabled: bool):
        self.settings.setValue("features/tp_snap_enabled", bool(enabled))
        self.snap_enabled = bool(enabled)

    def set_snap_distance(self, value: int):
        self.settings.setValue("features/tp_snap_distance", int(value))
        self.snap_distance = int(value)

    def _create_my_empires_folder(self, settings):
        """Helper function to create my_empires folder and set default_save_folder setting."""
        # Determine the correct application root directory
        if getattr(sys, "frozen", False):
            # Running as PyInstaller executable - use the directory containing the .exe
            app_root = os.path.dirname(sys.executable)
        else:
            # Running in normal Python environment
            app_root = os.path.dirname(os.path.abspath(__file__))

        my_empires_folder = os.path.join(app_root, "my_empires")

        try:
            os.makedirs(my_empires_folder, exist_ok=True)
            settings.setValue("default_save_folder", my_empires_folder)
            print(f"Created my_empires folder at: {my_empires_folder}")
            return True
        except OSError as e:
            print(f"Could not create my_empires folder: {e}")
            # Fall back to application root as default save folder
            settings.setValue("default_save_folder", app_root)
            return False

    def load_c3_folder(self):
        s = self.settings
        self.c3_main_path = s.value("c3_main_folder", "", str)

        if not self.c3_main_path:
            QMessageBox.information(
                None,
                "Select Caesar 3 Folder",
                "Please select your Caesar 3 installation folder.\n\n"
                "This should be the folder that contains C3.sg2 and augustus.exe files.",
                QMessageBox.StandardButton.Ok,
            )
            folder = QFileDialog.getExistingDirectory(
                None, "Select Caesar 3 Main Directory", "", QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
            )
            if folder and self.validate_c3_directory(folder):
                s.setValue("c3_main_folder", folder)
                self.c3_main_path = folder

                # Create 'my_empires' folder using helper function
                self._create_my_empires_folder(s)

                return True
            else:
                QMessageBox.critical(
                    None, "Invalid Folder", "Please select a valid Caesar 3 directory.", QMessageBox.StandardButton.Ok
                )
                return False
        else:
            default_save_folder = s.value("default_save_folder", "", str)
            if not default_save_folder or not os.path.exists(default_save_folder):
                self._create_my_empires_folder(s)
        return True

    def validate_c3_directory(self, path: str) -> bool:
        required_files = ["C3.sg2", "augustus.exe"]
        missing = [file for file in required_files if not os.path.isfile(os.path.join(path, file))]
        if missing:
            QMessageBox.critical(
                None,
                "Missing Files",
                "The following required files are missing:\n" + "\n".join(missing),
                QMessageBox.StandardButton.Ok,
            )
            return False
        return True

    def select_augustus_user_directory(self) -> bool:
        """
        Politely ask the user if they'd like to select their Augustus *user* directory.
        - Stores the path in QSettings under 'augustus_user_folder'
        - Sets self.augustus_user_path on success
        - Returns True if a valid directory is stored/confirmed, False otherwise
        """
        s = self.settings
        existing = s.value("augustus_user_folder", "", str)
        if existing and os.path.isdir(existing):
            self.augustus_user_path = existing
            return True

        # If there was a stale path, let the user know (without forcing them).
        if existing and not os.path.isdir(existing):
            print(f"Previously configured Augustus user folder '{existing}' no longer exists.")

        # Ask nicely (do not force selection).
        reply = QMessageBox.question(
            None,
            "Select Augustus User Directory",
            "Would you like to select your Augustus user directory?\n\n"
            "This will help sync your Augustus and map editor with the Empire Editor outputs.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if reply != QMessageBox.StandardButton.Yes:
            # User declined; that's okay—just return False to signal nothing was set.
            return False

        # Let the user pick a directory (optional, but requested).
        folder = QFileDialog.getExistingDirectory(
            None, "Select Augustus User Directory", "", QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if not folder:
            # User cancelled the file dialog; nothing selected.
            return False

        if self.validate_augustus_user_directory(folder):
            s.setValue("augustus_user_folder", folder)
            self.augustus_user_path = folder
            self.augustus_community_image_path = os.path.join(folder, "community", "image")
            self.augustus_editor_empires_path = os.path.join(folder, "editor", "empires")
            return True

        # Folder chosen but failed validation.
        QMessageBox.critical(
            None, "Invalid Directory", "Please select a valid Augustus user directory.", QMessageBox.StandardButton.Ok
        )
        return False

    def validate_augustus_user_directory(self, path: str) -> bool:
        """
        Validate an Augustus *user* directory.
        Because user directories differ by OS/installs, we accept the directory if it
        contains at least one recognizable Augustus user artifact.

        Accepted markers (any one is enough):
          - A 'maps', 'saves', 'savegames', or 'mods' subfolder

        Shows a message box listing what was expected when validation fails.
        """
        if not path or not os.path.isdir(path):
            QMessageBox.critical(
                None, "Invalid Directory", "The selected path is not a directory.", QMessageBox.StandardButton.Ok
            )
            return False

        expected_dirs = ["editor", "community", "savegames"]

        has_dir_marker = any(os.path.isdir(os.path.join(path, d)) for d in expected_dirs)

        if has_dir_marker:
            return True

        # Nothing recognizable found; explain what we looked for.
        missing_msg = (
            "The selected folder does not look like an Augustus user directory.\n\n"
            "Have not found the following subfolders:\n"
            f" {', '.join(expected_dirs)}\n"
        )
        QMessageBox.warning(None, "Missing Expected Items", missing_msg, QMessageBox.StandardButton.Ok)
        return False

    def get_city_icons_dict(self):
        return self.city_icons_map

    def load_images(self):
        if self.c3_main_path:
            c3_sg_path = os.path.join(self.c3_main_path, "C3.sg2")
            reader = SgFileReader(c3_sg_path)
            self.images = reader.load_filtered("The_empire", "empire_bits", "empire_panels")
            self.create_selectable_elements()

    def create_selectable_elements(self):
        try:

            def crop5x5(img):
                return img.crop((0, 0, 5, 5))  # (left, top, right, bottom), bottom is exclusive

            def overlay_flag_on_city(city_pil, flag_pil, x_offset=0, y_offset=0):
                """Overlay a flag image on the top-right corner of a city icon."""
                # Create a copy of the city image to avoid modifying the original
                result = city_pil.copy()
                # Position flag in top-right corner with small margin
                flag_x = x_offset
                flag_y = y_offset
                # Paste flag with alpha blending if possible
                if flag_pil.mode == "RGBA":
                    result.paste(flag_pil, (flag_x, flag_y), flag_pil)
                else:
                    result.paste(flag_pil, (flag_x, flag_y))

                return result

            # Get the augustus_assets path
            if getattr(sys, "frozen", False):
                # Running as PyInstaller executable
                app_root = os.path.dirname(sys.executable)
                ui_assets_path = os.path.join(app_root, "_internal", "augustus_assets", "Graphics", "UI")
            else:
                # Running in normal Python environment
                app_root = os.path.dirname(os.path.abspath(__file__))
                ui_assets_path = os.path.join(app_root, "augustus_assets", "Graphics", "UI")

            # augustus assets used via layering:
            bits = self.images["empire_bits"]
            self.images["sea_dot"] = crop5x5(bits[102])
            self.images["land_dot"] = crop5x5(bits[94])

            # Load Empire_Icon images from augustus assets
            self.images["construction"] = Image.open(os.path.join(ui_assets_path, "Empire_Icon_Construction_01.png"))
            self.images["dis_town"] = Image.open(os.path.join(ui_assets_path, "Empire_Icon_Distant_01.png"))
            self.images["dis_village"] = Image.open(os.path.join(ui_assets_path, "Empire_Icon_Distant_02.png"))
            self.images["purple_flag"] = Image.open(os.path.join(ui_assets_path, "Empire_Icon_Flag_01.png"))
            self.images["res_food"] = Image.open(os.path.join(ui_assets_path, "Empire_Icon_Resource_01.png"))
            self.images["res_goods"] = Image.open(os.path.join(ui_assets_path, "Empire_Icon_Resource_02.png"))
            self.images["tr_town"] = Image.open(os.path.join(ui_assets_path, "Empire_Icon_Roman_01.png"))
            self.images["ro_town"] = Image.open(os.path.join(ui_assets_path, "Empire_Icon_Roman_02.png"))
            self.images["tr_village"] = Image.open(os.path.join(ui_assets_path, "Empire_Icon_Roman_03.png"))
            self.images["ro_village"] = Image.open(os.path.join(ui_assets_path, "Empire_Icon_Roman_04.png"))
            self.images["ro_capital"] = Image.open(os.path.join(ui_assets_path, "Empire_Icon_Roman_05.png"))
            self.images["tr_sea"] = Image.open(os.path.join(ui_assets_path, "Empire_Icon_Trade_01.png"))
            self.images["tr_land"] = Image.open(os.path.join(ui_assets_path, "Empire_Icon_Trade_02.png"))

            # Store flag images separately
            self.images["our_flag"] = bits[2]
            self.images["capital_flag"] = overlay_flag_on_city(
                self.images["our_flag"], self.images["purple_flag"], 0, 0
            )
            self.images["trade_flag"] = bits[9]
            self.images["roman_flag"] = bits[16]
            self.images["distant_flag"] = bits[23]

            # Helper function to overlay flag on city icon

            # Create city icons with flags overlaid
            our_city_base = bits[0]
            roman_city_base = bits[7]
            distant_city_base = bits[21]

            # Create flagged versions
            our_city_with_flag = overlay_flag_on_city(our_city_base, self.images["our_flag"], 17, 5)
            roman_city_with_flag = overlay_flag_on_city(roman_city_base, self.images["roman_flag"], 22, 5)
            trade_city_with_flag = overlay_flag_on_city(roman_city_base, self.images["trade_flag"], 22, 5)
            distant_city_with_flag = overlay_flag_on_city(distant_city_base, self.images["distant_flag"], 12, 5)
            capital_with_flag = overlay_flag_on_city(self.images["ro_capital"], self.images["capital_flag"], 17, 5)

            construction_with_flag = overlay_flag_on_city(self.images["construction"], self.images["roman_flag"], 2, 6)

            dis_town_with_flag = overlay_flag_on_city(self.images["dis_town"], self.images["distant_flag"], 11, 5)
            dis_village_with_flag = overlay_flag_on_city(self.images["dis_village"], self.images["distant_flag"], 11, 5)

            res_food_with_flag = overlay_flag_on_city(self.images["res_food"], self.images["trade_flag"], 1, 6)
            res_goods_with_flag = overlay_flag_on_city(self.images["res_goods"], self.images["trade_flag"], 1, 6)

            tr_sea_with_flag = overlay_flag_on_city(self.images["tr_sea"], self.images["trade_flag"], 19, 6)
            tr_land_with_flag = overlay_flag_on_city(self.images["tr_land"], self.images["trade_flag"], 19, 6)

            # Towns & villages get flags too now
            tr_town_with_flag = overlay_flag_on_city(self.images["tr_town"], self.images["trade_flag"], 17, 6)
            ro_town_with_flag = overlay_flag_on_city(self.images["ro_town"], self.images["roman_flag"], 17, 6)

            tr_village_with_flag = overlay_flag_on_city(self.images["tr_village"], self.images["trade_flag"], 17, 6)
            ro_village_with_flag = overlay_flag_on_city(self.images["ro_village"], self.images["roman_flag"], 17, 6)

            self.city_icons_map = {
                "construction": construction_with_flag,
                "dis_town": dis_town_with_flag,
                "dis_village": dis_village_with_flag,
                "res_food": res_food_with_flag,
                "res_goods": res_goods_with_flag,
                "tr_town": tr_town_with_flag,
                "ro_town": ro_town_with_flag,
                "tr_village": tr_village_with_flag,
                "ro_village": ro_village_with_flag,
                "ro_capital": capital_with_flag,
                "tr_sea": tr_sea_with_flag,
                "tr_land": tr_land_with_flag,
                "our_city": our_city_with_flag,
                "ro_city": roman_city_with_flag,
                "tr_city": trade_city_with_flag,
                "dis_city": distant_city_with_flag,
            }

            # images from vanilla files
            self.elements = [
                {"name": "Our City", "pil": our_city_with_flag, "kind": ed.CityType.OURS, "enabled": True},
                {"name": "Roman City", "pil": roman_city_with_flag, "kind": ed.CityType.ROMAN, "enabled": True},
                {"name": "Trade City", "pil": trade_city_with_flag, "kind": ed.CityType.TRADE, "enabled": True},
                {"name": "Distant City", "pil": distant_city_with_flag, "kind": ed.CityType.DISTANT, "enabled": True},
                {"name": "Empire Edge", "pil": bits[71], "kind": EmpObjTypes.EMPIRE_EDGE, "enabled": True},
                # Hidden items (same icon different function)
                {
                    "name": "Vulnerable City",
                    "pil": roman_city_with_flag,
                    "kind": ed.CityType.VULNERABLE,
                    "enabled": False,
                },
                {
                    "name": "Future Trade City",
                    "pil": trade_city_with_flag,
                    "kind": ed.CityType.FUTURE_TRADE,
                    "enabled": False,
                },
                # Disabled items
                {"name": "Distant Battle", "pil": bits[28], "kind": EmpObjTypes.DISTANT_BATTLE, "enabled": False},
                {"name": "Our Legion", "pil": bits[36], "kind": EmpObjTypes.OUR_LEGION, "enabled": False},
                {"name": "Natives", "pil": bits[52], "kind": EmpObjTypes.NATIVES, "enabled": False},
            ]
        except (KeyError, IndexError):
            self.init_failed = True
            QMessageBox.critical(None, "Error", "Error loading selectable elements.", QMessageBox.StandardButton.Ok)

    def has_our_city(self):
        """Return (True, city) if an 'ours' city exists, else (False, None)."""
        e = self.current_empire_object
        if not e:
            return False, None
        for c in e.cities:
            if c.city_type == ed.CityType.OURS:
                return True, c
        return False, None

    def has_any_data(self):
        """Rough check if current empire has any content worth warning about."""
        e = self.current_empire_object
        if not e:
            return False
        if e.cities:
            return True
        if e.ornaments:
            return True
        if e.invasion_paths:
            return True
        if e.distant_battle_paths:
            return True
        b = e.border
        if b and b.edges:
            return True
        if e.map_info:
            if e.map_info.image != "" or e.map_info.width != 0 or e.map_info.height != 0:
                return True
        return False

    def check_if_empire(self):
        return self.current_empire_object is not None

    def clear_empire(self):
        """Clear current empire from state (but do not create a new one)."""
        self.current_empire_object = None

    def new_empire(self):
        """Create a completely new, clean empire."""
        # Always start with a clean version 1 empire (no map_info)
        self.current_empire_object = ed.Empire(version=1)
