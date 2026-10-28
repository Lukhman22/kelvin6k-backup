#!/usr/bin/env python3
"""
J1 Absolute-Encoder Calibration helper.

Two ways to calibrate:

  1) AUTO (preferred) — `bash start_linuxcnc.sh calibrate` arms a marker file
     and patches the INI to use search-homing on the 650mm limit switch.
     The user clicks "Home J1"; when joint.1.homed rises, this component
     captures the encoder count at that moment and writes the calibration.

  2) MANUAL — physically jog J1 to its 650mm reference, then click the panel
     "Calibrate J1 @ 650mm" button.

On every subsequent LinuxCNC launch, start_linuxcnc.sh reads this file plus the
current encoder value and patches [JOINT_1] HOME/HOME_OFFSET so a single click on
"Home J1" snaps the joint to its true position.
"""
import hal
import time
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CAL_FILE   = os.path.join(SCRIPT_DIR, "j1_calibration.json")
ARM_FILE   = os.path.join(SCRIPT_DIR, "j1_cal_armed.flag")
J1_REF_POSITION_MM = 650.0
J1_SCALE_MM_PER_COUNT = 0.016638935  # 1 / 60.1

h = hal.component("j1-cal")
h.newpin("calibrate",      hal.HAL_BIT,   hal.HAL_IN)   # manual capture trigger
h.newpin("j1-homed",       hal.HAL_BIT,   hal.HAL_IN)   # joint.1.homed
h.newpin("encoder-raw",    hal.HAL_S32,   hal.HAL_IN)   # lcec.0.2.actual-position
h.newpin("cal-encoder",    hal.HAL_FLOAT, hal.HAL_OUT)  # last saved enc count
h.newpin("cal-position",   hal.HAL_FLOAT, hal.HAL_OUT)  # 650.0 (display)
h.newpin("cal-valid",      hal.HAL_BIT,   hal.HAL_OUT)  # 1 if cal file exists
h.newpin("cal-armed",      hal.HAL_BIT,   hal.HAL_OUT)  # 1 if auto-capture armed
h.newpin("predicted-pos",  hal.HAL_FLOAT, hal.HAL_OUT)  # live predicted J1 mm
h.newpin("encoder-now",    hal.HAL_FLOAT, hal.HAL_OUT)  # current encoder (display)
h.ready()


def load_cal():
    if not os.path.exists(CAL_FILE):
        return None
    try:
        with open(CAL_FILE) as f:
            return json.load(f)
    except Exception as e:
        print(f"j1-cal: load error: {e}")
        return None


def save_cal(enc_count, source):
    data = {
        "j1_cal_encoder":        int(enc_count),
        "j1_cal_position_mm":    J1_REF_POSITION_MM,
        "j1_scale_mm_per_count": J1_SCALE_MM_PER_COUNT,
        "calibrated_at":         time.strftime("%Y-%m-%d %H:%M:%S"),
        "source":                source,
    }
    fd = os.open(CAL_FILE + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(CAL_FILE + ".tmp", CAL_FILE)
    print(f"j1-cal: SAVED encoder={enc_count} -> {J1_REF_POSITION_MM}mm  ({source})")


cal = load_cal()
if cal:
    h["cal-encoder"]  = float(cal.get("j1_cal_encoder", 0))
    h["cal-position"] = cal.get("j1_cal_position_mm", J1_REF_POSITION_MM)
    h["cal-valid"]    = 1
    print(f"j1-cal: loaded cal_encoder={cal.get('j1_cal_encoder')} "
          f"-> {cal.get('j1_cal_position_mm')}mm")
else:
    h["cal-position"] = J1_REF_POSITION_MM
    h["cal-valid"]    = 0
    print("j1-cal: no calibration file yet")

armed = os.path.exists(ARM_FILE)
h["cal-armed"] = 1 if armed else 0
if armed:
    print("j1-cal: AUTO-ARMED — will capture encoder when joint.1.homed rises")

prev_btn   = False
prev_homed = False
try:
    while True:
        time.sleep(0.05)

        enc_now = int(h["encoder-raw"])
        h["encoder-now"] = float(enc_now)

        # MANUAL trigger (panel button)
        btn = bool(h["calibrate"])
        if btn and not prev_btn:
            try:
                save_cal(enc_now, "manual-button")
                h["cal-encoder"]  = float(enc_now)
                h["cal-position"] = J1_REF_POSITION_MM
                h["cal-valid"]    = 1
            except Exception as e:
                print(f"j1-cal: save error: {e}")
        prev_btn = btn

        # AUTO capture on home-switch search completion
        homed = bool(h["j1-homed"])
        if armed and homed and not prev_homed:
            try:
                save_cal(enc_now, "search-home-switch")
                h["cal-encoder"]  = float(enc_now)
                h["cal-position"] = J1_REF_POSITION_MM
                h["cal-valid"]    = 1
                # consume the arm so we don't recapture on next home click
                try:
                    os.remove(ARM_FILE)
                except OSError:
                    pass
                armed = False
                h["cal-armed"] = 0
                print("j1-cal: auto-arm consumed; future homes won't overwrite")
            except Exception as e:
                print(f"j1-cal: auto-save error: {e}")
        prev_homed = homed

        if h["cal-valid"]:
            delta_counts = enc_now - int(h["cal-encoder"])
            h["predicted-pos"] = (J1_REF_POSITION_MM
                                  + delta_counts * J1_SCALE_MM_PER_COUNT)
        else:
            h["predicted-pos"] = 0.0

except KeyboardInterrupt:
    raise SystemExit
