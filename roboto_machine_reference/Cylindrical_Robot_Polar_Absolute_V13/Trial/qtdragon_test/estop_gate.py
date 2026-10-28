#!/usr/bin/env python3
"""
estop_gate.py — Block F1 (E-stop reset) until all drives report ready.

Pins:
  drives-ready  (bit, IN)  AND of cia402.is-readyN — true when all 3 drives
                           have valid PDOs and no fault.
  user-request  (bit, IN)  iocontrol.0.user-request-enable — pulses high
                           each time the operator presses F1.
  blocked-count (s32, OUT) increments each time we block an F1 attempt
                           (for debug / pyvcp display if wanted).

When user-request rises and drives-ready is false we pop up a Tk dialog:
"Drives not ready — wait or restart LinuxCNC." The dialog runs in a daemon
thread so the HAL polling loop is not blocked.

The actual gating of emc-enable-in is done in HAL (and2 of user-enable-out
and drives-ready). This component is purely for the visual warning.
"""
import hal
import time
import threading

try:
    import tkinter as tk
    from tkinter import messagebox
    HAS_TK = True
except Exception:
    HAS_TK = False


def show_popup():
    if not HAS_TK:
        print("estop-gate: WARN — tkinter unavailable, no popup shown")
        return

    def _run():
        try:
            root = tk.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            messagebox.showwarning(
                "E-Stop blocked",
                "Drives are not ready yet.\n\n"
                "Wait until the DRO shows live encoder values, then press F1.\n\n"
                "If this persists, restart LinuxCNC.",
                parent=root,
            )
            root.destroy()
        except Exception as e:
            print(f"estop-gate: popup error: {e}")

    threading.Thread(target=_run, daemon=True).start()


h = hal.component("estop-gate")
h.newpin("drives-ready",  hal.HAL_BIT, hal.HAL_IN)
h.newpin("user-request",  hal.HAL_BIT, hal.HAL_IN)
h.newpin("blocked-count", hal.HAL_S32, hal.HAL_OUT)
h.ready()

print("estop-gate: Ready — F1 will warn if drives not ready")

prev_req = False
blocked = 0

try:
    while True:
        time.sleep(0.05)
        req = bool(h["user-request"])
        ready = bool(h["drives-ready"])

        # Rising edge of F1
        if req and not prev_req:
            if not ready:
                blocked += 1
                h["blocked-count"] = blocked
                print(f"estop-gate: F1 blocked — drives not ready (count={blocked})")
                show_popup()
            else:
                print("estop-gate: F1 accepted (drives ready)")
        prev_req = req
except KeyboardInterrupt:
    raise SystemExit
