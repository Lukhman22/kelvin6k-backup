#!/usr/bin/env python3
"""
J2 Absolute-Encoder Calibration helper.

Mirrors j0_calibrate.py — J2 has no limit switch, so calibration is manual:
physically jog J2 to its 0 mm reference (typically the carriage bottom / build
plate contact), then click "Calibrate J2 @ 0mm" on the panel. The current
SV670I encoder count is saved to j2_calibration.json.

On every normal-mode launch, start_linuxcnc.sh reads this file plus the live
encoder (via SDO 0x6064 on slave 1) and patches [JOINT_2] HOME / HOME_OFFSET
so the auto-home-on-machine-on pulse snaps J2 to its true height.
"""
import hal
import time
import json
import os

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CAL_FILE   = os.path.join(SCRIPT_DIR, "j2_calibration.json")
J2_REF_POSITION_MM    = 0.0
J2_SCALE_MM_PER_COUNT = 0.0006  # 1 / 1666.666

h = hal.component("j2-cal")
h.newpin("calibrate",      hal.HAL_BIT,   hal.HAL_IN)
h.newpin("encoder-raw",    hal.HAL_S32,   hal.HAL_IN)
h.newpin("cal-encoder",    hal.HAL_FLOAT, hal.HAL_OUT)
h.newpin("cal-position",   hal.HAL_FLOAT, hal.HAL_OUT)
h.newpin("cal-valid",      hal.HAL_BIT,   hal.HAL_OUT)
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
        print(f"j2-cal: load error: {e}")
        return None


def save_cal(enc_count, source):
    data = {
        "j2_cal_encoder":        int(enc_count),
        "j2_cal_position_mm":    J2_REF_POSITION_MM,
        "j2_scale_mm_per_count": J2_SCALE_MM_PER_COUNT,
        "calibrated_at":         time.strftime("%Y-%m-%d %H:%M:%S"),
        "source":                source,
    }
    fd = os.open(CAL_FILE + ".tmp", os.O_WRONLY | os.O_CREAT | os.O_TRUNC)
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(CAL_FILE + ".tmp", CAL_FILE)
    print(f"j2-cal: SAVED encoder={enc_count} -> {J2_REF_POSITION_MM}mm  ({source})")


cal = load_cal()
if cal:
    h["cal-encoder"]  = float(cal.get("j2_cal_encoder", 0))
    h["cal-position"] = cal.get("j2_cal_position_mm", J2_REF_POSITION_MM)
    h["cal-valid"]    = 1
    print(f"j2-cal: loaded cal_encoder={cal.get('j2_cal_encoder')} "
          f"-> {cal.get('j2_cal_position_mm')}mm")
else:
    h["cal-position"] = J2_REF_POSITION_MM
    h["cal-valid"]    = 0
    print("j2-cal: no calibration file yet")

prev_btn = False
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
                h["cal-position"] = J2_REF_POSITION_MM
                h["cal-valid"]    = 1
            except Exception as e:
                print(f"j2-cal: save error: {e}")
        prev_btn = btn

        if h["cal-valid"]:
            delta_counts = enc_now - int(h["cal-encoder"])
            h["predicted-pos"] = (J2_REF_POSITION_MM
                                  + delta_counts * J2_SCALE_MM_PER_COUNT)
        else:
            h["predicted-pos"] = 0.0

except KeyboardInterrupt:
    raise SystemExit
