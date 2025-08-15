# Center-Based Coordinate System Update Summary

## Overview

Updated the empire editor to treat all icon coordinates as center-based instead of top-left corner based. This aligns with how the actual game engine renders icons on the map.

## Key Changes Made

### 1. City Placement and Storage

**Before**: City coordinates (city.x, city.y) were stored as top-left corner positions
**After**: City coordinates (city.x, city.y) are now stored as center positions

- Updated `_place_city_on_scene()` to convert center coordinates to top-left for scene placement
- Updated `handle_city_drop()` to store center coordinates and convert to top-left for placement
- Updated `handle_icon_drop()` for city moving to properly handle center-based coordinates

### 2. City Hit Detection

Updated collision detection for trade route ending:
- `_trade_route_ends_at_city()`: Now uses center-based bounds checking
- Trade route drawing: Updated hit detection for "Our City" to use center-based bounds

### 3. Visual Icon Positioning

**Drag Cursor**: Updated mouse move event to center the floating icon on the cursor position
- Changed from top-left positioning to centering the icon on the cursor

### 4. Coordinate Helper Functions

**`_get_city_center()`**: Simplified since stored coordinates are already center-based
- Before: `return city.x + pixmap.width() // 2, city.y + pixmap.height() // 2`
- After: `return city.x, city.y`

### 5. Functions Already Correct

These functions were already using center-based positioning correctly:
- `render_empire_border()`: Uses `_place_pixmap()` with `center=True`
- `render_trade_route()`: Uses `_place_pixmap()` with `center=True` for trade dots
- `_place_pixmap()`: Already supports center positioning via `center` parameter

## Coordinate Conversion Pattern

Throughout the codebase, the pattern is now:

1. **Data Storage**: All city coordinates in empire data are stored as center positions
2. **Scene Placement**: Convert to top-left for Qt scene placement using:
   ```python
   top_left_x = center_x - pixmap.width() // 2
   top_left_y = center_y - pixmap.height() // 2
   ```
3. **Hit Detection**: Use center-based bounds:
   ```python
   half_width = pixmap.width() // 2
   half_height = pixmap.height() // 2
   if (city.x - half_width <= point.x <= city.x + half_width and 
       city.y - half_height <= point.y <= city.y + half_height):
   ```

## Files Modified

- `main_window.py`: Updated all coordinate handling logic

## Testing

- File compiles without syntax errors
- All coordinate conversions follow the consistent pattern
- XML save/load functionality maintains center-based coordinates
- Visual rendering uses proper center positioning for all icons

## Benefits

1. **Game Engine Compatibility**: Icons now render correctly matching the actual game engine
2. **Consistent Positioning**: All icons (cities, empire borders, trade routes) use center-based positioning
3. **Accurate Hit Detection**: Click detection properly accounts for icon centers
4. **Improved User Experience**: Dragging icons feels more natural with center-based cursor positioning

## Technical Notes

- The `_place_pixmap()` function was already designed to handle center positioning
- Qt scene items still use top-left positioning internally, but we convert at placement time
- All empire data (XML) stores center coordinates, maintaining consistency
- Border and trade route icons were already using center positioning via the `center=True` parameter
