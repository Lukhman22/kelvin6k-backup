#!/bin/bash
# start_linuxcnc_qtdragon.sh — Launch the QtDragon variant.
#
# Usage:
#   bash start_linuxcnc_qtdragon.sh
#
# Differences from start_linuxcnc.sh:
#   - Targets cylindrical_robot_qtdragon.ini (DISPLAY = qtvcp qtdragon).
#   - No PYVCP / postgui swap (the QtDragon ini has no PyVCP panel and
#     pins POSTGUI_HALFILE = postgui_qtdragon.hal).
#   - No "calibrate" mode here — for J0/J1 calibration use:
#         bash start_linuxcnc.sh calibrate
#     against the AXIS config (custompanel_calibrate.xml has the buttons).
#   - Auto-home is handled by abs_home.py inside the running LinuxCNC
#     (rising edge of halui.machine.is-on). This script no longer
#     pre-reads encoders via halrun — the userspace HAL comp does it.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INI_FILE="$SCRIPT_DIR/cylindrical_robot_qtdragon.ini"

echo "=== LinuxCNC Startup (QtDragon) ==="

# --- Reset INI homing values to defaults; abs_home.py will overwrite them
# on the F2 (machine-on) rising edge inside the running LinuxCNC instance.
sed -i "/^\[JOINT_0\]/,/^\[/{
    s/^HOME = .*/HOME = 0.0/
    s/^HOME_OFFSET = .*/HOME_OFFSET = 0.0/
}" "$INI_FILE"
sed -i "/^\[JOINT_1\]/,/^\[/{
    s/^HOME = .*/HOME = 650.0/
    s/^HOME_OFFSET = .*/HOME_OFFSET = 650.0/
    s/^HOME_SEARCH_VEL = .*/HOME_SEARCH_VEL = 0/
    s/^HOME_LATCH_VEL = .*/HOME_LATCH_VEL = 0/
}" "$INI_FILE"
sed -i "/^\[JOINT_2\]/,/^\[/{
    s/^HOME = .*/HOME = 0.0/
    s/^HOME_OFFSET = .*/HOME_OFFSET = 0.0/
}" "$INI_FILE"

echo "Launching LinuxCNC (QtDragon)..."
exec linuxcnc "$INI_FILE"
