# Empire Editor XML File Operations

## Overview

The Empire Editor now supports opening and saving empire data to/from XML files through the main window interface. This functionality connects the XML serialization methods in `empire_data.py` with the user interface in `main_window.py`.

## Features Added

### Menu Actions

Two new menu options have been added to the **File** menu:

- **Open Empire XML** (Ctrl+O) - Load an empire from an XML file
- **Save Empire XML** (Ctrl+S) - Save the current empire to an XML file

### XML File Operations

#### Opening Empire XML Files

When you select "Open Empire XML":

1. A file dialog opens allowing you to select an XML file
2. If you have unsaved changes, you'll be prompted to confirm loading the new empire
3. The XML file is parsed and loaded into the editor
4. All empire data is rendered on the map including:
   - Cities with their correct types and positions
   - Empire borders (if defined)
   - Trade routes (if defined)
   - Other empire elements

#### Saving Empire XML Files

When you select "Save Empire XML":

1. A file dialog opens allowing you to choose where to save the XML file
2. The current empire data is serialized to XML format
3. The file is saved with proper XML formatting including:
   - XML declaration
   - DOCTYPE declaration
   - Pretty-printed structure

### Supported Empire Elements

The XML operations support all empire data elements:

- **Cities**: Name, position, type (ours/trade/distant/etc.), buying/selling resources, trade routes
- **Empire Border**: Border edges with density and hidden flags
- **Trade Routes**: Land/sea routes with waypoints
- **Ornaments**: Decorative map elements
- **Invasion Paths**: Battle locations
- **Distant Battle Paths**: Remote battle campaigns

## Technical Implementation

### Key Methods Added

#### main_window.py

- `open_empire_xml()` - Handles opening XML files with error handling and UI updates
- `save_empire_xml()` - Handles saving XML files with proper file extensions
- `_render_loaded_empire()` - Renders all loaded empire data onto the scene
- `_place_city_on_scene()` - Places individual cities on the map
- `_render_trade_route_for_city()` - Renders trade route visualizations

#### empire_data.py

XML serialization methods were already present:

- `Empire.read_xml(path)` - Class method to load empire from XML file
- `Empire.from_xml_string(xml_text)` - Class method to parse empire from XML string
- `Empire.write_xml(path)` - Instance method to save empire to XML file
- `Empire.to_xml_string()` - Instance method to serialize empire to XML string

### Error Handling

The implementation includes comprehensive error handling:

- File not found errors
- XML parsing errors
- Invalid empire data
- Unsaved changes warnings
- User-friendly error messages

### Data Preservation

When loading an empire:

- Existing background images are preserved if loaded
- Scene state is properly cleared before loading new data
- All UI elements are properly updated
- Visual rendering matches the loaded data

## Usage Notes

1. **File Extensions**: When saving, if you don't specify a `.xml` extension, it will be added automatically.

2. **Background Images**: Loading an empire XML file doesn't include background images - these need to be loaded separately through "Map Settings > Select background Image".

3. **Data Validation**: The XML parser validates the structure and will show error messages for invalid files.

4. **Keyboard Shortcuts**: Use Ctrl+O and Ctrl+S for quick access to open and save operations.

## Example Workflow

1. Start the Empire Editor
2. Load a background image (Map Settings > Select background Image)
3. Create cities, borders, and trade routes using the editor tools
4. Save your work (Ctrl+S or File > Save Empire XML)
5. Later, load your saved empire (Ctrl+O or File > Open Empire XML)
6. Continue editing or export for use in your game

## Compatibility

The XML format is compatible with the Caesar III/Augustus empire map format, making it easy to:

- Import existing empire maps
- Export maps for use in the game
- Share empire designs with others
- Backup and version control empire designs

## Testing

Run `test_xml_integration.py` to verify that all XML operations are working correctly. This test validates:

- XML string generation and parsing
- File reading and writing operations
- Data integrity through save/load cycles
- UI integration compatibility
