#!/usr/bin/env python3
"""Quick analysis: what radius does the validator produce?"""
import math, re

TOOL_OFFSET = -235.0

def compensate(x, y):
    d_sq = x**2 + y**2
    r_sq = d_sq - TOOL_OFFSET**2
    if r_sq < 0: r_sq = 0.01
    r = math.sqrt(r_sq)
    ba = math.atan2(y, x)
    oa = math.atan2(TOOL_OFFSET, r) if r > 0 else math.pi/2
    a = ba - oa
    return r * math.cos(a), r * math.sin(a)

coord_pat = re.compile(r'([XYZF])(-?\d*\.?\d+)', re.IGNORECASE)
cx, cy = 650.0, 0.0
min_arm_r, max_arm_r = 99999, 0

with open('/home/kelvin6k/linuxcnc/nc_files/NON PLANAR.ngc') as f:
    for i, line in enumerate(f, 1):
        line = line.strip()
        upper = line.upper()
        if 'G0' in upper or 'G1' in upper:
            nx, ny = cx, cy
            for m in coord_pat.finditer(line):
                axis = m.group(1).upper()
                val = float(m.group(2))
                if axis == 'X': nx = val
                elif axis == 'Y': ny = val
            
            orig_r = math.sqrt(nx**2 + ny**2)
            comp_x, comp_y = compensate(nx, ny)
            arm_r = math.sqrt(comp_x**2 + comp_y**2)
            
            if arm_r < min_arm_r: min_arm_r = arm_r
            if arm_r > max_arm_r: max_arm_r = arm_r
            
            if i <= 10 or abs(arm_r - 1000) < 20:
                print(f"Line {i}: orig({nx:.0f},{ny:.0f}) r={orig_r:.0f} -> comp({comp_x:.0f},{comp_y:.0f}) arm_r={arm_r:.0f}")
            
            cx, cy = nx, ny

print(f"\nARM radius range: {min_arm_r:.1f} - {max_arm_r:.1f} mm")
print(f"Does any point have arm_r near 1000? Min={min_arm_r:.1f}")
