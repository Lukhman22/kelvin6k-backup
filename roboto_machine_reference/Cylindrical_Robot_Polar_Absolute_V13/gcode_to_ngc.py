#!/usr/bin/env python3
"""
Cura .gcode → LinuxCNC .ngc Converter

Converts Cura-sliced 3D print G-code into clean LinuxCNC-compatible .ngc files.
Strips all Marlin-specific codes (E axis, M204, M106, G92 E0, etc.)
and outputs only G0/G1 with X Y Z F values.

Usage:
  python3 gcode_to_ngc.py input.gcode [output.ngc]
  
If output is not specified, replaces .gcode extension with .ngc
and saves to /home/kelvin6k/linuxcnc/nc_files/
"""

import sys
import re
import os

# Marlin M-codes to strip entirely
STRIP_MCODES = {'M82', 'M83', 'M84', 'M104', 'M106', 'M107', 'M109',
                'M140', 'M190', 'M204', 'M205', 'M220', 'M221'}

def convert_gcode_to_ngc(input_path, output_path):
    """Convert Cura .gcode to clean .ngc with just XYZ+F"""
    
    coord_pattern = re.compile(r'([XYZF])(-?\d*\.?\d+)', re.IGNORECASE)
    
    with open(input_path, 'r') as f:
        lines = f.readlines()
    
    output_lines = []
    output_lines.append("G21")         # mm mode
    output_lines.append("G90")         # absolute positioning
    
    FIXED_FEEDRATE = 2400.0  # Constant feedrate for all moves
    
    for line in lines:
        line_text = line.strip()
        
        # Skip empty lines and comments
        if not line_text or line_text.startswith(';') or line_text.startswith('('):
            continue
        
        upper = line_text.upper()
        
        # Skip unsupported M-codes
        mcode_match = re.match(r'^(M\d+)', line_text, re.IGNORECASE)
        if mcode_match and mcode_match.group(1).upper() in STRIP_MCODES:
            continue
        
        # Skip G92 E0 (extrusion counter resets)
        if re.match(r'^G92\s+E', line_text, re.IGNORECASE):
            continue
        
        # Handle Cura's ;F syntax: "G1 ;F3000 X100" → "G1 F3000 X100"
        if ';F' in line_text or ';f' in line_text:
            line_text = re.sub(r';([Ff])', r'\1', line_text)
        
        # Process G0/G1 moves — extract only X, Y, Z, F
        if re.match(r'^G[01]\b', upper):
            x_val = y_val = z_val = f_val = None
            
            for match in coord_pattern.finditer(line_text):
                axis = match.group(1).upper()
                value = float(match.group(2))
                if axis == 'X':
                    x_val = value
                elif axis == 'Y':
                    y_val = value
                elif axis == 'Z':
                    z_val = value
                elif axis == 'F':
                    f_val = value
            
            # Skip lines with no XYZ movement
            if x_val is None and y_val is None and z_val is None:
                continue
            
            # Determine G command
            g_cmd = "G0" if upper.startswith("G0") else "G1"
            
            # Build clean output line
            parts = [g_cmd]
            if x_val is not None:
                parts.append(f"X{x_val:.3f}")  
            if y_val is not None:
                parts.append(f"Y{y_val:.3f}")
            if z_val is not None:
                parts.append(f"Z{z_val:.3f}")
            
            # Always use fixed feedrate
            parts.append(f"F{FIXED_FEEDRATE:.1f}")
            
            output_lines.append(" ".join(parts))
        
        # Pass through M2 (program end), M64/M65 (digital out), M67/M68 (analog out)
        elif re.match(r'^M2\b|^M6[4-8]\b', line_text, re.IGNORECASE):
            output_lines.append(line_text)
    
    # Motor off + program end
    output_lines.append("M68 E0 Q0")
    output_lines.append("M68 E1 Q0")
    output_lines.append("M68 E2 Q0")
    output_lines.append("M2")
    
    # Write output
    with open(output_path, 'w') as f:
        for line in output_lines:
            f.write(line + "\n")
    
    print(f"✅ Converted: {input_path}")
    print(f"   Output:    {output_path}")
    print(f"   Lines:     {len(lines)} input → {len(output_lines)} output")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 gcode_to_ngc.py input.gcode [output.ngc]")
        sys.exit(1)
    
    input_path = sys.argv[1]
    
    if len(sys.argv) >= 3:
        output_path = sys.argv[2]
    else:
        # Auto-generate output path in nc_files directory
        basename = os.path.splitext(os.path.basename(input_path))[0]
        # Clean up filename (remove spaces, parentheses)
        basename = basename.replace(' ', '_').replace('(', '').replace(')', '')
        output_path = f"/home/kelvin6k/linuxcnc/nc_files/{basename}.ngc"
    
    if not os.path.exists(input_path):
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)
    
    convert_gcode_to_ngc(input_path, output_path)


if __name__ == '__main__':
    main()
