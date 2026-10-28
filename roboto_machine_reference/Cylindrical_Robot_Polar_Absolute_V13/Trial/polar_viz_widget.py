"""
polar_viz_widget.py — pure-Qt port of polar_visualizer.py (Feature 10).

Replaces the Tkinter visualizer loaded as a userspace HAL component.
Drawing matches the Tk reference: dark background, Cartesian grid that
densifies with zoom, min/max work-envelope circles, axis labels, cyan
trail polyline, yellow home marker at (650, 0), cyan tool dot with
white outline.

No HAL imports here — the host (qtdragon_hd_handler) pumps values in
via set_pose() at 10 Hz from qtvcp.viz-{x,y,homed} pins.
"""

import math

from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import (
    QGridLayout, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QVBoxLayout, QWidget,
)


# Work envelope — same constants as polar_visualizer.py.
MIN_RADIUS = 650.0
MAX_RADIUS = 2600.0
# Perpendicular tool offset (mm). Negative = clockwise from radius arm.
TOOL_OFFSET = -235.0

# Visual constants.
BG = QColor(10, 10, 21)             # canvas background
GRID_MINOR = QColor(51, 51, 51)
GRID_AXIS = QColor(85, 85, 85)
CIRCLE_MIN = QColor(102, 34, 0)     # min-radius circle (dark red)
CIRCLE_MAX = QColor(0, 102, 34)     # max-radius circle (dark green)
TRAIL = QColor(0, 255, 255)
HOME_MARK = QColor(255, 255, 0)
TOOL_FILL = QColor(0, 255, 255)
TOOL_OUTLINE = QColor(255, 255, 255)
AXIS_LABEL = QColor(102, 102, 102)


class PolarVizWidget(QWidget):
    """Polar-machine Cartesian visualizer. Pure Qt, no HAL dependency."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 300)
        self.setMouseTracking(False)
        self.setFocusPolicy(Qt.StrongFocus)
        # View state — same defaults as Tk reference.
        self.zoom = 0.15
        self.pan_x = 0.0
        self.pan_y = 0.0
        # Trail state.
        self.trail = []
        self.show_trail = True
        self.last_x = None
        self.last_y = None
        # Pose state.
        self.cart_x = 0.0
        self.cart_y = 0.0
        self.angle_deg = 0.0
        self.radius_mm = 0.0
        self.is_homed = False
        # Drag state.
        self._drag_start = None

    # ---- world <-> widget coordinate transforms ----

    def _world_to_widget(self, wx, wy):
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        return (cx + wx * self.zoom + self.pan_x,
                cy - wy * self.zoom + self.pan_y)

    def fit_to_envelope(self):
        w, h = self.width(), self.height()
        if w < 10 or h < 10:
            return
        self.zoom = min(w, h) * 0.85 / (2 * MAX_RADIUS)
        self.pan_x = 0.0
        self.pan_y = 0.0
        self.update()

    def clear_trail(self):
        self.trail = []
        self.last_x = None
        self.last_y = None
        self.update()

    def toggle_trail(self):
        self.show_trail = not self.show_trail
        self.update()

    # ---- external pose update (called from handler's 10 Hz timer) ----

    def set_pose(self, x_pos, y_pos, homed):
        """Push commanded (X,Y) + homed flag from HAL into the widget."""
        # Reproduce the Tk visualizer's polar/tool-offset transform.
        self.angle_deg = math.degrees(math.atan2(y_pos, x_pos))
        self.radius_mm = math.sqrt(x_pos * x_pos + y_pos * y_pos)
        a = math.radians(self.angle_deg)
        self.cart_x = self.radius_mm * math.cos(a) - TOOL_OFFSET * math.sin(a)
        self.cart_y = self.radius_mm * math.sin(a) + TOOL_OFFSET * math.cos(a)

        was_homed = self.is_homed
        self.is_homed = bool(homed)
        if self.is_homed and not was_homed:
            # Snap trail start to physical home (650, 0) on rising-edge of homed.
            self.trail = [(MIN_RADIUS, 0.0)]
            self.last_x = MIN_RADIUS
            self.last_y = 0.0

        # Append to trail only if displacement > 0.5 mm (matches Tk reference).
        if self.show_trail:
            if (self.last_x is None
                    or abs(self.cart_x - self.last_x) > 0.5
                    or abs(self.cart_y - self.last_y) > 0.5):
                self.trail.append((self.cart_x, self.cart_y))
                self.last_x = self.cart_x
                self.last_y = self.cart_y
        self.update()

    # ---- painting ----

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.fillRect(self.rect(), BG)
        self._draw_grid(p)
        self._draw_envelope(p)
        self._draw_axis_labels(p)
        if self.show_trail and len(self.trail) >= 2:
            self._draw_trail(p)
        self._draw_home_marker(p)
        self._draw_tool(p)

    def _draw_grid(self, p):
        # Grid spacing scales with zoom — matches Tk reference.
        grid_mm = 500
        if self.zoom > 0.1:
            grid_mm = 200
        if self.zoom > 0.2:
            grid_mm = 100
        w, h = self.width(), self.height()
        pen_minor = QPen(GRID_MINOR, 1)
        pen_axis = QPen(GRID_AXIS, 1)
        for x in range(-5000, 5001, grid_mm):
            wx, _ = self._world_to_widget(x, 0)
            if 0 <= wx <= w:
                p.setPen(pen_axis if x == 0 else pen_minor)
                p.drawLine(int(wx), 0, int(wx), h)
        for y in range(-5000, 5001, grid_mm):
            _, wy = self._world_to_widget(0, y)
            if 0 <= wy <= h:
                p.setPen(pen_axis if y == 0 else pen_minor)
                p.drawLine(0, int(wy), w, int(wy))

    def _draw_envelope(self, p):
        # Two concentric work-envelope circles at MIN_RADIUS / MAX_RADIUS.
        for r, color in ((MIN_RADIUS, CIRCLE_MIN), (MAX_RADIUS, CIRCLE_MAX)):
            cx, cy = self._world_to_widget(0, 0)
            r_px = r * self.zoom
            p.setPen(QPen(color, 2))
            p.setBrush(Qt.NoBrush)
            p.drawEllipse(QPointF(cx, cy), r_px, r_px)

    def _draw_axis_labels(self, p):
        ox, oy = self._world_to_widget(0, 0)
        p.setPen(AXIS_LABEL)
        p.setFont(QFont('Arial', 9))
        p.drawText(self.width() - 24, int(oy) + 4, 'X+')
        p.drawText(int(ox) + 8, 14, 'Y+')

    def _draw_trail(self, p):
        poly = QPolygonF()
        for tx, ty in self.trail:
            wx, wy = self._world_to_widget(tx, ty)
            poly.append(QPointF(wx, wy))
        p.setPen(QPen(TRAIL, 2))
        p.setBrush(Qt.NoBrush)
        p.drawPolyline(poly)

    def _draw_home_marker(self, p):
        hx, hy = self._world_to_widget(MIN_RADIUS, 0)
        p.setPen(QPen(HOME_MARK, 2))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(QPointF(hx, hy), 6, 6)

    def _draw_tool(self, p):
        tx, ty = self._world_to_widget(self.cart_x, self.cart_y)
        p.setPen(QPen(TOOL_OUTLINE, 2))
        p.setBrush(QBrush(TOOL_FILL))
        p.drawEllipse(QPointF(tx, ty), 10, 10)

    # ---- mouse interaction ----

    def wheelEvent(self, event):
        # Scroll zooms around the cursor. Clamp 0.01..1.0 like the Tk ref.
        factor = 1.1 if event.angleDelta().y() > 0 else 0.9
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        x = event.position().x() if hasattr(event, 'position') else event.x()
        y = event.position().y() if hasattr(event, 'position') else event.y()
        self.pan_x = (self.pan_x - (x - cx)) * factor + (x - cx)
        self.pan_y = (self.pan_y - (y - cy)) * factor + (y - cy)
        self.zoom = max(0.01, min(1.0, self.zoom * factor))
        self.update()
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = event.pos()

    def mouseMoveEvent(self, event):
        if self._drag_start is None:
            return
        dx = event.pos().x() - self._drag_start.x()
        dy = event.pos().y() - self._drag_start.y()
        self.pan_x += dx
        self.pan_y += dy
        self._drag_start = event.pos()
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start = None

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.fit_to_envelope()


class DroPanel(QWidget):
    """AXIS-style coordinate overlay — white-on-black monospace, two columns.

    Layout (row x col, 0-indexed):
      0  X    DTG X
      1  Y    DTG Y
      2  Z    DTG Z
      3  G54 X  G92 X
      4  G54 Y  G92 Y
      5  G54 Z  G92 Z
      6  G54 R
      7  TLO X
      8  TLO Y
      9  TLO Z
      10 Vel
    Values are right-aligned, all formatted "%8.3f".
    """

    _LEFT_ROWS = ('X', 'Y', 'Z', 'G54 X', 'G54 Y', 'G54 Z',
                  'G54 R', 'TLO X', 'TLO Y', 'TLO Z', 'Vel')
    _RIGHT_ROWS = ('DTG X', 'DTG Y', 'DTG Z', 'G92 X', 'G92 Y', 'G92 Z')

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('PolarVizDro')
        self.setStyleSheet(
            '#PolarVizDro { background-color:#000; }'
            '#PolarVizDro QLabel { color:#ffffff; }'
        )
        self.setFixedWidth(300)
        font = QFont('Monospace', 11)
        font.setStyleHint(QFont.TypeWriter)

        self._labels = {}
        grid = QGridLayout(self)
        grid.setContentsMargins(8, 8, 8, 8)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(2)

        def _add(row, col, key):
            cap = QLabel(key + ':')
            cap.setFont(font)
            cap.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            val = QLabel('0.000')
            val.setFont(font)
            val.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(cap, row, col * 2)
            grid.addWidget(val, row, col * 2 + 1)
            self._labels[key] = val

        for r, key in enumerate(self._LEFT_ROWS):
            _add(r, 0, key)
        for r, key in enumerate(self._RIGHT_ROWS):
            _add(r, 1, key)

        grid.setRowStretch(len(self._LEFT_ROWS), 1)

    def set_values(self, x, y, z, dtg, g54, g92, tlo, rot_xy, vel):
        """Update all readouts. dtg/g54/g92/tlo are 3-tuples (x,y,z)."""
        self._labels['X'].setText('{:8.3f}'.format(x))
        self._labels['Y'].setText('{:8.3f}'.format(y))
        self._labels['Z'].setText('{:8.3f}'.format(z))
        self._labels['DTG X'].setText('{:8.3f}'.format(dtg[0]))
        self._labels['DTG Y'].setText('{:8.3f}'.format(dtg[1]))
        self._labels['DTG Z'].setText('{:8.3f}'.format(dtg[2]))
        self._labels['G54 X'].setText('{:8.3f}'.format(g54[0]))
        self._labels['G54 Y'].setText('{:8.3f}'.format(g54[1]))
        self._labels['G54 Z'].setText('{:8.3f}'.format(g54[2]))
        self._labels['G54 R'].setText('{:8.3f}'.format(rot_xy))
        self._labels['G92 X'].setText('{:8.3f}'.format(g92[0]))
        self._labels['G92 Y'].setText('{:8.3f}'.format(g92[1]))
        self._labels['G92 Z'].setText('{:8.3f}'.format(g92[2]))
        self._labels['TLO X'].setText('{:8.3f}'.format(tlo[0]))
        self._labels['TLO Y'].setText('{:8.3f}'.format(tlo[1]))
        self._labels['TLO Z'].setText('{:8.3f}'.format(tlo[2]))
        self._labels['Vel'].setText('{:8.3f}'.format(vel))


class PolarVizWindow(QMainWindow):
    """Host window — DRO panel on the left, visualizer on the right."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Polar Robot Visualizer')
        self.resize(1200, 700)
        root = QWidget()
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)

        # Status bar — homed indicator + zoom + trail count.
        top = QHBoxLayout()
        self.lbl_homed = QLabel('● NOT HOMED')
        self.lbl_homed.setStyleSheet('color:#ff4444; font:bold 11pt Arial;')
        top.addWidget(self.lbl_homed)
        top.addStretch(1)
        self.lbl_zoom = QLabel('Zoom: --')
        self.lbl_zoom.setStyleSheet('color:#888;')
        top.addWidget(self.lbl_zoom)
        self.lbl_trail = QLabel('Trail: 0')
        self.lbl_trail.setStyleSheet('color:#888;')
        top.addWidget(self.lbl_trail)
        vbox.addLayout(top)

        # Middle row — DRO panel | canvas
        middle = QHBoxLayout()
        middle.setSpacing(4)
        self.dro = DroPanel()
        middle.addWidget(self.dro)
        self.viz = PolarVizWidget()
        middle.addWidget(self.viz, stretch=1)
        vbox.addLayout(middle, stretch=1)

        # Buttons.
        btns = QHBoxLayout()
        b_fit = QPushButton('Fit')
        b_fit.clicked.connect(self.viz.fit_to_envelope)
        b_fit.clicked.connect(self._refresh_status)
        btns.addWidget(b_fit)
        b_clear = QPushButton('Clear Trail')
        b_clear.clicked.connect(self.viz.clear_trail)
        b_clear.clicked.connect(self._refresh_status)
        btns.addWidget(b_clear)
        self.b_trail = QPushButton('Trail: ON')
        self.b_trail.clicked.connect(self._toggle_trail_clicked)
        btns.addWidget(self.b_trail)
        btns.addStretch(1)
        vbox.addLayout(btns)

        # Initial fit after first show — needs sizes.
        self.viz.fit_to_envelope()

    def _toggle_trail_clicked(self):
        self.viz.toggle_trail()
        self.b_trail.setText('Trail: ON' if self.viz.show_trail else 'Trail: OFF')

    def _refresh_status(self):
        self.lbl_zoom.setText('Zoom: {:.0f}%'.format(self.viz.zoom * 700))
        self.lbl_trail.setText('Trail: {}'.format(len(self.viz.trail)))

    def push_pose(self, x, y, homed):
        """Called by the handler's QTimer. Position-only update."""
        self.viz.set_pose(x, y, homed)
        if homed:
            self.lbl_homed.setText('● HOMED')
            self.lbl_homed.setStyleSheet('color:#00ff88; font:bold 11pt Arial;')
        else:
            self.lbl_homed.setText('● NOT HOMED')
            self.lbl_homed.setStyleSheet('color:#ff4444; font:bold 11pt Arial;')
        self._refresh_status()

    def push_dro(self, x, y, z, dtg, g54, g92, tlo, rot_xy, vel):
        """Update the AXIS-style DRO overlay. Called from the same timer."""
        self.dro.set_values(x, y, z, dtg, g54, g92, tlo, rot_xy, vel)
