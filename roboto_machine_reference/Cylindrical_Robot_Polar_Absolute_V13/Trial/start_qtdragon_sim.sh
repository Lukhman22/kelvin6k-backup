#!/bin/bash
# start_qtdragon_sim.sh — Boot QtDragon_hd in pure simulation.
#
# No EtherCAT, no servo drives, no cia402, no abs-home. Uses trivkins
# XYZ (see cylindrical_robot_qtdragon_sim.ini [KINS]). All 10 ported
# features are exercised against simulated joint loopbacks — see
# cylindrical_robot_sim.hal + postgui_sim.hal for the wiring.
#
# Use this on a dev box to customise the UI without hardware.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1
exec linuxcnc "$SCRIPT_DIR/cylindrical_robot_qtdragon_sim.ini"
