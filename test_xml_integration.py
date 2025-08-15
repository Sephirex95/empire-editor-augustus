#!/usr/bin/env python3
"""
Test script to verify XML empire file operations work correctly.
This tests the integration between empire_data.py XML methods and main_window.py
"""

import os
import sys
import tempfile
from pathlib import Path

# Add the current directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import empire_data as ed


def test_empire_xml_operations():
    """Test basic XML read/write operations for Empire objects."""
    print("Testing Empire XML operations...")
    
    # Create a test empire with some sample data
    print("  1. Creating test empire...")
    empire = ed.Empire(
        version=1,
        ornaments=[
            ed.Ornament(ed.OrnamentType.COLOSSEUM)
        ],
        border=ed.Border(
            density=28,
            edges=[
                ed.Edge(100, 100, False),
                ed.Edge(200, 100, False),
                ed.Edge(200, 200, False),
                ed.Edge(100, 200, False)
            ]
        ),
        cities=[
            ed.City(
                name="Rome",
                x=150,
                y=150,
                type=ed.CityType.OURS,
                buys=[ed.Resource(ed.ResourceType.WHEAT, 10)],
                sells=[ed.Resource(ed.ResourceType.MEAT, 5)],
                trade_route=ed.TradeRoute(
                    cost=100,
                    type=ed.TradeRouteType.LAND,
                    trade_points=[
                        ed.TradePoint(160, 160),
                        ed.TradePoint(180, 180)
                    ]
                )
            ),
            ed.City(
                name="Trading Post",
                x=300,
                y=300,
                type=ed.CityType.TRADE,
                buys=[ed.Resource(ed.ResourceType.FRUIT, 8)],
                sells=[ed.Resource(ed.ResourceType.FISH, 6)]
            )
        ],
        invasion_paths=[
            ed.InvasionPath([
                ed.Battle(250, 250)
            ])
        ],
        distant_battle_paths=[
            ed.DistantBattlePath(
                type=ed.DistantPathType.ROMAN,
                start_x=400,
                start_y=400,
                waypoints=[
                    ed.Waypoint(12, 450, 450),
                    ed.Waypoint(6, 500, 500)
                ]
            )
        ]
    )
    
    # Test XML string conversion
    print("  2. Testing XML string conversion...")
    xml_string = empire.to_xml_string()
    assert xml_string, "XML string should not be empty"
    assert "<?xml version=\"1.0\"?>" in xml_string, "XML declaration should be present"
    assert "<!DOCTYPE empire>" in xml_string, "DOCTYPE should be present"
    assert "<empire version=\"1\">" in xml_string, "Empire root element should be present"
    assert "<city name=\"Rome\"" in xml_string, "Rome city should be in XML"
    assert "<city name=\"Trading Post\"" in xml_string, "Trading Post city should be in XML"
    print("    ✓ XML string generation successful")
    
    # Test XML file writing and reading
    print("  3. Testing XML file write/read...")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as tmp_file:
        temp_path = tmp_file.name
    
    try:
        # Write to file
        empire.write_xml(temp_path)
        assert os.path.exists(temp_path), "XML file should be created"
        print("    ✓ XML file writing successful")
        
        # Read from file
        loaded_empire = ed.Empire.read_xml(temp_path)
        assert loaded_empire is not None, "Loaded empire should not be None"
        assert loaded_empire.version == empire.version, "Version should match"
        assert len(loaded_empire.cities) == len(empire.cities), "Number of cities should match"
        assert loaded_empire.cities[0].name == "Rome", "First city name should match"
        assert loaded_empire.cities[1].name == "Trading Post", "Second city name should match"
        assert loaded_empire.border is not None, "Border should be loaded"
        assert len(loaded_empire.border.edges) == 4, "Number of border edges should match"
        print("    ✓ XML file reading successful")
        
        # Test XML string parsing
        print("  4. Testing XML string parsing...")
        parsed_empire = ed.Empire.from_xml_string(xml_string)
        assert parsed_empire is not None, "Parsed empire should not be None"
        assert parsed_empire.cities[0].name == "Rome", "Parsed city name should match"
        print("    ✓ XML string parsing successful")
        
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)
    
    print("✓ All Empire XML operations tests passed!")


def test_ui_integration_compatibility():
    """Test that the methods used by main_window.py are available and working."""
    print("Testing UI integration compatibility...")
    
    # Test that all required methods exist
    print("  1. Checking required methods exist...")
    
    # Class methods for reading
    assert hasattr(ed.Empire, 'read_xml'), "Empire.read_xml method should exist"
    assert hasattr(ed.Empire, 'from_xml_string'), "Empire.from_xml_string method should exist"
    print("    ✓ Reading methods available")
    
    # Instance methods for writing
    test_empire = ed.Empire(version=1)
    assert hasattr(test_empire, 'write_xml'), "Empire.write_xml method should exist"
    assert hasattr(test_empire, 'to_xml_string'), "Empire.to_xml_string method should exist"
    print("    ✓ Writing methods available")
    
    # Test that empire objects have expected attributes for UI rendering
    print("  2. Checking empire object structure...")
    empire = ed.Empire(
        version=1,
        cities=[
            ed.City(name="Test", x=100, y=100, type=ed.CityType.OURS)
        ]
    )
    
    assert hasattr(empire, 'cities'), "Empire should have cities attribute"
    assert hasattr(empire, 'border'), "Empire should have border attribute"
    assert hasattr(empire.cities[0], 'name'), "City should have name attribute"
    assert hasattr(empire.cities[0], 'x'), "City should have x attribute"
    assert hasattr(empire.cities[0], 'y'), "City should have y attribute"
    assert hasattr(empire.cities[0], 'type'), "City should have type attribute"
    assert hasattr(empire.cities[0], 'trade_route'), "City should have trade_route attribute"
    print("    ✓ Empire structure compatible with UI")
    
    print("✓ UI integration compatibility tests passed!")


if __name__ == "__main__":
    print("Running Empire Editor XML Integration Tests...")
    print("=" * 50)
    
    try:
        test_empire_xml_operations()
        print()
        test_ui_integration_compatibility()
        print()
        print("=" * 50)
        print("🎉 All tests passed! XML integration is working correctly.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
