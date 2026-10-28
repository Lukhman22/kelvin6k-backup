#!/usr/bin/env python3
"""
Polar Kinematics Component for LinuxCNC
Converts Cartesian (X,Y) commands to Polar (angle, radius) for real-time jogging and motion.

World Coordinates: X, Y (Cartesian in mm)
Joint Coordinates: joint.0 = angle (degrees), joint.1 = radius (mm)

Forward Kinematics: Joint -> World
  X = radius * cos(angle)
  Y = radius * sin(angle)

Inverse Kinematics: World -> Joint
  angle = atan2(Y, X)
  radius = sqrt(X^2 + Y^2)
"""

import hal
import math
import time

# Create HAL component
h = hal.component("polar_kins")

# World coordinates (Cartesian) - what LinuxCNC commands
h.newpin("world-x", hal.HAL_FLOAT, hal.HAL_IN)  # Commanded X position
h.newpin("world-y", hal.HAL_FLOAT, hal.HAL_IN)  # Commanded Y position

# Joint coordinates (Polar) - what motors need
h.newpin("joint-0-cmd", hal.HAL_FLOAT, hal.HAL_OUT)  # Angle output (degrees)
h.newpin("joint-1-cmd", hal.HAL_FLOAT, hal.HAL_OUT)  # Radius output (mm)

# Joint feedback (Polar) - from motors
h.newpin("joint-0-fb", hal.HAL_FLOAT, hal.HAL_IN)  # Angle feedback (degrees)
h.newpin("joint-1-fb", hal.HAL_FLOAT, hal.HAL_IN)  # Radius feedback (mm)

# World feedback (Cartesian) - calculated from joint feedback
h.newpin("world-x-fb", hal.HAL_FLOAT, hal.HAL_OUT)  # X feedback
h.newpin("world-y-fb", hal.HAL_FLOAT, hal.HAL_OUT)  # Y feedback

# Parameters
h.newpin("min-radius", hal.HAL_FLOAT, hal.HAL_IN)  # Minimum radius (avoid singularity)

h.ready()

# Set default min radius
min_radius = 10.0  # mm - avoid singularity at center

try:
    while True:
        # Get minimum radius parameter
        min_r = h['min-radius']
        if min_r < 1.0:
            min_r = 10.0  # Default minimum
        
        # === INVERSE KINEMATICS: World (X,Y) -> Joint (angle, radius) ===
        x = h['world-x']
        y = h['world-y']
        
        # Calculate radius
        radius = math.sqrt(x*x + y*y)
        
        # Clamp radius to minimum
        if radius < min_r:
            radius = min_r
        
        # Calculate angle (in degrees)
        if radius > min_r:
            angle = math.degrees(math.atan2(y, x))
        else:
            # At center, maintain current angle
            angle = h['joint-0-fb']
        
        # Normalize angle to 0-360
        while angle < 0:
            angle += 360
        while angle >= 360:
            angle -= 360
        
        # Output to joints
        h['joint-0-cmd'] = angle
        h['joint-1-cmd'] = radius
        
        # === FORWARD KINEMATICS: Joint (angle, radius) -> World (X,Y) ===
        fb_angle = h['joint-0-fb']
        fb_radius = h['joint-1-fb']
        
        fb_angle_rad = math.radians(fb_angle)
        h['world-x-fb'] = fb_radius * math.cos(fb_angle_rad)
        h['world-y-fb'] = fb_radius * math.sin(fb_angle_rad)
        
        time.sleep(0.001)  # 1ms update rate

except KeyboardInterrupt:
    raise SystemExit
