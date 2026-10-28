#!/usr/bin/env python3
"""
abs_home.py — Compute absolute-encoder HOME / HOME_OFFSET at machine-on time.

Replaces the pre-launch halrun + SDO 0x6064 read in start_linuxcnc.sh.
By the time the operator clears E-stop (F1) and powers on (F2), lcec has
been running in the servo thread and the encoder feedback pins already hold
live counts. We use those counts to compute home positions from the
*_calibration.json files, set ini.N.home / ini.N.home_offset via halcmd, then
pulse trigger-home (wired to halui.home-all in postgui.hal).

Pins:
  j0-enc-raw  (float, IN)   raw encoder counts (angle-pos-fb-raw, J0 slave 0)
  j1-enc-raw  (float, IN)   raw encoder counts (radius-pos-fb-raw, J1 slave 2)
  j2-enc-raw  (float, IN)   raw encoder counts (z-pos-fb-raw,     J2 slave 1)
  machine-on  (bit,   IN)   halui.machine.is-on
  trigger-home(bit,   OUT)  pulses high after offsets are written
  ready       (bit,   OUT)  high after at least one successful compute
"""
import hal
import time
import os
import json
import subprocess

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_cal(name):
    path = os.path.join(SCRIPT_DIR, f"{name}_calibration.json")
    if not os.path.exists(path):
        print(f"abs-home: {name}: no calibration JSON, leaving HOME defaults")
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        print(f"abs-home: {name}: failed to load {path}: {e}")
        return None


j0_cal = load_cal("j0")
j1_cal = load_cal("j1")
j2_cal = load_cal("j2")


def setp(pin, value):
    try:
        subprocess.run(["halcmd", "setp", pin, f"{value:.6f}"], check=True)
        return True
    except Exception as e:
        print(f"abs-home: setp {pin}={value} failed: {e}")
        return False


def compute(cal, enc_now, pos_key, enc_key, scale_key, lo, hi, label):
    if cal is None:
        return None
    try:
        home = cal[pos_key] + (enc_now - cal[enc_key]) * cal[scale_key]
    except KeyError as e:
        print(f"abs-home: {label}: calibration missing key {e}")
        return None
    if home < lo or home > hi:
        print(f"abs-home: WARN {label} computed {home:.3f} outside [{lo},{hi}], skipped")
        return None
    print(f"abs-home: {label}: enc={enc_now:.0f} -> home={home:.6f}")
    return home


h = hal.component("abs-home")
h.newpin("j0-enc-raw",  hal.HAL_FLOAT, hal.HAL_IN)
h.newpin("j1-enc-raw",  hal.HAL_FLOAT, hal.HAL_IN)
h.newpin("j2-enc-raw",  hal.HAL_FLOAT, hal.HAL_IN)
h.newpin("machine-on",  hal.HAL_BIT,   hal.HAL_IN)
h.newpin("trigger-home", hal.HAL_BIT,  hal.HAL_OUT)
h.newpin("ready",       hal.HAL_BIT,   hal.HAL_OUT)
h.ready()

print("abs-home: Ready — will compute on F2 (machine-on rising edge)")

prev_on = False
pulse_until = 0.0

try:
    while True:
        time.sleep(0.05)
        on = bool(h["machine-on"])

        if on and not prev_on:
            j0_enc = h["j0-enc-raw"]
            j1_enc = h["j1-enc-raw"]
            j2_enc = h["j2-enc-raw"]
            print(f"abs-home: F2 detected, encoders J0={j0_enc:.0f} J1={j1_enc:.0f} J2={j2_enc:.0f}")

            j0_home = compute(j0_cal, j0_enc,
                              "j0_cal_position_deg", "j0_cal_encoder",
                              "j0_scale_deg_per_count", -360, 360, "J0")
            j1_home = compute(j1_cal, j1_enc,
                              "j1_cal_position_mm",  "j1_cal_encoder",
                              "j1_scale_mm_per_count", 650, 2500, "J1")
            j2_home = compute(j2_cal, j2_enc,
                              "j2_cal_position_mm",  "j2_cal_encoder",
                              "j2_scale_mm_per_count", 0, 2000, "J2")

            for idx, val in ((0, j0_home), (1, j1_home), (2, j2_home)):
                if val is None:
                    continue
                setp(f"ini.{idx}.home",         val)
                setp(f"ini.{idx}.home_offset",  val)

            # Brief settle so motion sees the new ini.N.home_offset before
            # halui.home-all is asserted.
            time.sleep(0.15)

            h["ready"] = True
            h["trigger-home"] = True
            pulse_until = time.time() + 0.5

        if h["trigger-home"] and time.time() > pulse_until:
            h["trigger-home"] = False

        prev_on = on
except KeyboardInterrupt:
    raise SystemExit
