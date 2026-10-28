"""
Print Calibrate — Qt-embedded G-code offset tool.

Lives inside the PRINT CAL top tab page (main_tab_Page_PrintCal). Replaces
the legacy standalone Tkinter gcode_viewer.py.

Workflow:
  1. The program loaded in QtDragon's main viewer is mirrored in here
     automatically (set_source_file), drawn against the machine's
     printable area — the MAX print-radius circle it must stay inside
     and the MIN dead-zone circle it must stay outside.
  2. Position it: drag on the canvas to move, Ctrl+drag to rotate, or
     type a machine X/Y and click PLACE START HERE to drop the
     program's start point on an exact coordinate. Points that fall
     outside the printable area turn red immediately.
  3. EXPORT -> writes the positioned file to
     <root>/Print Calibrate/output/<orig>_offset_<timestamp>.ngc
     (save only — it does not run it).
  4. LOAD -> writes the positioned file the same way, then emits
     request_load -> QtDragon's handler calls ACTION.OPEN_PROGRAM() to
     load it into the software so it can be run. LOAD is independent of
     EXPORT — it never requires an export first and always uses the
     model's current position.

The Δx/Δy/Δθ offsets are internal state (self._ox/_oy/_oa) driven by
the canvas and PLACE START HERE — there are deliberately no numeric
entry boxes for them, so the canvas gets the whole panel.

Pure functions parse_gcode_lines() and write_offset_file() carry the
G-code math; the rest is Qt UI.
"""

import math
import os
import re
import time

from PyQt5 import QtCore, QtGui, QtWidgets


# ─────────────────── reachable work envelope ───────────────────
# The robot is polar: a Cartesian G-code point (x, y) is reachable only if its
# distance from the rotary center, d = sqrt(x² + y²), maps to a joint radius
# within the JOINT_1 limits. With a perpendicular tool offset:
#       d = sqrt(r² + TOOL_OFFSET²)
# These MUST stay in sync with gcode_validator.py (LinuxCNC's [FILTER]) and
# JOINT_1 MIN/MAX_LIMIT in cylindrical_robot_qtdragon.ini, so the live preview,
# the validator, and the machine all agree on what "in reach" means.
TOOL_OFFSET = -235.0
MIN_RADIUS = math.sqrt(650.0**2 + TOOL_OFFSET**2)    # ~691.3 mm
MAX_RADIUS = math.sqrt(2500.0**2 + TOOL_OFFSET**2)   # ~2511.0 mm


def classify_moves(moves):
    """Flag moves whose tool-tip leaves the reachable annulus.

    Returns (bad_idx, rmin, rmax): a set of indices into `moves` that are out
    of reach, plus the min/max tool-tip radius seen (None if no moves). Shared
    by the live preview highlight, the status line, and the export guard."""
    bad = set()
    rmin = rmax = None
    for i, m in enumerate(moves):
        r = math.hypot(m.x, m.y)
        rmin = r if rmin is None else min(rmin, r)
        rmax = r if rmax is None else max(rmax, r)
        if r < MIN_RADIUS or r > MAX_RADIUS:
            bad.add(i)
    return bad, rmin, rmax


# ───────────────────── parse / write helpers ─────────────────────

_X_RE = re.compile(r'(X)([+-]?\d*\.?\d+)', re.IGNORECASE)
_Y_RE = re.compile(r'(Y)([+-]?\d*\.?\d+)', re.IGNORECASE)
_CMD_RE = re.compile(r'^\s*G0?[0123]\b', re.IGNORECASE)
_CMD_NOSPACE_RE = re.compile(r'^\s*G0?[0123][XYZ]', re.IGNORECASE)


class GCodeMove:
    """Single parsed move — pure data, no Qt deps."""
    __slots__ = ('cmd', 'x', 'y', 'line_num', 'raw')

    def __init__(self, cmd, x, y, line_num=0, raw=""):
        self.cmd = cmd  # 'G0' or 'G1' (G2/G3 normalized to G1 for preview)
        self.x = x
        self.y = y
        self.line_num = line_num
        self.raw = raw


def parse_gcode_lines(raw_lines):
    """Returns a list of GCodeMove. Tracks last known X/Y for lines that
    only specify one axis."""
    moves = []
    last_x = 0.0
    last_y = 0.0
    for i, line in enumerate(raw_lines):
        stripped = line.strip().upper()
        if not (_CMD_RE.match(stripped) or _CMD_NOSPACE_RE.match(stripped)):
            continue
        xm = _X_RE.search(line)
        ym = _Y_RE.search(line)
        if not (xm or ym):
            continue
        x = float(xm.group(2)) if xm else last_x
        y = float(ym.group(2)) if ym else last_y
        cmd = 'G0' if stripped.startswith(('G00', 'G0 ', 'G0X', 'G0Y',
                                            'G0Z')) else 'G1'
        moves.append(GCodeMove(cmd, x, y, line_num=i + 1, raw=line.rstrip()))
        last_x = x
        last_y = y
    return moves


def _append_axis_if_missing(line_text, axis_name, axis_value):
    if re.search(rf'{axis_name}[+-]?\d*\.?\d+', line_text, re.IGNORECASE):
        return line_text
    newline = "\n" if line_text.endswith("\n") else ""
    core = line_text[:-1] if newline else line_text
    split_idx = len(core)
    for marker in (";", "("):
        marker_idx = core.find(marker)
        if marker_idx != -1:
            split_idx = min(split_idx, marker_idx)
    head = core[:split_idx].rstrip()
    tail = core[split_idx:]
    return f"{head} {axis_name}{axis_value:.3f}{tail}{newline}"


def rotate_translate(x, y, oa, ox, oy, cx=0.0, cy=0.0):
    """Rotate (x, y) by oa degrees (CCW positive) about pivot (cx, cy),
    then translate by (ox, oy). Shared by the preview and the file export
    so the on-screen overlay always matches the saved G-code."""
    a = math.radians(oa)
    cos_a, sin_a = math.cos(a), math.sin(a)
    rx, ry = x - cx, y - cy
    nx = rx * cos_a - ry * sin_a + cx + ox
    ny = rx * sin_a + ry * cos_a + cy + oy
    return nx, ny


def write_offset_file(save_path, raw_lines, source_name, ox, oy, oa,
                      cx=0.0, cy=0.0):
    """Apply rotation (oa deg, CCW positive, about pivot (cx, cy)) then
    translation (ox, oy) to every X/Y coordinate in raw_lines and write to
    save_path."""
    last_x = 0.0
    last_y = 0.0
    os.makedirs(os.path.dirname(os.path.abspath(save_path)), exist_ok=True)
    with open(save_path, 'w') as f_out:
        f_out.write("; === G-Code Offset Applied ===\n")
        f_out.write(f"; Delta X: {ox:+.3f} mm\n")
        f_out.write(f"; Delta Y: {oy:+.3f} mm\n")
        f_out.write(f"; Delta Tilt: {oa:+.3f} deg (about {cx:.3f}, {cy:.3f})\n")
        f_out.write(f"; Source: {source_name}\n\n")
        for line in raw_lines:
            stripped = line.strip().upper()
            if _CMD_RE.match(stripped) or _CMD_NOSPACE_RE.match(stripped):
                xm = _X_RE.search(line)
                ym = _Y_RE.search(line)
                if xm or ym:
                    orig_x = float(xm.group(2)) if xm else last_x
                    orig_y = float(ym.group(2)) if ym else last_y
                    new_x, new_y = rotate_translate(orig_x, orig_y, oa,
                                                    ox, oy, cx, cy)
                    new_line = _X_RE.sub(f'X{new_x:.3f}', line, count=1)
                    new_line = _Y_RE.sub(f'Y{new_y:.3f}', new_line, count=1)
                    new_line = _append_axis_if_missing(new_line, "X", new_x)
                    new_line = _append_axis_if_missing(new_line, "Y", new_y)
                    f_out.write(new_line)
                    last_x = orig_x
                    last_y = orig_y
                else:
                    f_out.write(line)
            else:
                f_out.write(line)


# ──────────────────────── canvas widget ────────────────────────

class GCodeCanvas(QtWidgets.QWidget):
    """Toolpath preview — original (dim) + offset (bright) overlay.

    Also draws the machine's reachable envelope: the MAX_RADIUS circle the
    part must stay inside and the MIN_RADIUS circle it must stay outside, so
    reach is readable at a glance while dragging.

    - Left-drag: move the model (adjusts Δx / Δy offset live)
    - Ctrl+Left-drag: rotate the model about its center (adjusts Δθ live)
    - Wheel: zoom around cursor
    - Middle-drag: pan
    - Double-click: re-fit the view
    - Mouse hover: world-coordinate readout in the bottom-left corner
    - Auto-fit on first data load
    """

    # Emitted on left-drag with the incremental world-space (dx, dy) in mm.
    # The parent widget folds this into the Δx / Δy offset entries.
    offset_dragged = QtCore.pyqtSignal(float, float)
    # Emitted on Ctrl+left-drag with the incremental rotation in degrees
    # (CCW positive). The parent folds this into the Δθ entry.
    rotate_dragged = QtCore.pyqtSignal(float)

    # Industrial QtDragon-themed palette — dark machine-panel greys with the
    # QtDragon blue/green/red accents, so the preview reads like the rest of
    # the GUI rather than a foreign widget.
    BG       = QtGui.QColor('#2b2b2b')  # machine-panel dark grey
    GRID     = QtGui.QColor('#383838')  # faint grid
    GRID_MAJ = QtGui.QColor('#454545')  # emphasised major grid line
    AXIS     = QtGui.QColor('#6a6a6a')  # centre cross-hair
    ORIG_G1  = QtGui.QColor('#c8b18a')  # muted amber — the original part
    OFF_G1   = QtGui.QColor('#00FF00')  # QtDragon green — positioned part
    RAPID    = QtGui.QColor('#00aaff')  # QtDragon blue — rapid moves
    START    = QtGui.QColor('#00FF00')  # green start node
    END      = QtGui.QColor('#FFFFD0')  # status-yellow end node
    TEXT     = QtGui.QColor('#FFFFD0')  # QtDragon status-label yellow
    BAD      = QtGui.QColor('#FF0000')  # QtDragon red — out-of-reach segment
    ENV      = QtGui.QColor('#00aaff')  # QtDragon blue — print-area boundary
    ENV_FILL = QtGui.QColor(0, 170, 255, 20)   # faint blue wash over the ring
    ENV_BAD  = QtGui.QColor(255, 0, 0, 22)      # red wash when out of reach

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 280)
        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self._moves_orig = []
        self._moves_off = []
        self._bad_off = set()  # indices of out-of-reach offset moves
        self._bbox = (0.0, 0.0, 100.0, 100.0)
        self._zoom = 1.0
        self._pan_x = 0.0
        self._pan_y = 0.0
        self._needs_fit = False
        self._mouse_world = None
        self._pan_anchor = None
        self._offset_drag_last = None   # last screen pos while left-dragging
        self._rotate_last_angle = None  # last cursor angle (rad) while rotating

    # ── public API ──
    def set_moves(self, moves_orig, moves_off, bad_off=None):
        self._moves_orig = moves_orig
        self._moves_off = moves_off
        self._bad_off = bad_off or set()
        all_moves = list(moves_orig) + list(moves_off)
        if all_moves:
            xs = [m.x for m in all_moves]
            ys = [m.y for m in all_moves]
            self._bbox = (min(xs), min(ys), max(xs), max(ys))
        self._needs_fit = True
        self.update()

    def update_offset_moves(self, moves_off, bad_off=None):
        """Refresh only the offset (bright) overlay without recomputing the
        bounding box or re-fitting — used for live mouse-drag updates so the
        view doesn't jump while the operator drags."""
        self._moves_off = moves_off
        self._bad_off = bad_off or set()
        self.update()

    def fit_to_view(self):
        w = self.width()
        h = self.height()
        if w <= 4 or h <= 4:
            self._needs_fit = True
            return
        # Fit to the toolpath, but always keep the rotary centre (0,0) in
        # frame so the operator can see how far the model sits from the
        # centre relative to the MAX print-radius circle.
        bx0 = min(self._bbox[0], 0.0)
        by0 = min(self._bbox[1], 0.0)
        bx1 = max(self._bbox[2], 0.0)
        by1 = max(self._bbox[3], 0.0)
        bw = bx1 - bx0
        bh = by1 - by0
        if bw <= 0 or bh <= 0:
            self._zoom = 1.0
            self._pan_x = w / 2.0
            self._pan_y = h / 2.0
        else:
            margin = 30
            sx = (w - 2 * margin) / bw
            sy = (h - 2 * margin) / bh
            self._zoom = min(sx, sy)
            cx = (bx0 + bx1) / 2.0
            cy = (by0 + by1) / 2.0
            self._pan_x = w / 2.0 - cx * self._zoom
            self._pan_y = h / 2.0 + cy * self._zoom
        self._needs_fit = False
        self.update()

    # ── coordinate helpers ──
    def _world_to_screen(self, x, y):
        return (x * self._zoom + self._pan_x,
                -y * self._zoom + self._pan_y)

    def _screen_to_world(self, sx, sy):
        if self._zoom <= 0:
            return (0.0, 0.0)
        return ((sx - self._pan_x) / self._zoom,
                -(sy - self._pan_y) / self._zoom)

    def _model_pivot(self):
        """Rotation pivot = bounding-box center of the original toolpath."""
        if not self._moves_orig:
            return (0.0, 0.0)
        xs = [m.x for m in self._moves_orig]
        ys = [m.y for m in self._moves_orig]
        return ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)

    def _cursor_angle(self, sx, sy):
        """Angle (rad) of the cursor about the model pivot, in world space."""
        wx, wy = self._screen_to_world(sx, sy)
        px, py = self._model_pivot()
        return math.atan2(wy - py, wx - px)

    @staticmethod
    def _nice_step(rough):
        if rough <= 0:
            return 1.0
        mag = 10 ** math.floor(math.log10(rough))
        norm = rough / mag
        if norm < 2:
            return 1 * mag
        if norm < 5:
            return 2 * mag
        if norm < 10:
            return 5 * mag
        return 10 * mag

    # ── paint ──
    def paintEvent(self, ev):
        if self._needs_fit:
            self.fit_to_view()
        p = QtGui.QPainter(self)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        p.fillRect(self.rect(), self.BG)
        self._paint_grid(p)
        self._paint_axes(p)
        self._paint_envelope(p)
        self._paint_moves(p, self._moves_orig, self.ORIG_G1, dim=True)
        if self._moves_off and self._moves_off is not self._moves_orig:
            self._paint_moves(p, self._moves_off, self.OFF_G1, dim=False,
                              bad_idx=self._bad_off)
        self._paint_hud(p)
        # Inset instrument frame around the whole screen.
        p.setPen(QtGui.QPen(QtGui.QColor('#202020'), 1))
        p.setBrush(QtCore.Qt.NoBrush)
        p.drawRect(0, 0, self.width() - 1, self.height() - 1)

    def _paint_grid(self, p):
        # Minor grid + emphasised major line every 5 steps, for a CAD /
        # instrument-panel read rather than a flat mesh.
        step = self._nice_step(60.0 / max(self._zoom, 0.0001))
        x_min, y_min = self._screen_to_world(0, self.height())
        x_max, y_max = self._screen_to_world(self.width(), 0)
        minor = QtGui.QPen(self.GRID, 1, QtCore.Qt.SolidLine)
        major = QtGui.QPen(self.GRID_MAJ, 1, QtCore.Qt.SolidLine)
        x = math.floor(x_min / step) * step
        while x <= x_max:
            sx, _ = self._world_to_screen(x, 0)
            p.setPen(major if round(x / step) % 5 == 0 else minor)
            p.drawLine(int(sx), 0, int(sx), self.height())
            x += step
        y = math.floor(y_min / step) * step
        while y <= y_max:
            _, sy = self._world_to_screen(0, y)
            p.setPen(major if round(y / step) % 5 == 0 else minor)
            p.drawLine(0, int(sy), self.width(), int(sy))
            y += step

    def _paint_axes(self, p):
        ox, oy = self._world_to_screen(0, 0)
        p.setPen(QtGui.QPen(self.AXIS, 1, QtCore.Qt.DashLine))
        if 0 <= ox <= self.width():
            p.drawLine(int(ox), 0, int(ox), self.height())
        if 0 <= oy <= self.height():
            p.drawLine(0, int(oy), self.width(), int(oy))
        # Rotary-centre marker (the robot's pivot / world origin).
        if -8 <= ox <= self.width() + 8 and -8 <= oy <= self.height() + 8:
            p.setPen(QtGui.QPen(self.AXIS, 1.4))
            p.setBrush(QtCore.Qt.NoBrush)
            p.drawEllipse(QtCore.QPointF(ox, oy), 5, 5)
            p.drawLine(int(ox) - 8, int(oy), int(ox) + 8, int(oy))
            p.drawLine(int(ox), int(oy) - 8, int(ox), int(oy) + 8)

    def _paint_envelope(self, p):
        """Draw the machine's reachable print area centred on the rotary
        centre (world origin):

        - MAX_RADIUS: the machine's maximum print radius. A model is
          printable only if the whole toolpath stays INSIDE this circle,
          so it reads at a glance as "within reach vs. out of reach".
        - MIN_RADIUS: the unreachable dead-zone hole around the centre.

        The disk between the two circles is given a faint wash so the
        printable annulus is obvious while dragging; it turns red the moment
        any positioned point leaves the reachable area."""
        cx, cy = self._world_to_screen(0.0, 0.0)
        r_max = MAX_RADIUS * self._zoom
        r_min = MIN_RADIUS * self._zoom
        center = QtCore.QPointF(cx, cy)
        out = bool(self._bad_off)
        edge = self.BAD if out else self.ENV

        # Faint wash filling the printable annulus (max disk minus min hole);
        # red-tinted when the positioned part is out of reach.
        p.setPen(QtCore.Qt.NoPen)
        p.setBrush(self.ENV_BAD if out else self.ENV_FILL)
        ring = QtGui.QPainterPath()
        ring.addEllipse(center, r_max, r_max)
        hole = QtGui.QPainterPath()
        hole.addEllipse(center, r_min, r_min)
        p.drawPath(ring.subtracted(hole))

        # MAX print radius — the prominent boundary the model must stay within.
        p.setBrush(QtCore.Qt.NoBrush)
        p.setPen(QtGui.QPen(edge, 2.2, QtCore.Qt.SolidLine))
        p.drawEllipse(center, r_max, r_max)
        # MIN radius — inner dead-zone, drawn lighter/dashed.
        p.setPen(QtGui.QPen(edge, 1.2, QtCore.Qt.DashLine))
        p.drawEllipse(center, r_min, r_min)

    def _paint_moves(self, p, moves, g1_color, dim=False, bad_idx=None):
        if not moves:
            return
        alpha = 100 if dim else 230
        g1_pen = QtGui.QPen(
            QtGui.QColor(g1_color.red(), g1_color.green(),
                         g1_color.blue(), alpha),
            1.5 if dim else 2.0)
        rapid_pen = QtGui.QPen(
            QtGui.QColor(self.RAPID.red(), self.RAPID.green(),
                         self.RAPID.blue(), alpha),
            1, QtCore.Qt.DashLine)
        bad_pen = QtGui.QPen(self.BAD, 3.0)
        path_g1 = QtGui.QPainterPath()
        path_rapid = QtGui.QPainterPath()
        path_bad = QtGui.QPainterPath()
        prev = None
        for i, m in enumerate(moves):
            pt = self._world_to_screen(m.x, m.y)
            if prev is not None:
                # A segment is out-of-reach if either endpoint is flagged.
                if bad_idx and (i in bad_idx or (i - 1) in bad_idx):
                    tgt = path_bad
                else:
                    tgt = path_rapid if m.cmd == 'G0' else path_g1
                tgt.moveTo(prev[0], prev[1])
                tgt.lineTo(pt[0], pt[1])
            prev = pt
        p.setPen(rapid_pen)
        p.drawPath(path_rapid)
        p.setPen(g1_pen)
        p.drawPath(path_g1)
        if bad_idx:
            p.setPen(bad_pen)
            p.drawPath(path_bad)
        if not dim:
            s = self._world_to_screen(moves[0].x, moves[0].y)
            e = self._world_to_screen(moves[-1].x, moves[-1].y)
            p.setPen(QtCore.Qt.NoPen)
            p.setBrush(self.START)
            p.drawEllipse(QtCore.QPointF(s[0], s[1]), 4, 4)
            p.setBrush(self.END)
            p.drawRect(int(e[0]) - 4, int(e[1]) - 4, 8, 8)

    def _paint_hud(self, p):
        f = QtGui.QFont("Lato Heavy")
        f.setPointSize(9)
        p.setFont(f)
        bw = self._bbox[2] - self._bbox[0]
        bh = self._bbox[3] - self._bbox[1]
        p.setPen(self.TEXT)
        if self._moves_orig:
            p.drawText(10, 18,
                       f"{len(self._moves_orig)} MOVES   ·   "
                       f"BBOX {bw:.1f} × {bh:.1f} mm")
        # Live world-coordinate readout, right-aligned like a DRO.
        if self._mouse_world is not None:
            txt = f"X {self._mouse_world[0]:+.2f}    "\
                  f"Y {self._mouse_world[1]:+.2f}"
            p.setPen(QtGui.QColor('#00aaff'))
            p.drawText(10, self.height() - 10, txt)

    # ── events ──
    def wheelEvent(self, ev):
        delta = ev.angleDelta().y()
        if delta == 0:
            return
        factor = 1.18 if delta > 0 else (1.0 / 1.18)
        mx, my = ev.pos().x(), ev.pos().y()
        wx, wy = self._screen_to_world(mx, my)
        self._zoom *= factor
        self._pan_x = mx - wx * self._zoom
        self._pan_y = my + wy * self._zoom
        self.update()
        ev.accept()

    def mousePressEvent(self, ev):
        if ev.button() == QtCore.Qt.MiddleButton:
            self._pan_anchor = (ev.pos().x(), ev.pos().y(),
                                self._pan_x, self._pan_y)
            self.setCursor(QtCore.Qt.ClosedHandCursor)
        elif ev.button() == QtCore.Qt.LeftButton and self._moves_orig:
            if ev.modifiers() & QtCore.Qt.ControlModifier:
                # Ctrl+left-drag: rotate the model about its center
                self._rotate_last_angle = self._cursor_angle(
                    ev.pos().x(), ev.pos().y())
                self.setCursor(QtCore.Qt.CrossCursor)
            else:
                # Plain left-drag: move the model
                self._offset_drag_last = (ev.pos().x(), ev.pos().y())
                self.setCursor(QtCore.Qt.SizeAllCursor)

    def mouseReleaseEvent(self, ev):
        if ev.button() == QtCore.Qt.MiddleButton:
            self._pan_anchor = None
            self.unsetCursor()
        elif ev.button() == QtCore.Qt.LeftButton and (
                self._offset_drag_last is not None
                or self._rotate_last_angle is not None):
            self._offset_drag_last = None
            self._rotate_last_angle = None
            self.unsetCursor()

    def mouseMoveEvent(self, ev):
        if self._pan_anchor is not None:
            ax, ay, p0x, p0y = self._pan_anchor
            self._pan_x = p0x + (ev.pos().x() - ax)
            self._pan_y = p0y + (ev.pos().y() - ay)
        elif self._rotate_last_angle is not None:
            # Rotate: change in cursor angle about the pivot → Δθ (CCW +)
            cur = self._cursor_angle(ev.pos().x(), ev.pos().y())
            d = cur - self._rotate_last_angle
            # normalize the wraparound to (-π, π]
            d = (d + math.pi) % (2 * math.pi) - math.pi
            self._rotate_last_angle = cur
            if d:
                self.rotate_dragged.emit(math.degrees(d))
        elif self._offset_drag_last is not None and self._zoom > 0:
            # Convert the screen drag into a world-space (mm) delta and report
            # it. Screen Y is inverted relative to world Y.
            lx, ly = self._offset_drag_last
            dwx = (ev.pos().x() - lx) / self._zoom
            dwy = -(ev.pos().y() - ly) / self._zoom
            self._offset_drag_last = (ev.pos().x(), ev.pos().y())
            if dwx or dwy:
                self.offset_dragged.emit(dwx, dwy)
        self._mouse_world = self._screen_to_world(ev.pos().x(), ev.pos().y())
        self.update()

    def leaveEvent(self, ev):
        self._mouse_world = None
        self.update()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if self._needs_fit:
            self.fit_to_view()


# ──────────────────────── top widget ────────────────────────

class PrintCalWidget(QtWidgets.QWidget):
    """Embedded G-code offset tool. Drops into main_tab_Page_PrintCal."""

    # Emitted by the LOAD button with the absolute path of the positioned
    # file. The handler connects this to ACTION.OPEN_PROGRAM so QtDragon
    # loads the program and it becomes runnable. LOAD writes the positioned
    # file itself, so it works with no prior EXPORT; EXPORT only saves a copy.
    request_load = QtCore.pyqtSignal(str)

    # Themed status-bar skins — an inset instrument read-out in the QtDragon
    # palette (muted normal, red alarm).
    _STATUS_OK = ('color:#B0B0D0; background:#333333;'
                  ' border-top:1px solid #202020; padding:5px 8px;'
                  ' font: 10pt "Lato Heavy";')
    _STATUS_WARN = ('color:#FF6060; background:#3a2626;'
                    ' border-top:1px solid #202020; padding:5px 8px;'
                    ' font: bold 10pt "Lato Heavy";')

    def __init__(self, auto_save_dir, parent=None):
        super().__init__(parent)
        self._auto_save_dir = auto_save_dir
        self._gcode_path = None
        self._raw_lines = []
        self._moves_orig = []
        # Offset state lives here (no on-screen Δx/Δy/Δθ boxes) — driven by
        # canvas drags and PLACE START HERE, applied on export.
        self._ox = 0.0
        self._oy = 0.0
        self._oa = 0.0
        # Absolute path of the most recently written file (by EXPORT or
        # LOAD), or None. Only used so the main-viewer mirror ignores our
        # own output; it no longer gates the LOAD button.
        self._last_export_path = None
        self._build_ui()

    # QtDragon-style button skin: the reflected blue→dark gradient with an
    # accent border, hover/pressed green, greyed when disabled. Matches the
    # ActionButtons in the main GUI so the panel reads as one instrument.
    @staticmethod
    def _btn_qss(accent):
        return (
            "QPushButton {"
            " background: qlineargradient(spread:reflect, x1:0.5, y1:0,"
            " x2:0.5, y2:1, stop:0 rgba(120,140,180,255),"
            " stop:0.3 rgba(11,22,33,255));"
            f" border: 2px solid {accent}; border-radius: 4px;"
            " font: bold 10pt \"Lato Heavy\"; color: white;"
            " padding: 4px 14px; }"
            " QPushButton:hover { border: 2px solid #00FF00; }"
            " QPushButton:pressed { border-color: #00FF00; color: #00FF00; }"
            " QPushButton:disabled { color: #808080; border: 1px solid #444; }")

    # ── UI ──
    def _build_ui(self):
        # Tight margins + no title/label chrome: the whole panel is given
        # over to the graph. The only controls are the PLACE START HERE
        # feature and the two LOAD / EXPORT buttons.
        self.setStyleSheet(
            'PrintCalWidget { background: #404040; }'
            'QLabel { color: #E1E1E1; font: bold 10pt "Lato Heavy"; }')
        v = QtWidgets.QVBoxLayout(self)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(6)

        # ─ Single control row: PLACE START HERE  +  LOAD / EXPORT ─
        # Type the machine X/Y you read in calibrate mode; PLACE drops the
        # program's START point exactly there (updating the internal offset).
        row = QtWidgets.QHBoxLayout()
        row.setSpacing(6)

        # OPEN: pick a G-code file directly into this tab (the panel also
        # auto-mirrors whatever is loaded in the main viewer). Always enabled.
        self.btn_open = QtWidgets.QPushButton("📁  OPEN G-CODE")
        self.btn_open.setMinimumHeight(42)
        self.btn_open.setMinimumWidth(150)
        self.btn_open.setStyleSheet(self._btn_qss("#00aaff"))
        self.btn_open.setToolTip(
            "Open a G-code file directly in this tab. (The Print Calibration "
            "tab also mirrors whatever is loaded in the main viewer.)")
        self.btn_open.clicked.connect(self._on_open)
        row.addWidget(self.btn_open)

        row.addSpacing(12)
        row.addWidget(QtWidgets.QLabel("PLACE START AT (mm):"))

        self.ent_tx = self._make_offset_entry()
        self.ent_ty = self._make_offset_entry()
        for lbl_text, entry in (("X", self.ent_tx), ("Y", self.ent_ty)):
            row.addWidget(QtWidgets.QLabel(lbl_text))
            row.addWidget(entry)
            row.addSpacing(4)

        self.btn_place = QtWidgets.QPushButton("PLACE START HERE")
        self.btn_place.setMinimumHeight(42)
        self.btn_place.setMinimumWidth(160)
        self.btn_place.setStyleSheet(self._btn_qss("#00aaff"))
        self.btn_place.setToolTip(
            "Move the program so its START point lands at the X/Y above "
            "(read these from the DRO in calibrate mode).")
        self.btn_place.clicked.connect(self._on_place_absolute)
        self.btn_place.setEnabled(False)
        row.addWidget(self.btn_place)

        # FIT: re-fit the view to the toolpath (also on canvas double-click).
        self.btn_fit = QtWidgets.QPushButton("⟲  FIT")
        self.btn_fit.setMinimumHeight(42)
        self.btn_fit.setMinimumWidth(80)
        self.btn_fit.setStyleSheet(self._btn_qss("#6a6a6a"))
        self.btn_fit.setToolTip("Re-fit the view to the loaded program.")
        self.btn_fit.clicked.connect(lambda: self.canvas.fit_to_view())
        self.btn_fit.setEnabled(False)
        row.addWidget(self.btn_fit)

        row.addStretch(1)

        # EXPORT: save the positioned file to disk (no auto-run).
        self.btn_export = QtWidgets.QPushButton("💾  EXPORT")
        self.btn_export.setMinimumHeight(46)
        self.btn_export.setMinimumWidth(150)
        self.btn_export.setStyleSheet(self._btn_qss("#00FF00"))
        self.btn_export.setToolTip(
            "Save the positioned file to ./Print Calibrate/output/.")
        self.btn_export.clicked.connect(self._on_export)
        self.btn_export.setEnabled(False)
        row.addWidget(self.btn_export)

        # LOAD: position the file and push it straight into LinuxCNC so it
        # becomes runnable — no separate EXPORT step required.
        self.btn_load = QtWidgets.QPushButton("▶  LOAD")
        self.btn_load.setMinimumHeight(46)
        self.btn_load.setMinimumWidth(150)
        self.btn_load.setStyleSheet(self._btn_qss("#00aaff"))
        self.btn_load.setToolTip(
            "Load the positioned G-code directly into the software so it can "
            "be run. No export needed — uses the model's current position.")
        self.btn_load.clicked.connect(self._on_load)
        self.btn_load.setEnabled(False)
        row.addWidget(self.btn_load)

        v.addLayout(row)

        # ─ Canvas — given all remaining space ─
        self.canvas = GCodeCanvas()
        self.canvas.offset_dragged.connect(self._on_offset_drag)
        self.canvas.rotate_dragged.connect(self._on_rotate_drag)
        v.addWidget(self.canvas, 1)

        # ─ Status bar (inset instrument read-out) ─
        self.lbl_status = QtWidgets.QLabel("NO FILE LOADED")
        self.lbl_status.setStyleSheet(self._STATUS_OK)
        v.addWidget(self.lbl_status)

    @staticmethod
    def _make_offset_entry():
        e = QtWidgets.QLineEdit("0.000")
        e.setFixedWidth(80)
        e.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        v = QtGui.QDoubleValidator()
        v.setNotation(QtGui.QDoubleValidator.StandardNotation)
        v.setDecimals(3)
        e.setValidator(v)
        e.setStyleSheet(
            'QLineEdit { background: #202020; color: #FFFFD0;'
            ' border: 1px solid #555; border-radius: 3px; padding: 3px 6px;'
            ' font: bold 11pt "Monospace"; }'
            'QLineEdit:focus { border: 1px solid #00aaff; }')
        return e

    # ── public API ──
    def set_source_file(self, path):
        """Feed in the program currently loaded in QtDragon's main viewer so
        the calibration tool always mirrors it — the operator never opens a
        file from this tab. Ignores our own freshly-exported file (loading it
        would pointlessly reset the tool to the already-positioned output)."""
        if not path or path == self._last_export_path:
            return
        if os.path.abspath(path) == (
                os.path.abspath(self._gcode_path) if self._gcode_path else None):
            return
        self.load_file(path)

    def load_file(self, path):
        try:
            with open(path, 'r') as f:
                self._raw_lines = f.readlines()
        except OSError as e:
            QtWidgets.QMessageBox.warning(
                self, "Open failed",
                f"Could not read:\n{path}\n\n{e}")
            return False
        self._gcode_path = path
        # A new source clears the offset and any remembered output path.
        self._last_export_path = None
        self._ox = self._oy = self._oa = 0.0
        self._moves_orig = parse_gcode_lines(self._raw_lines)
        base = os.path.basename(path)
        if not self._moves_orig:
            self.lbl_status.setStyleSheet(self._STATUS_OK)
            self.lbl_status.setText(f"Loaded {base} — no X/Y moves found.")
        else:
            bad, rmin, rmax = classify_moves(self._moves_orig)
            if bad:
                self.lbl_status.setStyleSheet(self._STATUS_WARN)
                self.lbl_status.setText(
                    f"Loaded {base}: {len(self._moves_orig)} moves  ·  "
                    f"⚠ {len(bad)} already OUT OF REACH "
                    f"(r {rmin:.0f}–{rmax:.0f} mm; valid "
                    f"{MIN_RADIUS:.0f}–{MAX_RADIUS:.0f} mm) — apply an offset "
                    "to bring it into the work area.")
            else:
                self.lbl_status.setStyleSheet(self._STATUS_OK)
                self.lbl_status.setText(
                    f"Loaded: {base}  ·  {len(self._moves_orig)} moves  ·  "
                    f"{len(self._raw_lines)} lines  ·  all in reach.")
        # Prefill the absolute-placement fields with the part's current start
        # location, so they read as "where the start is now" and the operator
        # only edits the ones they want to retarget.
        sx, sy = self._start_point()
        self.ent_tx.setText(f"{sx:.3f}")
        self.ent_ty.setText(f"{sy:.3f}")
        self.canvas.set_moves(self._moves_orig, [])
        for b in (self.btn_export, self.btn_load, self.btn_place, self.btn_fit):
            b.setEnabled(True)
        return True

    def prefill_offsets(self, dx, dy, dt=0.0):
        """Stage-3 hook — pre-fill the internal offset from live machine
        state and refresh the preview."""
        self._ox, self._oy, self._oa = dx, dy, dt
        if self._moves_orig:
            self._refresh_offset_preview(dx, dy, dt, "Prefilled", refit=True)

    # ── slots ──
    def _on_open(self):
        """Open a G-code file directly into this tab via a file picker."""
        start = os.path.dirname(self._gcode_path) if self._gcode_path \
            else os.path.expanduser('~/linuxcnc/nc_files')
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open G-code", start,
            "G-code (*.ngc *.gcode *.nc *.txt);;All (*.*)")
        if path:
            self.load_file(path)

    def _pivot(self):
        """Rotation pivot = bounding-box center of the original toolpath."""
        if not self._moves_orig:
            return (0.0, 0.0)
        xs = [m.x for m in self._moves_orig]
        ys = [m.y for m in self._moves_orig]
        return ((min(xs) + max(xs)) / 2.0, (min(ys) + max(ys)) / 2.0)

    def _transform_moves(self, ox, oy, oa):
        cx, cy = self._pivot()
        out = []
        for m in self._moves_orig:
            nx, ny = rotate_translate(m.x, m.y, oa, ox, oy, cx, cy)
            out.append(GCodeMove(m.cmd, nx, ny, m.line_num, m.raw))
        return out

    def _start_point(self):
        """Reference point for absolute placement = the program's first
        X/Y move (where printing begins)."""
        if not self._moves_orig:
            return (0.0, 0.0)
        return (self._moves_orig[0].x, self._moves_orig[0].y)

    def _on_place_absolute(self):
        """Compute the offset that lands the START point on the typed machine
        X/Y, honoring any current rotation, then refresh the preview."""
        if not self._moves_orig:
            return
        try:
            tx = float(self.ent_tx.text() or '0')
            ty = float(self.ent_ty.text() or '0')
        except ValueError:
            QtWidgets.QMessageBox.warning(
                self, "Invalid", "Please enter numeric X / Y target values.")
            return
        oa = self._oa
        # Where the start point lands under rotation alone (no translation);
        # the needed translation is then target − that.
        sx, sy = self._start_point()
        cx, cy = self._pivot()
        base_x, base_y = rotate_translate(sx, sy, oa, 0.0, 0.0, cx, cy)
        self._ox = tx - base_x
        self._oy = ty - base_y
        self._refresh_offset_preview(self._ox, self._oy, oa, "Placed",
                                     refit=True)

    def _refresh_offset_preview(self, ox, oy, oa, verb, refit=False):
        """Recompute the offset overlay, flag any out-of-reach points (red on
        the canvas), push it to the view, and update the status line. APPLY
        re-fits the view (refit=True); live drags keep the current view."""
        moves_off = self._transform_moves(ox, oy, oa)
        bad, rmin, rmax = classify_moves(moves_off)
        if refit:
            self.canvas.set_moves(self._moves_orig, moves_off, bad)
        else:
            self.canvas.update_offset_moves(moves_off, bad)
        n = len(moves_off)
        # Live readout: where the START point currently lands.
        sx_now = moves_off[0].x if moves_off else 0.0
        sy_now = moves_off[0].y if moves_off else 0.0
        if bad:
            self.lbl_status.setStyleSheet(self._STATUS_WARN)
            self.lbl_status.setText(
                f"⚠ {len(bad)} of {n} points OUT OF REACH  "
                f"(r {rmin:.0f}–{rmax:.0f} mm; valid "
                f"{MIN_RADIUS:.0f}–{MAX_RADIUS:.0f} mm)  ·  start at "
                f"X{sx_now:+.1f} Y{sy_now:+.1f}  ·  "
                f"Δx={ox:+.3f} Δy={oy:+.3f} Δθ={oa:+.3f}°  — adjust before load/export.")
        else:
            self.lbl_status.setStyleSheet(self._STATUS_OK)
            self.lbl_status.setText(
                f"{verb}: start at X{sx_now:+.1f} Y{sy_now:+.1f}  ·  "
                f"Δx={ox:+.3f} Δy={oy:+.3f} Δθ={oa:+.3f}°  "
                f"— all {n} points in reach. Click Load to run it (or Export to save a copy).")
        return bad

    def _confirm_if_out_of_reach(self, ox, oy, oa):
        """Return True if export may proceed. If the offset path leaves the
        reachable annulus, confirm with the operator (default No) — this is
        the same envelope LinuxCNC's [FILTER] enforces, so an out-of-reach
        file would be rejected on load or mis-positioned by the kinematics."""
        moves_off = self._transform_moves(ox, oy, oa)
        bad, rmin, rmax = classify_moves(moves_off)
        if not bad:
            return True
        ret = QtWidgets.QMessageBox.warning(
            self, "Outside robot reach",
            f"{len(bad)} of {len(moves_off)} points fall outside the reachable "
            f"area.\n\nTool-tip radius spans {rmin:.0f}–{rmax:.0f} mm; the robot "
            f"can only reach {MIN_RADIUS:.0f}–{MAX_RADIUS:.0f} mm.\n\n"
            "LinuxCNC will reject this file on load (or clamp the move to the "
            "wrong position). Export anyway?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No)
        return ret == QtWidgets.QMessageBox.Yes

    def _on_offset_drag(self, dwx, dwy):
        """Left-drag on the canvas: fold the world-space delta into the
        internal offset and refresh the preview live (no re-fit). LOAD stays
        available — it always uses the model's current position."""
        if not self._moves_orig:
            return
        self._ox += dwx
        self._oy += dwy
        self._refresh_offset_preview(self._ox, self._oy, self._oa, "Moved")

    def _on_rotate_drag(self, d_deg):
        """Ctrl+left-drag on the canvas: fold the rotation delta into the
        internal offset and refresh the preview live (rotating about the
        model center, without re-fitting the view)."""
        if not self._moves_orig:
            return
        self._oa += d_deg
        self._refresh_offset_preview(self._ox, self._oy, self._oa, "Rotated")

    def _write_positioned_file(self):
        """Write the currently-positioned program to the output folder and
        return its absolute path, or None if aborted/failed. Shared by EXPORT
        (save only) and LOAD (save + push into the software) so both always
        act on the model's current position."""
        if not self._raw_lines or self._gcode_path is None:
            return None
        ox, oy, oa = self._ox, self._oy, self._oa
        if not self._confirm_if_out_of_reach(ox, oy, oa):
            return None
        try:
            os.makedirs(self._auto_save_dir, exist_ok=True)
        except OSError as e:
            QtWidgets.QMessageBox.critical(
                self, "Folder error",
                f"Could not create output folder:\n{self._auto_save_dir}"
                f"\n\n{e}")
            return None
        base = os.path.splitext(os.path.basename(self._gcode_path))[0]
        ts = time.strftime('%Y%m%d_%H%M%S')
        save_path = os.path.join(self._auto_save_dir,
                                 f"{base}_offset_{ts}.ngc")
        cx, cy = self._pivot()
        try:
            write_offset_file(save_path, self._raw_lines,
                              os.path.basename(self._gcode_path),
                              ox, oy, oa, cx, cy)
        except OSError as e:
            QtWidgets.QMessageBox.critical(
                self, "Save failed",
                f"Could not write:\n{save_path}\n\n{e}")
            return None
        # Remember it so the main-viewer mirror ignores our own output.
        self._last_export_path = save_path
        return save_path

    def _on_export(self):
        """Save the positioned file to the output folder (save only, no run)."""
        save_path = self._write_positioned_file()
        if not save_path:
            return
        self.lbl_status.setStyleSheet(self._STATUS_OK)
        self.lbl_status.setText(
            f"Exported {os.path.basename(save_path)}  ·  "
            "click Load to run it.")

    def _on_load(self):
        """Position the file and push it straight into the software so it can
        be run — independent of EXPORT, no prior save required."""
        save_path = self._write_positioned_file()
        if not save_path:
            return
        self.lbl_status.setStyleSheet(self._STATUS_OK)
        self.lbl_status.setText(
            f"Loading {os.path.basename(save_path)}…")
        self.request_load.emit(save_path)
