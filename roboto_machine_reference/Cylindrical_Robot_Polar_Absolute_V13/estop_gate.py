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

When user-request rises and drives-ready is false we pop up a Qt dialog
themed with QtDragon's dark_grey stylesheet so it matches the main GUI
("Drives not ready — wait or restart LinuxCNC").

The actual gating of emc-enable-in is done in HAL (and2 of user-enable-out
and drives-ready). This component is purely for the visual warning.
"""
import hal
import os
import sys

from PyQt5 import QtCore, QtWidgets


# Load the QtDragon dark theme so the popup matches the rest of the GUI
# instead of the system-default Tk/Qt look. Ships next to the handler.
_QSS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'qtdragon_hd', 'dark_grey.qss')


def _load_qss():
    try:
        with open(_QSS_PATH, 'r') as _f:
            return _f.read()
    except OSError:
        return ''


# QApplication must live on (and be created from) the main thread; the
# HAL poll runs on the same thread via a QTimer so QMessageBox.exec_()
# blocks only the polling, never the GUI thread of another process.
app = QtWidgets.QApplication(sys.argv if sys.argv else ['estop_gate'])
qss = _load_qss()
if qss:
    app.setStyleSheet(qss)


def show_popup():
    box = QtWidgets.QMessageBox()
    box.setWindowTitle("E-Stop blocked")
    box.setIcon(QtWidgets.QMessageBox.Warning)
    box.setText("Drives are not ready yet.")
    box.setInformativeText(
        "Wait until the DRO shows live encoder values, then press F1.\n\n"
        "If this persists, restart LinuxCNC.")
    box.setStandardButtons(QtWidgets.QMessageBox.Ok)
    box.setWindowFlags(box.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
    box.exec_()


h = hal.component("estop-gate")
h.newpin("drives-ready",  hal.HAL_BIT, hal.HAL_IN)
h.newpin("user-request",  hal.HAL_BIT, hal.HAL_IN)
h.newpin("blocked-count", hal.HAL_S32, hal.HAL_OUT)
h.ready()

print("estop-gate: Ready — F1 will warn if drives not ready")

_state = {'prev_req': False, 'blocked': 0}


def _poll():
    req = bool(h["user-request"])
    ready = bool(h["drives-ready"])
    # Rising edge of F1
    if req and not _state['prev_req']:
        if not ready:
            _state['blocked'] += 1
            h["blocked-count"] = _state['blocked']
            print(f"estop-gate: F1 blocked — drives not ready (count={_state['blocked']})")
            show_popup()
        else:
            print("estop-gate: F1 accepted (drives ready)")
    _state['prev_req'] = req


_timer = QtCore.QTimer()
_timer.timeout.connect(_poll)
_timer.start(50)  # 50 ms — same cadence as the previous time.sleep() loop

try:
    sys.exit(app.exec_())
except KeyboardInterrupt:
    raise SystemExit
