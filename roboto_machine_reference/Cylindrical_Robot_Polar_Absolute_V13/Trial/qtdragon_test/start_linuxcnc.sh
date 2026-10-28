#!/bin/bash
# start_linuxcnc.sh — Launch LinuxCNC
#
# Usage:
#   bash start_linuxcnc.sh            → Normal start (zero-click homing)
#                                       1. Launches LinuxCNC immediately
#                                       2. Operator clears E-stop (F1), then F2
#                                       3. abs_home.py reads live encoders, patches
#                                          ini.N.home_offset, fires halui.home-all
#                                          via postgui.hal — joints snap to
#                                          encoder-derived positions.
#                                       Load g-code and run. No homing buttons.
#   bash start_linuxcnc.sh calibrate  → Calibration mode (one-time, re-seed encoder ref)
#                                       Click 'Calibrate J0 @ 0deg' (after physically
#                                       aligning J0). For J1, click 'Search Home J1'
#                                       (encoder auto-captures via 650mm limit switch).
#                                       Then close + relaunch in normal mode.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
INI_FILE="$SCRIPT_DIR/cylindrical_robot.ini"
J1_ARM_FILE="$SCRIPT_DIR/j1_cal_armed.flag"

echo "=== LinuxCNC Startup ==="

# --- Pick the right panel + postgui per mode (patch INI references) ---
if [ "$1" = "calibrate" ]; then
    PANEL_FILE="custompanel_calibrate.xml"
    POSTGUI_FILE="postgui_calibrate.hal"
else
    PANEL_FILE="custompanel.xml"
    POSTGUI_FILE="postgui.hal"
fi
sed -i "s|^PYVCP = .*|PYVCP = ${PANEL_FILE}|"               "$INI_FILE"
sed -i "s|^POSTGUI_HALFILE = .*|POSTGUI_HALFILE = ${POSTGUI_FILE}|" "$INI_FILE"
echo "Mode: ${1:-normal}  panel=${PANEL_FILE}  postgui=${POSTGUI_FILE}"

# --- Reset INI homing values to defaults (then patched per mode below) ---
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

if [ "$1" = "calibrate" ]; then
    echo "CALIBRATE MODE"
    echo "  J1: patching for search-home (HOME_SEARCH_VEL=-40, LATCH=10)..."
    sed -i "/^\[JOINT_1\]/,/^\[/{
        s/^HOME = .*/HOME = 650.0/
        s/^HOME_OFFSET = .*/HOME_OFFSET = 650.0/
        s/^HOME_SEARCH_VEL = .*/HOME_SEARCH_VEL = -40.0/
        s/^HOME_LATCH_VEL = .*/HOME_LATCH_VEL = 10.0/
        s/^HOME_FINAL_VEL = .*/HOME_FINAL_VEL = 5.0/
    }" "$INI_FILE"
    : > "$J1_ARM_FILE"
    echo "  J1 auto-arm flag created: $J1_ARM_FILE"
    echo "  J0: manual calibrate via panel button (no auto-arm)"
    echo ""
    echo ">>> J1: jog OFF the switch if on it, then click 'Search Home J1'."
    echo ">>> J0: physically align J0 to 0deg, then click 'Calibrate J0 @ 0deg'."
    echo "    Close LinuxCNC and relaunch with 'bash start_linuxcnc.sh' for daily use."
else
    [ -f "$J1_ARM_FILE" ] && rm -f "$J1_ARM_FILE"
    echo ""
    echo ">>> Normal mode: clear E-stop (F1), wait for DRO values, then press F2."
    echo "    abs_home.py will read live encoders + apply HOME_OFFSET on F2."
fi

echo "Launching LinuxCNC..."
linuxcnc "$INI_FILE"
