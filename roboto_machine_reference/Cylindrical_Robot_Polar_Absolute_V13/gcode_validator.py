#!/usr/bin/env python3
"""
G-Code Filter for Polar Robot
- Validates tool-tip stays within work envelope (reachable annulus)
- Strips unsupported Marlin/Cura M-codes

Tool offset is now applied inside polarkins3d kinematics, so this filter
no longer pre-compensates X/Y — G-code goes through targeting tool-tip
cartesian coordinates directly.

Usage: Set as filter in LinuxCNC INI file
"""

import sys
import re
import math

# Perpendicular tool offset (mm) — for envelope math only.
# Must match TOOL_OFFSET in polarkins3d.comp.
TOOL_OFFSET = -235.0

# Reachable tool-tip distance from rotary center, given JOINT_1 radius limits
# 650..2500mm (see cylindrical_robot_qtdragon.ini) and a perpendicular tool
# offset:
#   d = sqrt(r² + offset²)
# MAX uses 2500 (the JOINT_1 MAX_LIMIT) — not 2600 — so a file that PASSES
# validation always runs without tripping the joint's soft limit.
MIN_RADIUS = math.sqrt(650.0**2 + TOOL_OFFSET**2)   # ~691.3 mm
MAX_RADIUS = math.sqrt(2500.0**2 + TOOL_OFFSET**2)  # ~2511.0 mm


def process_gcode(input_file):
    """Process G-code: compensate offset, validate, handle Cura 3D print format"""
    
    # Match all relevant axes including E (extrusion)
    coord_pattern = re.compile(r'([XYZFE])(-?\d*\.?\d+)', re.IGNORECASE)
    
    # Unsupported Marlin/Cura M-codes — convert to comments
    UNSUPPORTED_MCODES = {'M104', 'M106', 'M107', 'M109', 'M140', 'M190',
                          'M82', 'M83', 'M84', 'M204', 'M205', 'M220', 'M221'}
    
    if input_file == '-':
        lines = sys.stdin.readlines()
    else:
        with open(input_file, 'r') as f:
            lines = f.readlines()
    
    output_lines = []
    violations = []
    
    output_lines.append(f"(Tool offset {TOOL_OFFSET}mm applied in polarkins3d)")
    output_lines.append(f"(Reachable tool-tip annulus: {MIN_RADIUS:.1f}mm - {MAX_RADIUS:.1f}mm)")
    output_lines.append("")
    
    current_x = MIN_RADIUS
    current_y = 0.0
    line_num = 0
    
    for line in lines:
        line_num += 1
        line_text = line.strip()
        
        # Pass through comments and empty lines
        if not line_text or line_text.startswith(';') or line_text.startswith('('):
            output_lines.append(line.rstrip())
            continue
        
        upper = line_text.upper()
        
        # Strip unsupported Marlin M-codes — convert to comments
        mcode_match = re.match(r'^(M\d+)', line_text, re.IGNORECASE)
        if mcode_match and mcode_match.group(1).upper() in UNSUPPORTED_MCODES:
            output_lines.append(f"({line_text})")
            continue
        
        # Handle Cura's `;F` syntax: "G1 ;F3000 X100 Y200" 
        # The semicolon is NOT a comment here — F value follows it
        # Fix by removing the semicolon before F
        if ';F' in line_text or ';f' in line_text:
            line_text = re.sub(r';([Ff])', r'\1', line_text)
        
        # Process moves (G0/G1)
        if 'G0' in upper or 'G1' in upper:
            new_x, new_y = current_x, current_y
            z_value = None
            f_value = None
            e_value = None
            
            for match in coord_pattern.finditer(line_text):
                axis = match.group(1).upper()
                value = float(match.group(2))
                if axis == 'X':
                    new_x = value
                elif axis == 'Y':
                    new_y = value
                elif axis == 'Z':
                    z_value = value
                elif axis == 'F':
                    f_value = value
                elif axis == 'E':
                    e_value = value
            
            # Check tool-tip position against reachable envelope
            tip_radius = math.sqrt(new_x**2 + new_y**2)
            if tip_radius < MIN_RADIUS:
                violations.append((line_num, 'CENTER', tip_radius, new_x, new_y))
            elif tip_radius > MAX_RADIUS:
                violations.append((line_num, 'OUTSIDE', tip_radius, new_x, new_y))

            # Pass X/Y through unchanged — polarkins3d applies the tool offset.
            g_match = re.match(r'(G\d+\.?\d*)', line_text, re.IGNORECASE)
            g_cmd = g_match.group(1) if g_match else ''

            parts = [g_cmd]
            parts.append(f'X{new_x:.3f}')
            parts.append(f'Y{new_y:.3f}')
            if z_value is not None:
                parts.append(f'Z{z_value:.3f}')
            if f_value is not None:
                parts.append(f'F{f_value:.1f}')
            # NOTE: E values from Cura (extrusion amounts) are stripped.
            # LinuxCNC doesn't support E on G0/G1 lines — extruder is
            # PWM-controlled via panel sliders or M67/M68 commands.            
            output_lines.append(' '.join(parts))
            current_x, current_y = new_x, new_y
            
        elif 'G2' in upper or 'G3' in upper:
            # Arc moves - pass through (TODO: full arc compensation)
            output_lines.append(line_text)
        else:
            # Strip G92 E0 (Marlin extrusion counter reset — E isn't a LinuxCNC axis)
            if re.match(r'^G92\s+E', line_text, re.IGNORECASE):
                output_lines.append(f"({line_text})")
            else:
                # Pass through everything else (G92 XYZ, M67/M68, M2, etc.)
                output_lines.append(line.rstrip())
    
    # Output based on validation
    if violations:
        print("(===============================================)")
        print("(  ERROR: G-CODE CONTAINS NO-GO ZONE VIOLATIONS )")
        print("(===============================================)")
        print(f"(  Found {len(violations)} point(s) outside work area)")
        print(f"(  Valid radius range: {MIN_RADIUS:.1f}mm - {MAX_RADIUS:.1f}mm)")
        print("()")
        
        for ln, vtype, r, x, y in violations[:10]:
            if vtype == 'CENTER':
                print(f"(  Line {ln}: X={x:.1f} Y={y:.1f} -> r={r:.1f}mm < {MIN_RADIUS:.1f}mm)")
            else:
                print(f"(  Line {ln}: X={x:.1f} Y={y:.1f} -> r={r:.1f}mm > {MAX_RADIUS:.1f}mm)")
        
        if len(violations) > 10:
            print(f"(  ... and {len(violations) - 10} more)")
        
        print("(===============================================)")
        print("")
        print("M2 (Program stopped due to validation errors)")
    else:
        for line in output_lines:
            print(line)


def main():
    if len(sys.argv) < 2:
        process_gcode('-')
    else:
        process_gcode(sys.argv[1])


if __name__ == '__main__':
    main()
