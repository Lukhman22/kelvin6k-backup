#!/usr/bin/env python3
"""
J0 Absolute-Encoder Calibration helper.

Mirrors j1_calibrate.py but for the J0 (rotary base) joint.

Calibration: physically position J0 at its 0deg reference, then click the panel
"Calibrate J0 @ 0deg" button. The current SV660 encoder count is saved.

On every LinuxCNC launch, start_linuxcnc.sh reads this file plus the live
encoder and patches [JOINT_0] HOME / HOME_OFFSET so a single click on
"Abs Home J0" snaps the joint to its true encoder-derived position.
"""
import hal
import time
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CAL_FILE   = os.path.join(SCRIPT_DIR, "j0_calibration.json")
ARM_FILE   = os.path.join(SCRIPT_DIR, "j0_cal_armed.flag")
J0_REF_POSITION_DEG    = 0.0
J0_SCALE_DEG_PER_COUNT = 0.000590277778  # 1 / 1694.4444

h = hal.component("j0-cal")
h.newpin("calibrate",      hal.HAL_BIT,   hal.HAL_IN)
h.newpin("j0-homed",       hal.HAL_BIT,   hal.HAL_IN)
h.newpin("encoder-raw",    hal.HAL_S32,   hal.HAL_IN)
h.newpin("cal-encoder",    hal.HAL_FLOAT, hal.HAL_OUT)
h.newpin("cal-position",   hal.HAL_FLOAT, hal.HAL_OUT)
h.newpin("cal-valid",      hal.HAL_BIT,   hal.HAL_OUT)
h.newpin("cal-armed",      hal.HAL_BIT,   hal.HAL_OUT)
h.newpin("predicted-pos",  hal.HAL_FLOAT, hal.HAL_OUT)
h.newpin("encoder-now",    hal.HAL_FLOAT, hal.HAL_OUT)
h.ready()


def load_cal():
    if not os.path.exists(CAL_FILE):
        return None
    try:
        with open(CAL_FILE) as f:
            return json.load(f)
    except Exception as e:
        print(f"j0-cal: load error: {e}")
        return None


def save_cal(enc_count, source):
    data = {
        "j0_cal_encoder":         int(enc_count),
        "j0_cal_position_deg":    J0_REF_POSITION_DEG,
        "j0_scale_deg_per_count": J0_SCALE_DEG_PER_COUNT,
        "calibrated_at":          time.strftime("%Y-%m-%d %H:%M:%S"),
        "source":                 source,
    }
    fd = os.open(CAL_FILE + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(CAL_FILE + ".tmp", CAL_FILE)
    print(f"j0-cal: SAVED encoder={enc_count} -> {J0_REF_POSITION_DEG}deg  ({source})")


cal = load_cal()
if cal:
    h["cal-encoder"]  = float(cal.get("j0_cal_encoder", 0))
    h["cal-position"] = cal.get("j0_cal_position_deg", J0_REF_POSITION_DEG)
    h["cal-valid"]    = 1
    print(f"j0-cal: loaded cal_encoder={cal.get('j0_cal_encoder')} "
          f"-> {cal.get('j0_cal_position_deg')}deg")
else:
    h["cal-position"] = J0_REF_POSITION_DEG
    h["cal-valid"]    = 0
    print("j0-cal: no calibration file yet")

armed = os.path.exists(ARM_FILE)
h["cal-armed"] = 1 if armed else 0
if armed:
    print("j0-cal: AUTO-ARMED — will capture encoder when joint.0.homed rises")

prev_btn   = False
prev_homed = False
try:
    while True:
        time.sleep(0.05)

        enc_now = int(h["encoder-raw"])
        h["encoder-now"] = float(enc_now)

        btn = bool(h["calibrate"])
        if btn and not prev_btn:
            try:
                save_cal(enc_now, "manual-button")
                h["cal-encoder"]  = float(enc_now)
                h["cal-position"] = J0_REF_POSITION_DEG
                h["cal-valid"]    = 1
            except Exception as e:
                print(f"j0-cal: save error: {e}")
        prev_btn = btn

        homed = bool(h["j0-homed"])
        if armed and homed and not prev_homed:
            try:
                save_cal(enc_now, "search-home-switch")
                h["cal-encoder"]  = float(enc_now)
                h["cal-position"] = J0_REF_POSITION_DEG
                h["cal-valid"]    = 1
                try:
                    os.remove(ARM_FILE)
                except OSError:
                    pass
                armed = False
                h["cal-armed"] = 0
                print("j0-cal: auto-arm consumed")
            except Exception as e:
                print(f"j0-cal: auto-save error: {e}")
        prev_homed = homed

        if h["cal-valid"]:
            delta_counts = enc_now - int(h["cal-encoder"])
            h["predicted-pos"] = (J0_REF_POSITION_DEG
                                  + delta_counts * J0_SCALE_DEG_PER_COUNT)
        else:
            h["predicted-pos"] = 0.0

except KeyboardInterrupt:
    raise SystemExit
