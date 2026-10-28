#!/usr/bin/env python3
"""
Position Saver — reads displayed joint positions directly from LinuxCNC.
Saves J0/J1/J2 + G-code file/line to saved_positions.json every 0.1 seconds.
Uses linuxcnc.stat() to read the EXACT displayed position (no manual offset math).
All 3 joints are now absolute encoders — all saved and restored on resume.
"""
import hal
import time
import json
import os
import linuxcnc

SAVE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_positions.json")

lcnc_stat = linuxcnc.stat()

h = hal.component("pos-saver")
# Output pins for PyVCP display
h.newpin("j0-last-home", hal.HAL_FLOAT, hal.HAL_OUT)
h.newpin("j1-last-home", hal.HAL_FLOAT, hal.HAL_OUT)
h.newpin("j2-last-home", hal.HAL_FLOAT, hal.HAL_OUT)
h.newpin("gcode-line",   hal.HAL_FLOAT, hal.HAL_OUT)
# Input pins (raw motor-pos-fb for encoder-based correction)
h.newpin("j0-pos", hal.HAL_FLOAT, hal.HAL_IN)
h.newpin("j1-pos", hal.HAL_FLOAT, hal.HAL_IN)
h.newpin("j2-pos", hal.HAL_FLOAT, hal.HAL_IN)
h.newpin("j0-homed", hal.HAL_BIT, hal.HAL_IN)
h.newpin("j1-homed", hal.HAL_BIT, hal.HAL_IN)
h.newpin("j2-homed", hal.HAL_BIT, hal.HAL_IN)
h.ready()

# Last-known-good resume point. Seeded from the on-disk state so that an
# idle machine (motion_line == 0) does not clobber a valid resume line.
last_gcode_file = ""
last_gcode_line = 0

# Load last saved state for initial PyVCP display
if os.path.exists(SAVE_FILE):
    try:
        with open(SAVE_FILE) as f:
            data = json.load(f)
        h["j0-last-home"] = data.get("j0", 0.0)
        h["j1-last-home"] = data.get("j1", 650.0)
        h["j2-last-home"] = data.get("j2", 0.0)
        h["gcode-line"]   = float(data.get("gcode_line", 0))
        last_gcode_file = data.get("gcode_file", "") or ""
        last_gcode_line = int(data.get("gcode_line", 0) or 0)
        print(f"pos-saver: Loaded J0={data.get('j0',0):.2f} J1={data.get('j1',650):.2f} J2={data.get('j2',0):.2f}")
    except Exception as e:
        print(f"pos-saver: Load error: {e}")

print("pos-saver: Ready — saving all 3 joints every 0.1s")

try:
    while True:
        time.sleep(0.1)

        try:
            lcnc_stat.poll()
        except Exception:
            continue

        # All 3 joints must be homed before saving
        j0_homed = lcnc_stat.joint[0]['homed']
        j1_homed = lcnc_stat.joint[1]['homed']
        j2_homed = lcnc_stat.joint[2]['homed']

        if not (j0_homed and j1_homed and j2_homed):
            continue

        # Read EXACT displayed joint positions from LinuxCNC
        j0_pos = lcnc_stat.joint[0]['output']
        j1_pos = lcnc_stat.joint[1]['output']
        j2_pos = lcnc_stat.joint[2]['output']

        # Raw motor-pos-fb for encoder-based delta correction
        j0_raw = h["j0-pos"]
        j1_raw = h["j1-pos"]
        j2_raw = h["j2-pos"]

        # Update PyVCP display
        h["j0-last-home"] = j0_pos
        h["j1-last-home"] = j1_pos
        h["j2-last-home"] = j2_pos

        # Track G-code progress against the CURRENTLY loaded program only.
        # When the operator loads a different file, the old resume point is
        # no longer valid — switch to the new file and reset its line to 0
        # so auto-resume never applies an old file's line to a new program.
        #
        # Compare by basename, not full path: lcnc_stat.file is LinuxCNC's
        # [FILTER] temp path (/tmp/emcflt-XXXX.d/<name>). The temp DIR is
        # regenerated every launch, but the basename is the original
        # filename and is stable across launches — so the same program
        # auto-resumed on the next boot is NOT mistaken for a new file.
        current_file = lcnc_stat.file or ""
        if current_file and (os.path.basename(current_file) !=
                             os.path.basename(last_gcode_file)):
            last_gcode_file = current_file
            last_gcode_line = 0

        # motion_line is the line motion is actually executing; it drops
        # back to 0 when the interpreter goes idle (program stopped/
        # aborted/finished, or just homed and sitting). Only advance the
        # resume point while motion is actively running — otherwise an idle
        # machine overwrites a valid resume line with 0 and auto-resume
        # always restarts the print from the beginning.
        motion_line = lcnc_stat.motion_line
        if motion_line > 0:
            last_gcode_file = current_file
            last_gcode_line = motion_line
        gcode_file = last_gcode_file
        gcode_line = last_gcode_line
        h["gcode-line"] = float(gcode_line)

        # Atomic write — force to disk immediately (survives power cuts)
        current = {
            "j0": round(j0_pos, 6),
            "j1": round(j1_pos, 6),
            "j2": round(j2_pos, 6),
            "j0_raw": round(j0_raw, 6),
            "j1_raw": round(j1_raw, 6),
            "j2_raw": round(j2_raw, 6),
            "gcode_file": gcode_file,
            "gcode_line": gcode_line,
        }
        try:
            fd = os.open(SAVE_FILE + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
            with os.fdopen(fd, 'w') as f:
                json.dump(current, f)
                f.flush()
                os.fsync(f.fileno())
            os.replace(SAVE_FILE + ".tmp", SAVE_FILE)
        except Exception as e:
            print(f"pos-saver: Save error: {e}")

except KeyboardInterrupt:
    raise SystemExit
