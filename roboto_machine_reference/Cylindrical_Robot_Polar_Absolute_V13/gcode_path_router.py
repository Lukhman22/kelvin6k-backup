#!/usr/bin/env python3
"""
G-Code Path Router for Polar Robot
Detects moves that would cross the center no-go zone and re-routes them
to arc around the boundary instead of going straight through.

Usage:
    ./gcode_path_router.py input.ngc > output.ngc
    
Or as a LinuxCNC filter:
    Set this as the filter for .ngc files in INI
"""

import sys
import re
import math

# Work envelope limits
MIN_RADIUS = 650.0
MAX_RADIUS = 2600.0
SAFE_RADIUS = 700.0  # Route arcs slightly outside min_radius for safety margin

def distance_to_center(x, y):
    """Calculate distance from point to origin"""
    return math.sqrt(x*x + y*y)

def line_crosses_center(x1, y1, x2, y2, min_r):
    """
    Check if line segment from (x1,y1) to (x2,y2) crosses the center exclusion zone.
    Returns True if the minimum distance from origin to line is less than min_r.
    """
    # Vector math: find closest point on line segment to origin
    dx = x2 - x1
    dy = y2 - y1
    
    # Line segment length squared
    len_sq = dx*dx + dy*dy
    if len_sq == 0:
        return distance_to_center(x1, y1) < min_r
    
    # Parameter t for closest point on line
    t = max(0, min(1, (-x1*dx - y1*dy) / len_sq))
    
    # Closest point on segment
    closest_x = x1 + t * dx
    closest_y = y1 + t * dy
    
    # Distance from origin to closest point
    min_dist = distance_to_center(closest_x, closest_y)
    
    return min_dist < min_r

def generate_arc_around(x1, y1, x2, y2, g_code, feedrate):
    """
    Generate arc move(s) that go around the center zone.
    Returns list of G-code lines.
    """
    # Calculate angles
    angle1 = math.atan2(y1, x1)
    angle2 = math.atan2(y2, x2)
    
    # Determine shortest arc direction
    delta_angle = angle2 - angle1
    if delta_angle > math.pi:
        delta_angle -= 2 * math.pi
    elif delta_angle < -math.pi:
        delta_angle += 2 * math.pi
    
    # Generate intermediate points along arc at SAFE_RADIUS
    lines = []
    num_points = max(2, int(abs(delta_angle) / (math.pi / 6)))  # At least every 30 degrees
    
    for i in range(1, num_points + 1):
        t = i / num_points
        angle = angle1 + delta_angle * t
        
        if i < num_points:
            # Intermediate point on arc
            arc_x = SAFE_RADIUS * math.cos(angle)
            arc_y = SAFE_RADIUS * math.sin(angle)
            lines.append(f"{g_code} X{arc_x:.3f} Y{arc_y:.3f}{feedrate}")
        else:
            # Final point is actual target
            lines.append(f"{g_code} X{x2:.3f} Y{y2:.3f}{feedrate}")
    
    return lines

def process_gcode(input_file):
    """Process G-code file and re-route center-crossing moves"""
    
    move_pattern = re.compile(r'^(G[01])\s*(.*)', re.IGNORECASE)
    coord_pattern = re.compile(r'([XYZEF])(-?\d*\.?\d+)', re.IGNORECASE)
    
    current_x = 650.0  # Start at home
    current_y = 0.0
    
    # Header
    print("; Processed by gcode_path_router.py - Center zone avoidance enabled")
    print(f"; No-go zone: radius < {MIN_RADIUS}mm")
    print()
    
    # Read input
    if input_file == '-':
        lines = sys.stdin.readlines()
    else:
        with open(input_file, 'r') as f:
            lines = f.readlines()
    
    rerouted_count = 0
    
    for line in lines:
        original_line = line.strip()
        
        # Skip empty lines and comments
        if not original_line or original_line.startswith(';') or original_line.startswith('('):
            print(original_line)
            continue
        
        # Check if this is a G0 or G1 move
        move_match = move_pattern.match(original_line)
        if move_match:
            g_code = move_match.group(1).upper()
            rest = move_match.group(2)
            
            # Parse coordinates
            coords = {}
            for match in coord_pattern.finditer(rest):
                axis = match.group(1).upper()
                value = float(match.group(2))
                coords[axis] = value
            
            # Get target position
            target_x = coords.get('X', current_x)
            target_y = coords.get('Y', current_y)
            
            # Build feedrate string
            feedrate = f" F{coords['F']:.0f}" if 'F' in coords else ""
            
            # Check if this move crosses center zone
            if line_crosses_center(current_x, current_y, target_x, target_y, MIN_RADIUS):
                # Generate arc around center
                print(f"; REROUTED: Original was {original_line}")
                arc_lines = generate_arc_around(current_x, current_y, target_x, target_y, g_code, feedrate)
                for arc_line in arc_lines:
                    print(arc_line)
                rerouted_count += 1
            else:
                # Safe to go straight
                print(original_line)
            
            # Update current position
            current_x = target_x
            current_y = target_y
        else:
            # Not a move command, pass through unchanged
            print(original_line)
    
    print()
    print(f"; Path routing complete: {rerouted_count} moves rerouted around center zone")

def main():
    if len(sys.argv) < 2:
        process_gcode('-')
    else:
        input_file = sys.argv[1]
        process_gcode(input_file)

if __name__ == '__main__':
    main()
