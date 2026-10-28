#!/usr/bin/env python3
"""
Cartesian to Polar G-code Post-Processor
Converts Cura's Cartesian G-code (X,Y in mm) to Polar coordinates (angle, radius)

Usage:
    ./cartesian_to_polar.py input.gcode > output.ngc
    
Or as a LinuxCNC filter:
    Set PROGRAM_EXTENSION = .gcode cartesian_to_polar.py in INI file
"""

import sys
import re
import math

def cartesian_to_polar(x, y):
    """Convert Cartesian (x, y) to Polar (angle_deg, radius)"""
    radius = math.sqrt(x**2 + y**2)
    angle_deg = math.degrees(math.atan2(y, x))
    
    # Normalize angle to 0-360 range
    if angle_deg < 0:
        angle_deg += 360
    
    return angle_deg, radius

def process_gcode(input_file):
    """Process G-code file and convert coordinates"""
    
    # Regular expression to match G0/G1 moves with X and/or Y
    move_pattern = re.compile(r'^(G[01])\s*(.*)', re.IGNORECASE)
    coord_pattern = re.compile(r'([XYZEFABS])(-?\d*\.?\d+)', re.IGNORECASE)
    
    # Track current position for incremental moves
    current_x = 0.0
    current_y = 0.0
    
    # Header
    print("; Converted from Cartesian to Polar coordinates")
    print("; X = angle (degrees), Y = radius (mm)")
    print("; Original file: {}".format(input_file if input_file != '-' else 'stdin'))
    print()
    
    # Read input
    if input_file == '-':
        lines = sys.stdin.readlines()
    else:
        with open(input_file, 'r') as f:
            lines = f.readlines()
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines and comments
        if not line or line.startswith(';'):
            print(line)
            continue
        
        # Check if this is a G0 or G1 move
        move_match = move_pattern.match(line)
        if move_match:
            g_code = move_match.group(1).upper()
            rest = move_match.group(2)
            
            # Parse coordinates
            coords = {}
            for match in coord_pattern.finditer(rest):
                axis = match.group(1).upper()
                value = float(match.group(2))
                coords[axis] = value
            
            # Update current position if X or Y specified
            if 'X' in coords:
                current_x = coords['X']
            if 'Y' in coords:
                current_y = coords['Y']
            
            # Convert to polar if we have position data
            if 'X' in coords or 'Y' in coords:
                angle, radius = cartesian_to_polar(current_x, current_y)
                
                # Build new G-code line
                new_line = "{} X{:.4f} Y{:.4f}".format(g_code, angle, radius)
                
                # Add Z if present
                if 'Z' in coords:
                    new_line += " Z{:.4f}".format(coords['Z'])
                
                # Add feedrate if present
                if 'F' in coords:
                    new_line += " F{:.1f}".format(coords['F'])
                
                # Add extrusion if present (for 3D printing)
                if 'E' in coords:
                    new_line += " E{:.5f}".format(coords['E'])
                
                print(new_line)
            else:
                # No X/Y, just pass through
                print(line)
        else:
            # Not a move command, pass through unchanged
            print(line)

def main():
    if len(sys.argv) < 2:
        # Read from stdin (for use as LinuxCNC filter)
        process_gcode('-')
    else:
        input_file = sys.argv[1]
        process_gcode(input_file)

if __name__ == '__main__':
    main()
