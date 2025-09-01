"""
Default Cities Management Module

This module handles the population and management of the default cities menu,
including loading city data from JSON, creating menu hierarchies, and handling
city placement/removal based on predefined coordinates.
"""

import json
import os
import sys
from typing import Dict, Any, Optional, List

from PySide6 import QtWidgets as QWI, QtGui as QGU
import empire_data as ed


class DefaultCitiesManager:
    """Manages the default cities menu and functionality."""

    def __init__(self, main_window, logger):
        """Initialize the default cities manager.

        Args:
            main_window: Reference to the main window instance
        """
        self.main_window = main_window
        self.logger = logger  # Logger instance
        self.cities_data: Dict[str, Any] = {}
        self.region_actions: Dict[str, QGU.QAction] = {}
        self.city_actions: Dict[str, List[QGU.QAction]] = {}
        self.select_all_regions_action: Optional[QGU.QAction] = None

    def populate_menu(self):
        """Populate the Default Cities menu with hierarchical regions and cities from JSON."""
        try:
            # Handle PyInstaller bundle paths
            if getattr(sys, "frozen", False):
                # Running in PyInstaller bundle
                base_path = sys._MEIPASS
            else:
                # Running in normal Python environment
                base_path = os.path.dirname(os.path.abspath(__file__))

            json_path = os.path.join(
                base_path,
                "augustus_assets",
                "Areldir_maps",
                "cities_grouped.json",
            )

            if not os.path.exists(json_path):
                self.logger.debug(f"Cities JSON file not found: {json_path}")
                return

            with open(json_path, "r", encoding="utf-8") as f:
                self.cities_data = json.load(f)

            # Clear existing menu items
            self.main_window.ui.menuDefaultCities.clear()
            # Reset tracking dictionaries
            self.region_actions = {}
            self.city_actions = {}
            self.select_all_regions_action = None

            # Get the current background map name
            current_map_name = self._get_current_map_name()
            if not current_map_name:
                # No background set, show message
                no_bg_action = QGU.QAction("No background set - select a background first", self.main_window)
                no_bg_action.setEnabled(False)
                self.main_window.ui.menuDefaultCities.addAction(no_bg_action)
                return

            select_all_regions_action = QGU.QAction("Add all", self.main_window)
            select_all_regions_action.setCheckable(True)

            # Create region menus with cities
            for region_name, cities in self.cities_data.items():
                # Check if any cities in this region have coordinates for current map
                available_cities = []
                for city_name, city_data in cities.items():
                    map_data = city_data.get("default_map", {}).get(current_map_name)
                    if map_data:
                        # Check if city coordinates fit within current background bounds
                        if self._city_fits_on_current_background(map_data.get("x"), map_data.get("y")):
                            available_cities.append((city_name, city_data))

                # Only create region menu if it has cities for current map
                if not available_cities:
                    continue

                # Create region submenu
                region_menu = self.main_window.ui.menuDefaultCities.addMenu(region_name)

                # Create a "Select All" action for the region
                select_all_action = QGU.QAction(f"Select All {region_name}", self.main_window)
                select_all_action.setCheckable(True)
                select_all_action.triggered.connect(
                    lambda checked, region=region_name: self.on_region_select_all(region, checked)
                )
                region_menu.addAction(select_all_action)
                self.region_actions[region_name] = select_all_action

                # Add separator
                region_menu.addSeparator()

                # Add individual city actions (only for available cities)
                region_city_actions = []
                for city_name, city_data in available_cities:
                    city_action = QGU.QAction(city_name, self.main_window)
                    city_action.setCheckable(True)
                    city_action.triggered.connect(
                        lambda checked, city=city_name, region=region_name: self.on_city_selected(region, city, checked)
                    )
                    region_menu.addAction(city_action)
                    region_city_actions.append(city_action)

                self.city_actions[region_name] = region_city_actions

            # Add "Add all" action at the top if there are any regions
            if self.region_actions:
                select_all_regions_action.triggered.connect(self.on_select_all_regions)
                self.select_all_regions_action = select_all_regions_action
                # Insert at the beginning of the menu
                acts = self.main_window.ui.menuDefaultCities.actions()
                if acts:
                    self.main_window.ui.menuDefaultCities.insertAction(acts[0], select_all_regions_action)
                else:
                    self.main_window.ui.menuDefaultCities.addAction(select_all_regions_action)

                # Add a separator after the "Add all" action
                self.main_window.ui.menuDefaultCities.addSeparator()

        except Exception as e:
            self.logger.debug(f"Error populating Default Cities menu: {e}")

    def update_menu_state(self):
        """Enable/disable Default Cities menu based on background type."""
        # Enable menu only for predefined map types
        should_enable = self.main_window.bg_type in [
            ed.EmpBackgroundTypes.BIG_MAP,
            ed.EmpBackgroundTypes.NORTH_MAP,
            ed.EmpBackgroundTypes.SOUTH_MAP,
        ]

        self.main_window.ui.menuDefaultCities.setEnabled(should_enable)

        # If enabled, sync the menu state with loaded cities
        if should_enable:
            self.sync_menu_with_loaded_empire()

    def sync_menu_with_loaded_empire(self):
        """Sync the default cities menu checkboxes with cities already loaded in the empire."""
        if not self.main_window.state.current_empire_object or not hasattr(
            self.main_window.state.current_empire_object, "cities"
        ):
            return

        if not self.cities_data or not self.city_actions:
            return

        current_map_name = self._get_current_map_name()
        if not current_map_name or current_map_name == ed.EmpBackgroundTypes.CUSTOM:
            return

        # Get all cities currently in the empire
        loaded_cities = self.main_window.state.current_empire_object.cities

        # Clear all checkboxes first
        for region_name, region_city_actions in self.city_actions.items():
            for action in region_city_actions:
                action.setChecked(False)

        # Check cities that match default city positions
        for loaded_city in loaded_cities:
            # Try to find this city in the default cities data
            for region_name, cities in self.cities_data.items():
                for city_name, city_data in cities.items():
                    map_data = city_data.get("default_map", {}).get(current_map_name)
                    if map_data:
                        expected_x = map_data.get("x")
                        expected_y = map_data.get("y")

                        # Check if the loaded city matches this default city position (within tolerance)
                        if (
                            expected_x is not None
                            and expected_y is not None
                            and abs(loaded_city.x - expected_x) <= 5  # 5 pixel tolerance
                            and abs(loaded_city.y - expected_y) <= 5
                        ):
                            # Find the corresponding action and check it
                            if region_name in self.city_actions:
                                for action in self.city_actions[region_name]:
                                    if action.text() == city_name:
                                        action.setChecked(True)
                                        break
                            break

        # Update the "Select All" states for each region
        for region_name in self.region_actions:
            self._update_region_select_all_state(region_name)

        # Update the main "Add all" state
        self._update_main_select_all_state()

    def untick_city_if_removed(self, city):
        """Untick a city in the default cities menu if it was removed."""
        if not self.cities_data or not self.city_actions:
            return

        city_name = city.name
        current_map_name = self._get_current_map_name()

        if not current_map_name:
            return

        # Search for the city in all regions
        for region_name, cities in self.cities_data.items():
            if city_name in cities:
                city_data = cities[city_name]
                map_data = city_data.get("default_map", {}).get(current_map_name, {})

                # Check if this matches the coordinates of the removed city
                if map_data.get("x") == city.x and map_data.get("y") == city.y:
                    # Find and untick the corresponding menu action
                    if region_name in self.city_actions:
                        for action in self.city_actions[region_name]:
                            if action.text() == city_name:
                                action.setChecked(False)
                                # Update the region "Select All" state
                                self._update_region_select_all_state(region_name)
                                return

    def place_city(self, region_name: str, city_name: str):
        """Place a default city on the map using coordinates from JSON."""
        try:
            current_map_name = self._get_current_map_name()
            if not current_map_name or not self.cities_data:
                return

            # Get city data from JSON
            city_data = self.cities_data.get(region_name, {}).get(city_name, {})
            map_data = city_data.get("default_map", {}).get(current_map_name, {})

            if not map_data:
                self.logger.debug(f"No coordinates found for {city_name} on {current_map_name}")
                return

            x = map_data.get("x")
            y = map_data.get("y")

            if x is None or y is None:
                self.logger.debug(f"Invalid coordinates for {city_name}: x={x}, y={y}")
                return

            # Get the Empire reference from main window's state
            empire = self.main_window.state.current_empire_object if self.main_window.state else None

            # Check if city already exists at this location to avoid duplicates
            if self.main_window.state.check_if_empire():
                for existing_city in empire.cities:
                    if (
                        existing_city.name == city_name
                        and abs(existing_city.x - x) <= 2
                        and abs(existing_city.y - y) <= 2
                    ):
                        # City already exists at this location, don't add duplicate
                        self.logger.debug(f"City {city_name} already exists at ({x}, {y})")
                        return

            # Create a city object and map the type from JSON
            city = ed.City(city_name, x, y)
            city.city_type = ed.CityType.ROMAN
            # Use unified method to add the city properly
            self.main_window.add_city_to_empire(city)
        except Exception as e:
            self.logger.debug(f"Error placing city {city_name}: {e}")

    def remove_city(self, region_name: str, city_name: str):
        """Remove a default city from the map."""
        try:
            if not self.main_window.state.check_if_empire():
                return

            current_map_name = self._get_current_map_name()

            # Get expected coordinates for this default city
            expected_coords = None
            if self.cities_data and current_map_name:
                city_data = self.cities_data.get(region_name, {}).get(city_name, {})
                map_data = city_data.get("default_map", {}).get(current_map_name, {})
                if map_data:
                    expected_x = map_data.get("x")
                    expected_y = map_data.get("y")
                    if expected_x is not None and expected_y is not None:
                        expected_coords = (expected_x, expected_y)

            # Get the Empire reference from main window's state
            empire = self.main_window.state.current_empire_object if self.main_window.state else None

            # Find and remove cities that match the name and location (if known)
            cities_to_remove = []
            for city in empire.cities:
                if city.name == city_name:
                    # If we know the expected coordinates, only remove cities at that location
                    if expected_coords:
                        expected_x, expected_y = expected_coords
                        if abs(city.x - expected_x) <= 5 and abs(city.y - expected_y) <= 5:
                            cities_to_remove.append(city)
                    else:
                        # If we don't know expected coordinates, remove all cities with this name
                        cities_to_remove.append(city)

            # Remove the identified cities
            for city in cities_to_remove:
                empire.cities.remove(city)
                self.main_window.Manager.remove_city(city)

                # Remove name label if it exists using proper key
                city_key = id(city)
                if city_key in self.main_window.city_labels:
                    try:
                        text_item = self.main_window.city_labels[city_key]
                        if hasattr(text_item, "bg_rect"):
                            self.main_window.scene.removeItem(text_item.bg_rect)
                        self.main_window.scene.removeItem(text_item)
                        del self.main_window.city_labels[city_key]
                    except (RuntimeError, KeyError):
                        pass

            if cities_to_remove:
                self.logger.debug(f"Removed {len(cities_to_remove)} instance(s) of {city_name}")

        except Exception as e:
            self.logger.debug(f"Error removing city {city_name}: {e}")

    # Event handlers
    def on_select_all_regions(self, checked: bool):
        """Handle the top-level "Add all" checkbox that selects/deselects all regions and cities."""
        # Toggle all region "Select All" actions
        for region_name in self.region_actions:
            region_action = self.region_actions[region_name]
            region_action.setChecked(checked)
            # This will trigger the region's select all logic
            self.on_region_select_all(region_name, checked)

    def on_region_select_all(self, region_name: str, checked: bool):
        """Handle region "Select All" checkbox."""
        if region_name in self.city_actions:
            for city_action in self.city_actions[region_name]:
                city_action.setChecked(checked)
                # Also trigger the city selection logic
                city_name = city_action.text()
                self.on_city_selected(region_name, city_name, checked)

    def on_city_selected(self, region_name: str, city_name: str, checked: bool):
        """Handle individual city selection."""
        self.logger.debug(f"City {city_name} in {region_name}: {'selected' if checked else 'deselected'}")

        # Update region "Select All" state based on individual city states
        if region_name in self.city_actions and region_name in self.region_actions:
            region_action = self.region_actions[region_name]
            city_actions = self.city_actions[region_name]

            # Check if all cities are selected
            all_selected = all(action.isChecked() for action in city_actions)

            # Update region action state
            region_action.setChecked(all_selected)

        # Update the main "Add all" action state
        self._update_main_select_all_state()

        # Place or remove the city on the map
        if checked:
            self.place_city(region_name, city_name)
        else:
            self.remove_city(region_name, city_name)

    # Private helper methods
    def _get_current_map_name(self) -> str:
        """Get the current map name based on background type."""
        if self.main_window.bg_type == ed.EmpBackgroundTypes.BIG_MAP:
            return "Orbis Terrarum"
        elif self.main_window.bg_type == ed.EmpBackgroundTypes.NORTH_MAP:
            return "Occidentalis"
        elif self.main_window.bg_type == ed.EmpBackgroundTypes.SOUTH_MAP:
            return "Orientalis"
        else:
            if self.main_window.bg_item is not None:
                return ed.EmpBackgroundTypes.CUSTOM
            else:
                return ed.EmpBackgroundTypes.NONE

    def _city_fits_on_current_background(self, x: Optional[int], y: Optional[int]) -> bool:
        """Check if city coordinates fit within current background image bounds."""
        if x is None or y is None:
            return False

        if not self.main_window.bg_item:
            return True  # No background set, allow all

        # Get background image dimensions
        pixmap = self.main_window.bg_item.pixmap()
        if pixmap.isNull():
            return True

        bg_width = pixmap.width()
        bg_height = pixmap.height()

        # Check if coordinates are within bounds (with some margin for city icon size)
        margin = 50  # Allow some margin for city icon
        return x >= 0 and x < bg_width - margin and y >= 0 and y < bg_height - margin

    def _update_region_select_all_state(self, region_name: str):
        """Update the Select All action state for a region based on its cities."""
        if region_name not in self.region_actions or region_name not in self.city_actions:
            return

        region_action = self.region_actions[region_name]
        city_actions = self.city_actions[region_name]

        # Check if all cities are checked
        all_checked = all(action.isChecked() for action in city_actions)

        # Update the region action state
        region_action.setChecked(all_checked)

        # Also update the main "Add all" state
        self._update_main_select_all_state()

    def _update_main_select_all_state(self):
        """Update the main 'Add all' action state based on all region states."""
        if not self.select_all_regions_action:
            return

        # Check if all region "Select All" actions are checked
        all_regions_selected = all(region_action.isChecked() for region_action in self.region_actions.values())

        # Update the main action state
        self.select_all_regions_action.setChecked(all_regions_selected)
